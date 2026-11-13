from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, date, datetime
from typing import Any

from app.contracts import (
    Availability,
    Coordinates,
    DailyWeather,
    DataStatus,
    Measurement,
    Provenance,
)
from app.services.weather.client import OpenMeteoClient
from app.services.weather.exceptions import (
    InvalidCoordinatesError,
    WeatherAdapterError,
)
from app.services.weather.models import SupplementaryDailyWeather, WeatherResult

logger = logging.getLogger("terrapulse.weather.adapter")

DEFAULT_DAILY_FORECAST_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
    "shortwave_radiation_sum",
    "relative_humidity_2m_mean",
]

DEFAULT_DAILY_ENSEMBLE_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
    "shortwave_radiation_sum",
]


def normalize_member_id(raw_member: str) -> str:
    """Normalize raw member identifiers like 'member01', 'member_1', 'member-01' to 'member-01'."""
    cleaned = raw_member.strip().lower()
    m = re.match(r"^member[-_]?(\d+)$", cleaned)
    if m:
        return f"member-{int(m.group(1)):02d}"
    return cleaned.replace("_", "-")


def _build_measurement(
    val: float | None,
    unit: str,
    variable_name: str,
    min_val: float | None = None,
    max_val: float | None = None,
) -> Measurement:
    """Safely build a C1 Measurement ensuring missing data never becomes zero and units are preserved."""
    if val is None:
        return Measurement(
            value=None,
            unit=unit,
            availability=Availability(
                status=DataStatus.MISSING,
                reason=f"{variable_name} missing from provider",
            ),
        )
    try:
        num_val = float(val)
    except (ValueError, TypeError):
        return Measurement(
            value=None,
            unit=unit,
            availability=Availability(
                status=DataStatus.INVALID,
                reason=f"Unparseable numeric value '{val}' for {variable_name}",
            ),
        )

    if (min_val is not None and num_val < min_val) or (max_val is not None and num_val > max_val):
        return Measurement(
            value=None,
            unit=unit,
            availability=Availability(
                status=DataStatus.INVALID,
                reason=f"{variable_name} value {num_val} exceeds physical bounds [{min_val}, {max_val}]",
            ),
        )

    return Measurement(
        value=round(num_val, 3),
        unit=unit,
        availability=Availability(status=DataStatus.AVAILABLE),
    )


