from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.contracts import (
    Availability,
    C1EnvironmentalInput,
    C7ModelCapability,
    Coordinates,
    DailyWeather,
    DataStatus,
    Measurement,
    Provenance,
    SimulationPeriod,
    SoilProperties,
)
from app.services.crop_lens import (
    CropLensResolver,
    CropRecord,
    ResolutionStatus,
    get_crop_by_id,
)
from app.services.environmental.exceptions import (
    InvalidCoordinatesError,
)
from app.services.environmental.models import (
    EnvironmentalInputRequest,
    EnvironmentalInputResult,
)
from app.services.soil import (
    SoilAdapterError,
    SoilGridsAdapter,
    SoilNetworkError,
    SoilProviderError,
    SoilResponseMalformedError,
    SoilResult,
    SoilTimeoutError,
)
from app.services.weather import (
    OpenMeteoWeatherAdapter,
    WeatherAdapterError,
    WeatherNetworkError,
    WeatherProviderError,
    WeatherResponseMalformedError,
    WeatherResult,
    WeatherTimeoutError,
    normalize_member_id,
)


class EnvironmentalInputService:
    """Orchestrates, normalizes, and validates environmental inputs into authoritative C1 contracts.

    Coordinates retrieval of weather data from Open-Meteo and gridded soil properties from
    ISRIC SoilGrids, verifies crop capability and requested outputs against the C7 registry,
    and enforces strict scientific data-quality constraints (physical bounds, missingness
    preservation, and independent provider failure handling).
    """

    def __init__(
        self,
        weather_adapter: OpenMeteoWeatherAdapter | None = None,
        soil_adapter: SoilGridsAdapter | None = None,
        crop_resolver: CropLensResolver | None = None,
        cache_ttl_seconds: int = 3600,
        max_cache_entries: int = 1000,
    ) -> None:
        self.weather_adapter = weather_adapter or OpenMeteoWeatherAdapter()
        self.soil_adapter = soil_adapter or SoilGridsAdapter()
        self.crop_resolver = crop_resolver or CropLensResolver()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_entries = max_cache_entries
        self._cache: OrderedDict[str, tuple[datetime, EnvironmentalInputResult]] = (
            OrderedDict()
        )

    def _validate_coordinates(self, latitude: float, longitude: float) -> None:
        """Validate latitude and longitude against geographic WGS 84 bounds."""
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise InvalidCoordinatesError(
                f"Coordinates out of bounds: latitude={latitude} must be in [-90, 90], "
                f"longitude={longitude} must be in [-180, 180]."
            )

    def _determine_soil_target_depth_cm(
        self,
        requested_depth: float | None,
        capability: C7ModelCapability | None,
    ) -> float:
        """Determine effective soil profile depth following strict priority rules:

        1. Explicit soil_target_depth_cm supplied by caller.
        2. Crop C7 max_rooting_depth_m parameter multiplied by 100.
        3. Default fallback of 30.0 cm.
        """
        if requested_depth is not None and requested_depth > 0:
            return float(requested_depth)

        if capability is not None and capability.model_parameters:
            raw_depth = (
                capability.model_parameters.get("max_rooting_depth_m")
                or capability.model_parameters.get("maxRootingDepthM")
            )
            if raw_depth is not None:
                try:
                    val = float(raw_depth)
                    if val > 0:
                        return round(val * 100.0, 2)
                except (ValueError, TypeError):
                    pass

        return 30.0

    def _generate_cache_key(
        self,
        request: EnvironmentalInputRequest,
        effective_target_depth_cm: float,
    ) -> str:
        """Generate unique cache key accounting for all parameters affecting the snapshot."""
        return (
            f"{request.farm_id}:{request.plot_id}:"
            f"{request.location.latitude:.4f}:{request.location.longitude:.4f}:"
            f"{request.timezone}:{request.simulation_period.start_date}:{request.simulation_period.end_date}:"
            f"{request.weather_member_id}:{effective_target_depth_cm:.1f}:"
            f"{request.crop_id}:{request.crop_query}:{','.join(sorted(request.requested_outputs))}"
        )

    def _build_fallback_soil(
        self, reason: str, depth_cm: float = 30.0
    ) -> SoilProperties:
        """Build a compliant SoilProperties object where all measurements are explicitly MISSING."""
        return SoilProperties(
            depth_cm=Measurement(
                value=None,
                unit="cm",
                availability=Availability(status=DataStatus.MISSING, reason=reason),
            ),
            texture=None,
            field_capacity=Measurement(
                value=None,
                unit="m3/m3",
                availability=Availability(status=DataStatus.MISSING, reason=reason),
            ),
            wilting_point=Measurement(
                value=None,
                unit="m3/m3",
                availability=Availability(status=DataStatus.MISSING, reason=reason),
            ),
            bulk_density=None,
        )

    def _build_outage_daily_weather(
        self,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> list[DailyWeather]:
        """Generate dated DailyWeather records with status MISSING for every day during a weather outage."""
        records: list[DailyWeather] = []
        curr = start_date
        while curr <= end_date:
            records.append(
                DailyWeather(
                    date=curr,
                    temperature_min_c=Measurement(
                        value=None,
                        unit="degC",
                        availability=Availability(
                            status=DataStatus.MISSING, reason=reason
                        ),
                    ),
                    temperature_max_c=Measurement(
                        value=None,
                        unit="degC",
                        availability=Availability(
                            status=DataStatus.MISSING, reason=reason
                        ),
                    ),
                    rainfall_mm=Measurement(
                        value=None,
                        unit="mm",
                        availability=Availability(
                            status=DataStatus.MISSING, reason=reason
                        ),
                    ),
                    reference_evapotranspiration_mm=Measurement(
                        value=None,
                        unit="mm",
                        availability=Availability(
                            status=DataStatus.MISSING, reason=reason
                        ),
                    ),
                    ensemble_member_id=None,
                )
            )
            curr += timedelta(days=1)
        return records

    def _resolve_and_validate_crop(
        self,
        req: EnvironmentalInputRequest,
        errors: list[str],
        warnings: list[str],
        unsupported_outputs: list[str],
    ) -> tuple[CropRecord | None, C7ModelCapability | None]:
        """Resolve crop identity and verify that requested outputs and engine are supported."""
        crop: CropRecord | None = None
        capability: C7ModelCapability | None = None

        if req.crop_id is not None:
            crop = get_crop_by_id(req.crop_id)
            if crop is None:
                errors.append(f"Crop ID '{req.crop_id}' was not found in the crop registry.")
                return None, None
            capability = crop.to_c7_capability()
        elif req.crop_query is not None and req.crop_query.strip():
            res = self.crop_resolver.resolve(req.crop_query)
            if res.status == ResolutionStatus.EXACT_MATCH and res.crop is not None:
                crop = res.crop
                capability = res.capability or crop.to_c7_capability()
            elif res.status == ResolutionStatus.AMBIGUOUS:
                errors.append(
                    f"Crop query '{req.crop_query}' is ambiguous ({len(res.candidates)} matches found). "
                    "Explicit crop confirmation is required."
                )
                return None, None
            else:
                errors.append(
                    f"Crop query '{req.crop_query}' was not found in the crop registry."
                )
                return None, None
        else:
            warnings.append("No crop specified; crop capability validation skipped.")
            return None, None

        if capability is not None:
            crop_name = (
                capability.accepted_crop_names[0]
                if capability.accepted_crop_names
                else "selected crop"
            )

            # Check engine support for quantitative simulation
            if (
                req.require_quantitative_simulation
                and capability.selected_engine == "identity/ecology-only"
            ):
                errors.append(
                    f"Crop '{crop_name}' uses engine 'identity/ecology-only' which does not support "
                    "quantitative simulation. Quantitative yield and water-balance modeling are unsupported."
                )
            elif req.require_quantitative_simulation and not capability.supported_outputs:
                errors.append(f"Farm-scale simulation is unsupported for crop '{crop_name}'.")

            # Check requested outputs against crop's supported outputs
            if req.requested_outputs:
                for out in req.requested_outputs:
                    if out not in capability.supported_outputs:
                        unsupported_outputs.append(out)
                        errors.append(
                            f"Requested simulation output '{out}' is not supported for crop '{crop_name}' "
                            f"(engine: {capability.selected_engine}:{capability.engine_version}). "
                            f"Supported outputs: {capability.supported_outputs}."
                        )

        return crop, capability

    def _build_single_result(
        self,
        request: EnvironmentalInputRequest,
        weather_result: WeatherResult | None,
        soil_result: SoilResult | None,
        weather_fetch_error: str | None,
        soil_fetch_error: str | None,
        capability: C7ModelCapability | None,
        effective_target_depth_cm: float,
        crop_errors: list[str],
        crop_warnings: list[str],
        unsupported_outputs: list[str],
        target_member_id: str | None,
        now: datetime,
    ) -> EnvironmentalInputResult:
        """Internal worker to assemble and validate a single C1 environmental input trajectory."""
        errors: list[str] = list(crop_errors)
        warnings: list[str] = list(crop_warnings)
        missing_fields: list[str] = []
        unsupported_outs: list[str] = list(unsupported_outputs)

        # 1. Validate Simulation Period
        if request.simulation_period.start_date > request.simulation_period.end_date:
            errors.append(
                f"Simulation start date ({request.simulation_period.start_date}) cannot be after "
                f"end date ({request.simulation_period.end_date})."
            )

        # 2. Select Daily Weather Records
        selected_daily_weather: list[DailyWeather] = []
        is_weather_outage = False

        if weather_result is not None:
            if target_member_id is not None:
                norm_member = normalize_member_id(target_member_id)
                member_records = weather_result.ensemble_members.get(norm_member)
                if member_records is None:
                    errors.append(
                        f"Requested ensemble member '{target_member_id}' (normalized: '{norm_member}') "
                        f"was not found in weather forecast. Available members: "
                        f"{sorted(weather_result.ensemble_members.keys())}."
                    )
                    is_weather_outage = True
                else:
                    selected_daily_weather = list(member_records)
            else:
                if not weather_result.deterministic_available:
                    errors.append(
                        f"Deterministic weather forecast is unavailable: {weather_result.deterministic_error}"
                    )
                    is_weather_outage = True
                else:
                    selected_daily_weather = list(weather_result.deterministic_daily)
        else:
            is_weather_outage = True
            missing_fields.append("daily_weather")
            if weather_fetch_error:
                errors.append(weather_fetch_error)

        start_date = request.simulation_period.start_date
        end_date = request.simulation_period.end_date

        # If complete weather outage or member missing, generate dated DailyWeather records with status MISSING
        if is_weather_outage or not selected_daily_weather:
            days_count = (end_date - start_date).days + 1
            outage_msg = f"Weather provider complete outage: missing records for all {days_count} simulation days."
            if not any("outage" in e.lower() or "retrieval failed" in e.lower() for e in errors):
                errors.append(outage_msg)
            reason = weather_fetch_error or (
                errors[-1] if errors else outage_msg
            )
            period_daily_weather = self._build_outage_daily_weather(
                start_date, end_date, reason=reason
            )
            if "daily_weather" not in missing_fields:
                missing_fields.append("daily_weather")
        else:
            period_daily_weather = [
                dw for dw in selected_daily_weather if start_date <= dw.date <= end_date
            ]
            period_daily_weather.sort(key=lambda dw: dw.date)

            present_dates = {dw.date for dw in period_daily_weather}
            expected_dates: list[date] = []
            curr = start_date
            while curr <= end_date:
                expected_dates.append(curr)
                curr += timedelta(days=1)

            missing_dates = [d for d in expected_dates if d not in present_dates]
            if missing_dates:
                missing_fields.append("daily_weather:dates")
                errors.append(
                    f"Weather data is missing coverage for dates: {[d.isoformat() for d in missing_dates]}."
                )

        # 3. Validate Physical Bounds and Completeness of Daily Weather Records
        for dw in period_daily_weather:
            t_min = dw.temperature_min_c
            t_max = dw.temperature_max_c
            rainfall = dw.rainfall_mm

            # Check for missing values (never replace with 0)
            if not is_weather_outage:
                if t_min.value is None or t_min.availability.status != DataStatus.AVAILABLE:
                    missing_fields.append(f"daily_weather[{dw.date}].temperature_min_c")
                    errors.append(
                        f"Daily weather on {dw.date} is missing minimum temperature. Missing values are never zeroed."
                    )
                if t_max.value is None or t_max.availability.status != DataStatus.AVAILABLE:
                    missing_fields.append(f"daily_weather[{dw.date}].temperature_max_c")
                    errors.append(
                        f"Daily weather on {dw.date} is missing maximum temperature. Missing values are never zeroed."
                    )
                if rainfall.value is None or rainfall.availability.status != DataStatus.AVAILABLE:
                    missing_fields.append(f"daily_weather[{dw.date}].rainfall_mm")
                    errors.append(
                        f"Daily weather on {dw.date} is missing rainfall. Missing values are never zeroed."
                    )

            # Physical consistency check: T_min <= T_max
            if (
                t_min.value is not None
                and t_max.value is not None
                and t_min.value > t_max.value
            ):
                errors.append(
                    f"Physical consistency violation on {dw.date}: temperature_min ({t_min.value}°C) "
                    f"> temperature_max ({t_max.value}°C)."
                )

            # Physical bounds check: rainfall >= 0
            if rainfall.value is not None and rainfall.value < 0:
                errors.append(
                    f"Physical consistency violation on {dw.date}: rainfall ({rainfall.value} mm) cannot be negative."
                )

            # Reference ET0 check
            if dw.reference_evapotranspiration_mm is not None:
                et0 = dw.reference_evapotranspiration_mm
                if et0.value is not None and et0.value < 0:
                    errors.append(
                        f"Physical consistency violation on {dw.date}: reference evapotranspiration ({et0.value} mm) "
                        "cannot be negative."
                    )
            elif not is_weather_outage:
                warnings.append(
                    f"Daily weather on {dw.date} does not include reference ET0 measurement."
                )

        # 4. Process and Validate Soil Data
        soil_props: SoilProperties
        if soil_result is not None:
            soil_props = soil_result.soil_properties

            # Check depth
            if soil_props.depth_cm.value is None or soil_props.depth_cm.availability.status != DataStatus.AVAILABLE:
                missing_fields.append("soil.depth_cm")
                errors.append("Mandatory soil depth measurement is missing.")
            elif soil_props.depth_cm.value <= 0:
                errors.append(f"Invalid soil depth: {soil_props.depth_cm.value} cm (must be > 0).")

            if soil_result.availability.status == DataStatus.MISSING:
                coverages = soil_result.raw_metadata.get("coverages", {})
                failures = sorted({
                    reason for name, reason in coverages.items()
                    if name.startswith(("wv0033_", "wv1500_")) and reason != "sampled"
                })
                if failures:
                    errors.append("SoilGrids hydraulic coverage is incomplete: " + "; ".join(failures) + ".")

            # Check field capacity
            fc = soil_props.field_capacity
            if fc.value is None or fc.availability.status != DataStatus.AVAILABLE:
                missing_fields.append("soil.field_capacity")
                errors.append("Mandatory soil field capacity measurement is missing.")

            # Check wilting point
            wp = soil_props.wilting_point
            if wp.value is None or wp.availability.status != DataStatus.AVAILABLE:
                missing_fields.append("soil.wilting_point")
                errors.append("Mandatory soil wilting point measurement is missing.")

            # Physical checks for soil moisture limits
            if fc.value is not None and wp.value is not None:
                if fc.value < 0 or wp.value < 0:
                    errors.append("Physical consistency violation: soil water contents cannot be negative.")
                if fc.value <= wp.value:
                    errors.append(
                        f"Physical consistency violation: field capacity ({fc.value} m3/m3) must exceed "
                        f"wilting point ({wp.value} m3/m3)."
                    )
        else:
            missing_fields.extend(["soil.depth_cm", "soil.field_capacity", "soil.wilting_point"])
            soil_props = self._build_fallback_soil(
                reason=soil_fetch_error or "Soil data retrieval failed.",
                depth_cm=effective_target_depth_cm,
            )
            if soil_fetch_error and soil_fetch_error not in errors:
                errors.append(soil_fetch_error)

        # 5. Aggregate Provenance and Data Source IDs
        data_source_ids: list[str] = []
        provenance: list[Provenance] = []

        if weather_result is not None:
            data_source_ids.extend(weather_result.data_source_ids)
            provenance.extend(weather_result.provenance)
        if soil_result is not None:
            data_source_ids.extend(soil_result.data_source_ids)
            provenance.extend(soil_result.provenance)

        seen_ds: set[str] = set()
        deduped_data_source_ids: list[str] = []
        for ds in data_source_ids:
            if ds not in seen_ds:
                seen_ds.add(ds)
                deduped_data_source_ids.append(ds)

        # 6. Determine Overall Status and Availability
        status: DataStatus
        is_valid: bool

        if errors:
            is_valid = False
            if unsupported_outs or any(
                "identity/ecology-only" in err or "unsupported" in err.lower()
                for err in errors
            ):
                status = DataStatus.UNSUPPORTED
            elif missing_fields or any(
                "missing" in err.lower() or "unavailable" in err.lower() for err in errors
            ):
                status = DataStatus.MISSING
            else:
                status = DataStatus.INVALID
        else:
            is_valid = True
            status = DataStatus.AVAILABLE

        # 7. Assemble Authoritative C1 Contract Payload (strict farm_id, no plot_id)
        c1_input = C1EnvironmentalInput(
            contract_version="1.0",
            farm_id=request.farm_id,
            location=request.location,
            timezone=request.timezone,
            simulation_period=request.simulation_period,
            daily_weather=period_daily_weather,
            soil=soil_props,
            data_source_ids=deduped_data_source_ids,
            retrieved_at=now,
            availability=Availability(
                status=status,
                reason="; ".join(errors) if errors else None,
            ),
            provenance=provenance,
        )

        return EnvironmentalInputResult(
            is_valid=is_valid,
            status=status,
            c1_input=c1_input,
            plot_id=request.plot_id,
            capability=capability,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            unsupported_outputs=unsupported_outs,
            freshness="live",
            weather_result=weather_result,
            soil_result=soil_result,
        )

    async def prepare_environmental_input(
        self, request: EnvironmentalInputRequest
    ) -> EnvironmentalInputResult:
        """Prepare, normalize, and validate environmental inputs into the authoritative C1 contract."""
        self._validate_coordinates(request.location.latitude, request.location.longitude)

        now = datetime.now(UTC)

        crop_errors: list[str] = []
        crop_warnings: list[str] = []
        unsupported_outputs: list[str] = []

        _crop, capability = self._resolve_and_validate_crop(
            request, crop_errors, crop_warnings, unsupported_outputs
        )

        effective_target_depth_cm = self._determine_soil_target_depth_cm(
            request.soil_target_depth_cm, capability
        )

        cache_key = self._generate_cache_key(request, effective_target_depth_cm)

        if not request.force_refresh and cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            age_sec = int((now - cached_time).total_seconds())
            if age_sec < self.cache_ttl_seconds:
                self._cache.move_to_end(cache_key)
                result_copy = cached_result.model_copy(deep=True)
                result_copy.freshness = f"cached ({age_sec}s old)"
                return result_copy
            del self._cache[cache_key]

        # Fetch weather
        weather_result: WeatherResult | None = None
        weather_fetch_error: str | None = None
        include_ensemble = bool(
            request.weather_member_id is not None or request.include_ensemble is True
        )

        try:
            weather_result = await self.weather_adapter.fetch_weather(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                timezone=request.timezone,
                start_date=request.simulation_period.start_date,
                end_date=request.simulation_period.end_date,
                include_ensemble=include_ensemble,
            )
        except (
            WeatherAdapterError,
            WeatherNetworkError,
            WeatherProviderError,
            WeatherResponseMalformedError,
            WeatherTimeoutError,
        ) as exc:
            weather_fetch_error = f"Weather data retrieval failed: {exc}"

        # Fetch soil
        soil_result: SoilResult | None = None
        soil_fetch_error: str | None = None

        try:
            soil_result = await self.soil_adapter.fetch_soil(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                target_depth_cm=effective_target_depth_cm,
            )
        except (
            SoilAdapterError,
            SoilNetworkError,
            SoilProviderError,
            SoilResponseMalformedError,
            SoilTimeoutError,
        ) as exc:
            soil_fetch_error = f"Soil data retrieval failed: {exc}"

        result = self._build_single_result(
            request=request,
            weather_result=weather_result,
            soil_result=soil_result,
            weather_fetch_error=weather_fetch_error,
            soil_fetch_error=soil_fetch_error,
            capability=capability,
            effective_target_depth_cm=effective_target_depth_cm,
            crop_errors=crop_errors,
            crop_warnings=crop_warnings,
            unsupported_outputs=unsupported_outputs,
            target_member_id=request.weather_member_id,
            now=now,
        )

        if result.is_valid:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
            self._cache[cache_key] = (now, result)
            while len(self._cache) > self.max_cache_entries:
                self._cache.popitem(last=False)

        return result

    async def prepare_ensemble_batch(
        self,
        request: EnvironmentalInputRequest,
        member_ids: list[str] | None = None,
    ) -> dict[str, EnvironmentalInputResult]:
        """Prepare independent C1 inputs for multiple ensemble members using a single weather & soil fetch.

        Args:
            request: Base environmental input request (farm, plot, coordinates, dates, crop).
            member_ids: Optional explicit list of member IDs to process (e.g. ['member-01', 'member-02']).
                        If None, processes all available ensemble members in the retrieved forecast.

        Returns:
            Dictionary mapping member ID to its independent EnvironmentalInputResult.
        """
        self._validate_coordinates(request.location.latitude, request.location.longitude)

        now = datetime.now(UTC)

        crop_errors: list[str] = []
        crop_warnings: list[str] = []
        unsupported_outputs: list[str] = []

        _crop, capability = self._resolve_and_validate_crop(
            request, crop_errors, crop_warnings, unsupported_outputs
        )

        effective_target_depth_cm = self._determine_soil_target_depth_cm(
            request.soil_target_depth_cm, capability
        )

        # If explicit member_ids are specified and all are in cache and fresh, serve directly from cache
        if member_ids is not None and not request.force_refresh:
            all_cached = True
            cached_subset: dict[str, EnvironmentalInputResult] = {}
            for mid in member_ids:
                req_mid = request.model_copy(update={"weather_member_id": mid})
                mid_cache_key = self._generate_cache_key(
                    req_mid, effective_target_depth_cm
                )
                if mid_cache_key in self._cache:
                    cached_time, cached_result = self._cache[mid_cache_key]
                    age_sec = int((now - cached_time).total_seconds())
                    if age_sec < self.cache_ttl_seconds:
                        self._cache.move_to_end(mid_cache_key)
                        res_copy = cached_result.model_copy(deep=True)
                        res_copy.freshness = f"cached ({age_sec}s old)"
                        cached_subset[mid] = res_copy
                        continue
                all_cached = False
                break
            if all_cached:
                return cached_subset

        # Single fetch for weather (with include_ensemble=True) and single fetch for soil
        weather_result: WeatherResult | None = None
        weather_fetch_error: str | None = None

        try:
            weather_result = await self.weather_adapter.fetch_weather(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                timezone=request.timezone,
                start_date=request.simulation_period.start_date,
                end_date=request.simulation_period.end_date,
                include_ensemble=True,
            )
        except (
            WeatherAdapterError,
            WeatherNetworkError,
            WeatherProviderError,
            WeatherResponseMalformedError,
            WeatherTimeoutError,
        ) as exc:
            weather_fetch_error = f"Weather data retrieval failed: {exc}"

        soil_result: SoilResult | None = None
        soil_fetch_error: str | None = None

        try:
            soil_result = await self.soil_adapter.fetch_soil(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                target_depth_cm=effective_target_depth_cm,
            )
        except (
            SoilAdapterError,
            SoilNetworkError,
            SoilProviderError,
            SoilResponseMalformedError,
            SoilTimeoutError,
        ) as exc:
            soil_fetch_error = f"Soil data retrieval failed: {exc}"

        # Determine target members
        target_members: list[str]
        if member_ids is not None:
            target_members = list(member_ids)
        elif weather_result is not None and weather_result.ensemble_members:
            target_members = sorted(weather_result.ensemble_members.keys())
        else:
            target_members = []

        results: dict[str, EnvironmentalInputResult] = {}
        for mid in target_members:
            req_mid = request.model_copy(update={"weather_member_id": mid})
            mid_cache_key = self._generate_cache_key(req_mid, effective_target_depth_cm)

            if not request.force_refresh and mid_cache_key in self._cache:
                cached_time, cached_result = self._cache[mid_cache_key]
                age_sec = int((now - cached_time).total_seconds())
                if age_sec < self.cache_ttl_seconds:
                    self._cache.move_to_end(mid_cache_key)
                    result_copy = cached_result.model_copy(deep=True)
                    result_copy.freshness = f"cached ({age_sec}s old)"
                    results[mid] = result_copy
                    continue
                del self._cache[mid_cache_key]

            mid_res = self._build_single_result(
                request=req_mid,
                weather_result=weather_result,
                soil_result=soil_result,
                weather_fetch_error=weather_fetch_error,
                soil_fetch_error=soil_fetch_error,
                capability=capability,
                effective_target_depth_cm=effective_target_depth_cm,
                crop_errors=crop_errors,
                crop_warnings=crop_warnings,
                unsupported_outputs=unsupported_outputs,
                target_member_id=mid,
                now=now,
            )

            if mid_res.is_valid:
                if mid_cache_key in self._cache:
                    self._cache.move_to_end(mid_cache_key)
                self._cache[mid_cache_key] = (now, mid_res)
                while len(self._cache) > self.max_cache_entries:
                    self._cache.popitem(last=False)

            results[mid] = mid_res

        return results

    async def prepare(
        self,
        farm_id: UUID,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        timezone: str = "Asia/Kolkata",
        plot_id: UUID | None = None,
        crop_id: UUID | None = None,
        crop_query: str | None = None,
        requested_outputs: list[str] | None = None,
        weather_member_id: str | None = None,
        include_ensemble: bool | None = None,
        soil_target_depth_cm: float | None = None,
        require_quantitative_simulation: bool = True,
        force_refresh: bool = False,
    ) -> EnvironmentalInputResult:
        """Convenience method to prepare environmental inputs from explicit primitive parameters."""
        self._validate_coordinates(latitude, longitude)
        location = Coordinates(latitude=latitude, longitude=longitude, crs="EPSG:4326")
        sim_period = SimulationPeriod(start_date=start_date, end_date=end_date)
        req = EnvironmentalInputRequest(
            farm_id=farm_id,
            plot_id=plot_id,
            location=location,
            timezone=timezone,
            simulation_period=sim_period,
            crop_id=crop_id,
            crop_query=crop_query,
            requested_outputs=requested_outputs or [],
            weather_member_id=weather_member_id,
            include_ensemble=include_ensemble,
            soil_target_depth_cm=soil_target_depth_cm,
            require_quantitative_simulation=require_quantitative_simulation,
            force_refresh=force_refresh,
        )
        return await self.prepare_environmental_input(req)