class OpenMeteoWeatherAdapter:
    """Adapter for retrieving and normalizing weather and ensemble forecast data from Open-Meteo.

    Normalizes data into C1-compliant DailyWeather records, preserves individual ensemble member
    identities and timestamps, and guarantees independent error resilience between deterministic
    and ensemble requests.
    """

    def __init__(self, client: OpenMeteoClient | None = None) -> None:
        self.client = client or OpenMeteoClient()

    def _validate_coordinates(self, latitude: float, longitude: float) -> None:
        """Validate latitude and longitude against geographic WGS 84 bounds."""
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise InvalidCoordinatesError(
                f"Coordinates out of bounds: latitude={latitude} must be in [-90, 90], "
                f"longitude={longitude} must be in [-180, 180]."
            )

    def _parse_deterministic(
        self, payload: dict[str, Any]
    ) -> tuple[list[DailyWeather], list[SupplementaryDailyWeather]]:
        """Parse Open-Meteo /v1/forecast daily data into C1 DailyWeather and SupplementaryDailyWeather."""
        daily = payload.get("daily", {})
        times = daily.get("time", [])
        num_records = len(times)

        t_min_list = daily.get("temperature_2m_min", [None] * num_records)
        t_max_list = daily.get("temperature_2m_max", [None] * num_records)
        precip_list = daily.get("precipitation_sum", daily.get("rain_sum", [None] * num_records))
        et0_list = daily.get("et0_fao_evapotranspiration", [None] * num_records)

        rh_list = daily.get("relative_humidity_2m_mean", [None] * num_records)
        wind_spd_list = daily.get("wind_speed_10m_max", [None] * num_records)
        wind_dir_list = daily.get("wind_direction_10m_dominant", [None] * num_records)
        rad_list = daily.get("shortwave_radiation_sum", [None] * num_records)

        daily_records: list[DailyWeather] = []
        supplementary_records: list[SupplementaryDailyWeather] = []

        for i, t_str in enumerate(times):
            day_date = date.fromisoformat(t_str)

            m_tmin = _build_measurement(
                t_min_list[i] if i < len(t_min_list) else None,
                unit="degC",
                variable_name="temperatureMinC",
                min_val=-90.0,
                max_val=60.0,
            )
            m_tmax = _build_measurement(
                t_max_list[i] if i < len(t_max_list) else None,
                unit="degC",
                variable_name="temperatureMaxC",
                min_val=-90.0,
                max_val=60.0,
            )
            m_rain = _build_measurement(
                precip_list[i] if i < len(precip_list) else None,
                unit="mm",
                variable_name="rainfallMm",
                min_val=0.0,
                max_val=2000.0,
            )
            m_et0 = _build_measurement(
                et0_list[i] if i < len(et0_list) else None,
                unit="mm",
                variable_name="referenceEvapotranspirationMm",
                min_val=0.0,
                max_val=100.0,
            )

            daily_records.append(
                DailyWeather(
                    date=day_date,
                    temperatureMinC=m_tmin,
                    temperatureMaxC=m_tmax,
                    rainfallMm=m_rain,
                    referenceEvapotranspirationMm=m_et0,
                    ensembleMemberId=None,
                )
            )

            m_rh = _build_measurement(
                rh_list[i] if i < len(rh_list) else None,
                unit="%",
                variable_name="relativeHumidityMean",
                min_val=0.0,
                max_val=100.0,
            )
            m_wind_spd = _build_measurement(
                wind_spd_list[i] if i < len(wind_spd_list) else None,
                unit="km/h",
                variable_name="windSpeedMax",
                min_val=0.0,
                max_val=300.0,
            )
            m_wind_dir = _build_measurement(
                wind_dir_list[i] if i < len(wind_dir_list) else None,
                unit="deg",
                variable_name="windDirectionDominant",
                min_val=0.0,
                max_val=360.0,
            )
            m_rad = _build_measurement(
                rad_list[i] if i < len(rad_list) else None,
                unit="MJ/m2",
                variable_name="shortwaveRadiationSum",
                min_val=0.0,
                max_val=100.0,
            )

            supplementary_records.append(
                SupplementaryDailyWeather(
                    date=day_date,
                    ensembleMemberId=None,
                    relativeHumidityMean=m_rh,
                    windSpeedMax=m_wind_spd,
                    windDirectionDominant=m_wind_dir,
                    shortwaveRadiationSum=m_rad,
                )
            )

        return daily_records, supplementary_records

    def _parse_ensemble(
        self, payload: dict[str, Any]
    ) -> tuple[dict[str, list[DailyWeather]], dict[str, list[SupplementaryDailyWeather]]]:
        """Parse Open-Meteo /v1/ensemble daily data into member-mapped DailyWeather and SupplementaryDailyWeather."""
        daily = payload.get("daily", {})
        times = daily.get("time", [])

        # Detect all member suffixes
        member_suffixes: set[str] = set()
        member_pattern = re.compile(r"^(.+)_(member[-_]?\d+|control|mean)$", re.IGNORECASE)

        for key in daily:
            match = member_pattern.match(key)
            if match:
                member_suffixes.add(match.group(2))

        # If no explicit member suffixes found, check if control or standalone exists
        if not member_suffixes:
            # Fallback for single-member ensemble or control run
            member_suffixes.add("member01")

        # Map suffixes to normalized member IDs
        normalized_map = {suffix: normalize_member_id(suffix) for suffix in member_suffixes}
        # Sort member IDs for deterministic ordering
        sorted_suffixes = sorted(member_suffixes, key=lambda s: normalized_map[s])

        ensemble_members: dict[str, list[DailyWeather]] = {}
        ensemble_supp: dict[str, list[SupplementaryDailyWeather]] = {}

        for suffix in sorted_suffixes:
            norm_id = normalized_map[suffix]
            m_records: list[DailyWeather] = []
            m_supp: list[SupplementaryDailyWeather] = []

            # Retrieve member-specific lists
            t_min_list = daily.get(f"temperature_2m_min_{suffix}", daily.get("temperature_2m_min"))
            t_max_list = daily.get(f"temperature_2m_max_{suffix}", daily.get("temperature_2m_max"))
            precip_list = daily.get(
                f"precipitation_sum_{suffix}",
                daily.get(f"rain_sum_{suffix}", daily.get("precipitation_sum")),
            )
            et0_list = daily.get(
                f"et0_fao_evapotranspiration_{suffix}", daily.get("et0_fao_evapotranspiration")
            )

            rh_list = daily.get(
                f"relative_humidity_2m_mean_{suffix}", daily.get("relative_humidity_2m_mean")
            )
            wind_spd_list = daily.get(
                f"wind_speed_10m_max_{suffix}", daily.get("wind_speed_10m_max")
            )
            wind_dir_list = daily.get(
                f"wind_direction_10m_dominant_{suffix}", daily.get("wind_direction_10m_dominant")
            )
            rad_list = daily.get(
                f"shortwave_radiation_sum_{suffix}", daily.get("shortwave_radiation_sum")
            )

            for i, t_str in enumerate(times):
                day_date = date.fromisoformat(t_str)

                # Check partial forecast arrays
                v_tmin = t_min_list[i] if t_min_list and i < len(t_min_list) else None
                v_tmax = t_max_list[i] if t_max_list and i < len(t_max_list) else None
                v_precip = precip_list[i] if precip_list and i < len(precip_list) else None
                v_et0 = et0_list[i] if et0_list and i < len(et0_list) else None

                m_tmin = _build_measurement(
                    v_tmin,
                    unit="degC",
                    variable_name=f"temperatureMinC_{norm_id}",
                    min_val=-90.0,
                    max_val=60.0,
                )
                m_tmax = _build_measurement(
                    v_tmax,
                    unit="degC",
                    variable_name=f"temperatureMaxC_{norm_id}",
                    min_val=-90.0,
                    max_val=60.0,
                )
                m_rain = _build_measurement(
                    v_precip,
                    unit="mm",
                    variable_name=f"rainfallMm_{norm_id}",
                    min_val=0.0,
                    max_val=2000.0,
                )
                m_et0 = _build_measurement(
                    v_et0,
                    unit="mm",
                    variable_name=f"referenceEvapotranspirationMm_{norm_id}",
                    min_val=0.0,
                    max_val=100.0,
                )

                m_records.append(
                    DailyWeather(
                        date=day_date,
                        temperatureMinC=m_tmin,
                        temperatureMaxC=m_tmax,
                        rainfallMm=m_rain,
                        referenceEvapotranspirationMm=m_et0,
                        ensembleMemberId=norm_id,
                    )
                )

                v_rh = rh_list[i] if rh_list and i < len(rh_list) else None
                v_wind_spd = (
                    wind_spd_list[i] if wind_spd_list and i < len(wind_spd_list) else None
                )
                v_wind_dir = (
                    wind_dir_list[i] if wind_dir_list and i < len(wind_dir_list) else None
                )
                v_rad = rad_list[i] if rad_list and i < len(rad_list) else None

                m_rh = _build_measurement(
                    v_rh,
                    unit="%",
                    variable_name=f"relativeHumidityMean_{norm_id}",
                    min_val=0.0,
                    max_val=100.0,
                )
                m_wind_spd = _build_measurement(
                    v_wind_spd,
                    unit="km/h",
                    variable_name=f"windSpeedMax_{norm_id}",
                    min_val=0.0,
                    max_val=300.0,
                )
                m_wind_dir = _build_measurement(
                    v_wind_dir,
                    unit="deg",
                    variable_name=f"windDirectionDominant_{norm_id}",
                    min_val=0.0,
                    max_val=360.0,
                )
                m_rad = _build_measurement(
                    v_rad,
                    unit="MJ/m2",
                    variable_name=f"shortwaveRadiationSum_{norm_id}",
                    min_val=0.0,
                    max_val=100.0,
                )

                m_supp.append(
                    SupplementaryDailyWeather(
                        date=day_date,
                        ensembleMemberId=norm_id,
                        relativeHumidityMean=m_rh,
                        windSpeedMax=m_wind_spd,
                        windDirectionDominant=m_wind_dir,
                        shortwaveRadiationSum=m_rad,
                    )
                )

            ensemble_members[norm_id] = m_records
            ensemble_supp[norm_id] = m_supp

        return ensemble_members, ensemble_supp

    async def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "Asia/Kolkata",
        start_date: date | None = None,
        end_date: date | None = None,
        past_days: int | None = None,
        forecast_days: int = 7,
        include_ensemble: bool = True,
        ensemble_models: list[str] | None = None,
    ) -> WeatherResult:
        """Fetch deterministic and ensemble weather data, normalizing into C1 data contracts.

        Args:
            latitude: Latitude coordinate between -90.0 and 90.0 (WGS 84).
            longitude: Longitude coordinate between -180.0 and 180.0 (WGS 84).
            timezone: Timezone string (default 'Asia/Kolkata').
            start_date: Optional start date for simulation or forecast window.
            end_date: Optional end date for simulation or forecast window.
            past_days: Optional number of historical days to include.
            forecast_days: Number of forecast days (default 7).
            include_ensemble: Whether to query the Open-Meteo ensemble endpoint.
            ensemble_models: Optional specific ensemble models (e.g. ['gfs_seamless']).

        Returns:
            WeatherResult containing C1 DailyWeather records, member forecasts, and provenance.
        """
        self._validate_coordinates(latitude, longitude)
        retrieved_at = datetime.now(UTC)

        coords = Coordinates(latitude=latitude, longitude=longitude, crs="EPSG:4326")

        # Build forecast query parameters
        forecast_params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "daily": ",".join(DEFAULT_DAILY_FORECAST_VARIABLES),
        }
        if start_date and end_date:
            forecast_params["start_date"] = start_date.isoformat()
            forecast_params["end_date"] = end_date.isoformat()
        else:
            forecast_params["forecast_days"] = forecast_days
            if past_days:
                forecast_params["past_days"] = past_days

        # Build ensemble query parameters
        ensemble_params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "daily": ",".join(DEFAULT_DAILY_ENSEMBLE_VARIABLES),
        }
        if start_date and end_date:
            ensemble_params["start_date"] = start_date.isoformat()
            ensemble_params["end_date"] = end_date.isoformat()
        else:
            ensemble_params["forecast_days"] = forecast_days
            if past_days:
                ensemble_params["past_days"] = past_days

        if ensemble_models:
            ensemble_params["models"] = ",".join(ensemble_models)

        # Launch requests concurrently with fault isolation
        tasks = [self.client.fetch_forecast(forecast_params)]
        if include_ensemble:
            tasks.append(self.client.fetch_ensemble(ensemble_params))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        forecast_res = results[0]
        ensemble_res = results[1] if include_ensemble else None

        # If both failed with exceptions, raise the primary error
        if isinstance(forecast_res, Exception) and (
            not include_ensemble or isinstance(ensemble_res, Exception)
        ):
            if isinstance(forecast_res, WeatherAdapterError):
                raise forecast_res
            raise WeatherAdapterError(f"Weather retrieval failed: {forecast_res}") from forecast_res

        # Process deterministic forecast
        deterministic_daily: list[DailyWeather] = []
        deterministic_supp: list[SupplementaryDailyWeather] = []
        deterministic_available = True
        deterministic_error: str | None = None
        elevation_m: float | None = None
        raw_metadata: dict[str, Any] = {}

        if isinstance(forecast_res, Exception):
            deterministic_available = False
            deterministic_error = str(forecast_res)
            logger.warning("Deterministic weather request failed: %s", forecast_res)
        elif isinstance(forecast_res, dict):
            elevation_m = forecast_res.get("elevation")
            raw_metadata["forecast_generationtime_ms"] = forecast_res.get("generationtime_ms")
            deterministic_daily, deterministic_supp = self._parse_deterministic(forecast_res)

        # Process ensemble forecast
        ensemble_members: dict[str, list[DailyWeather]] = {}
        ensemble_supp: dict[str, list[SupplementaryDailyWeather]] = {}
        ensemble_available = include_ensemble
        ensemble_error: str | None = None

        if include_ensemble:
            if isinstance(ensemble_res, Exception):
                ensemble_available = False
                ensemble_error = str(ensemble_res)
                logger.warning("Ensemble weather request failed: %s", ensemble_res)
            elif isinstance(ensemble_res, dict):
                raw_metadata["ensemble_generationtime_ms"] = ensemble_res.get("generationtime_ms")
                ensemble_members, ensemble_supp = self._parse_ensemble(ensemble_res)

        # Construct Provenance and Data Source IDs
        provenance: list[Provenance] = []
        data_source_ids: list[str] = []

        if deterministic_available:
            data_source_ids.append("open-meteo:forecast")
            provenance.append(
                Provenance(
                    sourceId="open-meteo:forecast",
                    sourceVersion="v1",
                    retrievedAt=retrieved_at,
                    reference="https://open-meteo.com/en/docs",
                )
            )

        if ensemble_available and ensemble_members:
            data_source_ids.append("open-meteo:ensemble")
            model_ver = ",".join(ensemble_models) if ensemble_models else "gfs_seamless"
            provenance.append(
                Provenance(
                    sourceId="open-meteo:ensemble",
                    sourceVersion=model_ver,
                    retrievedAt=retrieved_at,
                    reference="https://open-meteo.com/en/docs/ensemble-api",
                )
            )

        return WeatherResult(
            location=coords,
            timezone=timezone,
            elevationM=elevation_m,
            retrievedAt=retrieved_at,
            deterministicDaily=deterministic_daily,
            deterministicSupplementary=deterministic_supp,
            deterministicAvailable=deterministic_available,
            deterministicError=deterministic_error,
            ensembleMembers=ensemble_members,
            ensembleSupplementary=ensemble_supp,
            ensembleAvailable=ensemble_available,
            ensembleError=ensemble_error,
            dataSourceIds=data_source_ids,
            provenance=provenance,
            rawMetadata=raw_metadata,
        )
