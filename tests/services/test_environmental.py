from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
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
from app.services.environmental import (
    EnvironmentalInputRequest,
    EnvironmentalInputService,
    InvalidCoordinatesError,
)
from app.services.soil import (
    SoilGridsAdapter,
    SoilProviderError,
    SoilResult,
)
from app.services.weather import (
    OpenMeteoWeatherAdapter,
    WeatherProviderError,
    WeatherResult,
)

FIXTURES_PATH = (
    Path(__file__).parents[2] / "packages" / "contracts" / "fixtures" / "c1.json"
)
SAMPLE_C1_FIXTURE = json.loads(FIXTURES_PATH.read_text())

SAMPLE_FARM_ID = UUID("00000000-0000-0000-0000-000000000001")
TURMERIC_CROP_ID = UUID("00000000-0000-0000-0000-000000000003")
MAIZE_CROP_ID = UUID("00000000-0000-0000-0000-000000000010")
COTTON_CROP_ID = UUID("00000000-0000-0000-0000-000000000050")


def _build_test_daily_weather(
    day: date,
    temp_min: float | None = 22.0,
    temp_max: float | None = 31.0,
    rainfall: float | None = 0.0,
    et0: float | None = 4.2,
    member_id: str | None = None,
) -> DailyWeather:
    return DailyWeather(
        date=day,
        temperature_min_c=Measurement(
            value=temp_min,
            unit="degC",
            availability=Availability(
                status=DataStatus.AVAILABLE
                if temp_min is not None
                else DataStatus.MISSING
            ),
        ),
        temperature_max_c=Measurement(
            value=temp_max,
            unit="degC",
            availability=Availability(
                status=DataStatus.AVAILABLE
                if temp_max is not None
                else DataStatus.MISSING
            ),
        ),
        rainfall_mm=Measurement(
            value=rainfall,
            unit="mm",
            availability=Availability(
                status=DataStatus.AVAILABLE
                if rainfall is not None
                else DataStatus.MISSING
            ),
        ),
        reference_evapotranspiration_mm=Measurement(
            value=et0,
            unit="mm",
            availability=Availability(
                status=DataStatus.AVAILABLE if et0 is not None else DataStatus.MISSING
            ),
        )
        if et0 is not None
        else None,
        ensemble_member_id=member_id,
    )


def _build_test_weather_result(
    start_date: date,
    end_date: date,
    temp_min: float | None = 22.0,
    temp_max: float | None = 31.0,
    rainfall: float | None = 0.0,
    et0: float | None = 4.2,
    include_ensemble: bool = True,
) -> WeatherResult:
    now = datetime.now(UTC)
    dates = [start_date, end_date]

    det_records = [
        _build_test_daily_weather(d, temp_min, temp_max, rainfall, et0, member_id=None)
        for d in dates
    ]

    ensemble_members: dict[str, list[DailyWeather]] = {}
    if include_ensemble:
        ensemble_members["member-01"] = [
            _build_test_daily_weather(
                d, temp_min, temp_max, rainfall, et0, member_id="member-01"
            )
            for d in dates
        ]
        m2_tmin = (temp_min + 1.0) if temp_min is not None else None
        m2_tmax = (temp_max + 1.5) if temp_max is not None else None
        m2_rain = (rainfall + 2.0) if rainfall is not None else None
        ensemble_members["member-02"] = [
            _build_test_daily_weather(
                d, m2_tmin, m2_tmax, m2_rain, et0, member_id="member-02"
            )
            for d in dates
        ]

    return WeatherResult(
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        retrieved_at=now,
        deterministic_daily=det_records,
        deterministic_available=True,
        ensemble_members=ensemble_members,
        ensemble_available=include_ensemble,
        data_source_ids=["open-meteo:forecast", "open-meteo:ensemble"],
        provenance=[
            Provenance(
                source_id="open-meteo:forecast",
                source_version="1.0",
                retrieved_at=now,
                reference="Open-Meteo Weather Forecast API",
            ),
            Provenance(
                source_id="open-meteo:ensemble",
                source_version="1.0",
                retrieved_at=now,
                reference="Open-Meteo Weather Ensemble API",
            ),
        ],
    )


def _build_test_soil_result(
    depth: float | None = 30.0,
    fc: float | None = 0.28,
    wp: float | None = 0.12,
    texture: str | None = "loam",
) -> SoilResult:
    now = datetime.now(UTC)
    soil_props = SoilProperties(
        depth_cm=Measurement(
            value=depth,
            unit="cm",
            availability=Availability(
                status=DataStatus.AVAILABLE if depth is not None else DataStatus.MISSING
            ),
        ),
        texture=texture,
        field_capacity=Measurement(
            value=fc,
            unit="m3/m3",
            availability=Availability(
                status=DataStatus.AVAILABLE if fc is not None else DataStatus.MISSING
            ),
        ),
        wilting_point=Measurement(
            value=wp,
            unit="m3/m3",
            availability=Availability(
                status=DataStatus.AVAILABLE if wp is not None else DataStatus.MISSING
            ),
        ),
        bulk_density=None,
    )
    return SoilResult(
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        profile_depth_cm=depth or 30.0,
        soil_properties=soil_props,
        data_source_ids=["isric-soilgrids"],
        provenance=[
            Provenance(
                source_id="isric-soilgrids",
                source_version="2.0",
                retrieved_at=now,
                reference="ISRIC SoilGrids 250m v2.0 (modelled/gridded predictions, not in-situ field measurements)",
            )
        ],
        retrieved_at=now,
        availability=Availability(status=DataStatus.AVAILABLE),
    )


def _setup_service(
    weather_result: WeatherResult | None = None,
    soil_result: SoilResult | None = None,
    weather_error: Exception | None = None,
    soil_error: Exception | None = None,
) -> EnvironmentalInputService:
    weather_mock = AsyncMock(spec=OpenMeteoWeatherAdapter)
    if weather_error:
        weather_mock.fetch_weather.side_effect = weather_error
    else:
        weather_mock.fetch_weather.return_value = (
            weather_result
            or _build_test_weather_result(date(2026, 6, 1), date(2026, 6, 2))
        )

    soil_mock = AsyncMock(spec=SoilGridsAdapter)
    if soil_error:
        soil_mock.fetch_soil.side_effect = soil_error
    else:
        soil_mock.fetch_soil.return_value = (
            soil_result or _build_test_soil_result()
        )

    return EnvironmentalInputService(
        weather_adapter=weather_mock,
        soil_adapter=soil_mock,
    )


# --- 1. Valid Complete Environmental Input ---
@pytest.mark.asyncio
async def test_valid_complete_environmental_input():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
        requested_outputs=["actualEvapotranspiration", "waterStress"],
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is True
    assert res.status == DataStatus.AVAILABLE
    assert len(res.errors) == 0
    assert len(res.missing_fields) == 0
    assert len(res.unsupported_outputs) == 0
    assert res.freshness == "live"

    c1 = res.c1_input
    assert c1 is not None
    assert c1.contract_version == "1.0"
    assert c1.farm_id == SAMPLE_FARM_ID
    assert c1.availability.status == DataStatus.AVAILABLE
    assert len(c1.daily_weather) == 2
    assert c1.soil.depth_cm.value == 30.0
    assert c1.soil.field_capacity.value == 0.28
    assert c1.soil.wilting_point.value == 0.12

    # Second invocation with same params must leverage cache
    res_cached = await service.prepare_environmental_input(req)
    assert res_cached.is_valid is True
    assert res_cached.freshness.startswith("cached")


# --- 2. Missing Mandatory Weather Data ---
@pytest.mark.asyncio
async def test_missing_mandatory_weather_data():
    weather_res = _build_test_weather_result(
        date(2026, 6, 1),
        date(2026, 6, 2),
        temp_min=None,  # Missing minimum temperature
    )
    service = _setup_service(weather_result=weather_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.MISSING
    assert any("temperature_min_c" in mf for mf in res.missing_fields)
    assert any("never zeroed" in err for err in res.errors)

    # Missing value must NEVER be converted to zero
    assert res.c1_input is not None
    d1 = res.c1_input.daily_weather[0]
    assert d1.temperature_min_c.value is None
    assert d1.temperature_min_c.value != 0.0
    assert d1.temperature_min_c.availability.status == DataStatus.MISSING


# --- 3. Missing Mandatory Soil Data ---
@pytest.mark.asyncio
async def test_missing_mandatory_soil_data():
    soil_res = _build_test_soil_result(fc=None)  # Missing field capacity
    service = _setup_service(soil_result=soil_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.MISSING
    assert "soil.field_capacity" in res.missing_fields
    assert res.c1_input is not None
    assert res.c1_input.soil.field_capacity.value is None
    assert res.c1_input.soil.field_capacity.value != 0.0
    assert res.c1_input.availability.status == DataStatus.MISSING


# --- 4. Invalid Physical Values (Temperature T_min > T_max) ---
@pytest.mark.asyncio
async def test_invalid_physical_values_temperature():
    weather_res = _build_test_weather_result(
        date(2026, 6, 1),
        date(2026, 6, 2),
        temp_min=35.0,
        temp_max=25.0,  # T_min > T_max
    )
    service = _setup_service(weather_result=weather_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.INVALID
    assert any("temperature_min (35.0°C) > temperature_max (25.0°C)" in err for err in res.errors)


# --- 5. Invalid Physical Values (Soil FC < WP) ---
@pytest.mark.asyncio
async def test_invalid_physical_values_soil():
    soil_res = _build_test_soil_result(fc=0.10, wp=0.25)  # FC < WP
    service = _setup_service(soil_result=soil_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.INVALID
    assert any("field capacity (0.1 m3/m3) cannot be less than wilting point (0.25 m3/m3)" in err for err in res.errors)


# --- 6. Invalid Physical Values (Negative Rainfall) ---
@pytest.mark.asyncio
async def test_invalid_physical_values_negative_rainfall():
    weather_res = _build_test_weather_result(
        date(2026, 6, 1),
        date(2026, 6, 2),
        rainfall=-5.0,  # Negative rainfall
    )
    service = _setup_service(weather_result=weather_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.INVALID
    assert any("rainfall (-5.0 mm) cannot be negative" in err for err in res.errors)


# --- 7. Invalid Location Coordinates ---
@pytest.mark.asyncio
async def test_invalid_location_coordinates():
    service = _setup_service()

    with pytest.raises(InvalidCoordinatesError):
        await service.prepare(
            farm_id=SAMPLE_FARM_ID,
            latitude=95.0,  # Latitude > 90
            longitude=75.0,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
        )

    with pytest.raises(InvalidCoordinatesError):
        await service.prepare(
            farm_id=SAMPLE_FARM_ID,
            latitude=15.0,
            longitude=-185.0,  # Longitude < -180
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
        )


# --- 8. Unsupported Crop Capability (identity/ecology-only) ---
@pytest.mark.asyncio
async def test_unsupported_crop_capability():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=COTTON_CROP_ID,  # Cotton is identity/ecology-only
        require_quantitative_simulation=True,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.UNSUPPORTED
    assert any("uses engine 'identity/ecology-only' which does not support quantitative simulation" in err for err in res.errors)


# --- 9. Unsupported Requested Outputs ---
@pytest.mark.asyncio
async def test_unsupported_requested_outputs():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
        # Turmeric only supports: actualEvapotranspiration, waterStress, irrigation
        requested_outputs=["actualEvapotranspiration", "yield", "canopyCover"],
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.UNSUPPORTED
    assert "yield" in res.unsupported_outputs
    assert "canopyCover" in res.unsupported_outputs
    assert any("output 'yield' is not supported" in err for err in res.errors)
    assert any("output 'canopyCover' is not supported" in err for err in res.errors)


# --- 10. Partial Weather-Provider Failure ---
@pytest.mark.asyncio
async def test_partial_weather_provider_failure():
    service = _setup_service(
        weather_error=WeatherProviderError(status_code=500, message="Open-Meteo down"),
        soil_result=_build_test_soil_result(),
    )
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.MISSING
    assert any("Weather data retrieval failed" in err for err in res.errors)
    # Soil data must remain available and uncorrupted
    assert res.soil_result is not None
    assert res.c1_input is not None
    assert res.c1_input.soil.field_capacity.value == 0.28


# --- 11. Partial Soil-Provider Failure ---
@pytest.mark.asyncio
async def test_partial_soil_provider_failure():
    service = _setup_service(
        weather_result=_build_test_weather_result(date(2026, 6, 1), date(2026, 6, 2)),
        soil_error=SoilProviderError(status_code=503, message="ISRIC SoilGrids down"),
    )
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert res.status == DataStatus.MISSING
    assert any("Soil data retrieval failed" in err for err in res.errors)
    # Weather data must remain available and uncorrupted
    assert res.weather_result is not None
    assert res.c1_input is not None
    assert len(res.c1_input.daily_weather) == 2
    # Fallback soil has MISSING status
    assert res.c1_input.soil.field_capacity.availability.status == DataStatus.MISSING
    assert res.c1_input.soil.field_capacity.value is None


# --- 12. Ensemble Member Preservation ---
@pytest.mark.asyncio
async def test_ensemble_member_preservation():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
        weather_member_id="member-01",
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is True
    assert res.c1_input is not None
    assert len(res.c1_input.daily_weather) == 2
    for dw in res.c1_input.daily_weather:
        assert dw.ensemble_member_id == "member-01"

    # Non-existent member reports clear error
    req_bad_member = req.model_copy(update={"weather_member_id": "member-99"})
    res_bad = await service.prepare_environmental_input(req_bad_member)
    assert res_bad.is_valid is False
    assert any("Requested ensemble member 'member-99'" in err for err in res_bad.errors)


@pytest.mark.asyncio
async def test_multiple_distinct_ensemble_members_preserved():
    d1 = date(2026, 6, 1)
    d2 = date(2026, 6, 2)
    m1_records = [
        _build_test_daily_weather(d1, temp_min=18.0, temp_max=28.0, rainfall=0.0, member_id="member-01"),
        _build_test_daily_weather(d2, temp_min=19.0, temp_max=29.0, rainfall=2.0, member_id="member-01"),
    ]
    m2_records = [
        _build_test_daily_weather(d1, temp_min=24.0, temp_max=36.0, rainfall=15.0, member_id="member-02"),
        _build_test_daily_weather(d2, temp_min=25.0, temp_max=37.5, rainfall=20.0, member_id="member-02"),
    ]
    weather_res = WeatherResult(
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        retrieved_at=datetime.now(UTC),
        deterministic_daily=[],
        deterministic_available=False,
        ensemble_members={"member-01": m1_records, "member-02": m2_records},
        ensemble_available=True,
        data_source_ids=["open-meteo:ensemble"],
        provenance=[],
    )
    service = _setup_service(weather_result=weather_res)

    req_m1 = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(start_date=d1, end_date=d2),
        crop_id=TURMERIC_CROP_ID,
        weather_member_id="member-01",
    )
    req_m2 = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(start_date=d1, end_date=d2),
        crop_id=TURMERIC_CROP_ID,
        weather_member_id="member-02",
    )

    res_m1 = await service.prepare_environmental_input(req_m1)
    res_m2 = await service.prepare_environmental_input(req_m2)

    assert res_m1.is_valid is True
    assert res_m2.is_valid is True
    assert res_m1.c1_input is not None
    assert res_m2.c1_input is not None

    # Assert requested member IDs are preserved
    for dw in res_m1.c1_input.daily_weather:
        assert dw.ensemble_member_id == "member-01"
    for dw in res_m2.c1_input.daily_weather:
        assert dw.ensemble_member_id == "member-02"

    # Assert exact daily values are preserved
    assert res_m1.c1_input.daily_weather[0].temperature_max_c.value == 28.0
    assert res_m1.c1_input.daily_weather[0].rainfall_mm.value == 0.0
    assert res_m2.c1_input.daily_weather[0].temperature_max_c.value == 36.0
    assert res_m2.c1_input.daily_weather[0].rainfall_mm.value == 15.0

    assert res_m1.c1_input.daily_weather[1].temperature_max_c.value == 29.0
    assert res_m1.c1_input.daily_weather[1].rainfall_mm.value == 2.0
    assert res_m2.c1_input.daily_weather[1].temperature_max_c.value == 37.5
    assert res_m2.c1_input.daily_weather[1].rainfall_mm.value == 20.0

    # Assert distinct values and no averaging or blending
    assert res_m1.c1_input.daily_weather[0].temperature_max_c.value != res_m2.c1_input.daily_weather[0].temperature_max_c.value
    assert res_m1.c1_input.daily_weather[0].rainfall_mm.value != res_m2.c1_input.daily_weather[0].rainfall_mm.value
    assert res_m1.c1_input.daily_weather[0].temperature_max_c.value != 32.0  # Not (28 + 36)/2
    assert res_m1.c1_input.daily_weather[0].rainfall_mm.value != 7.5        # Not (0 + 15)/2


@pytest.mark.asyncio
async def test_cache_bounding_lru_eviction():
    service = _setup_service()
    service.max_cache_entries = 2
    service.cache_ttl_seconds = 100

    base_req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)),
        crop_id=TURMERIC_CROP_ID,
    )

    req1 = base_req.model_copy(update={"location": Coordinates(latitude=15.3171, longitude=75.7139, crs="EPSG:4326")})
    req2 = base_req.model_copy(update={"location": Coordinates(latitude=15.3172, longitude=75.7139, crs="EPSG:4326")})
    req3 = base_req.model_copy(update={"location": Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326")})

    # Prepare req1, req2
    res1 = await service.prepare_environmental_input(req1)
    res2 = await service.prepare_environmental_input(req2)
    assert res1.is_valid is True
    assert res2.is_valid is True
    assert len(service._cache) == 2

    # Access req1 to refresh its recency
    cached_req1 = await service.prepare_environmental_input(req1)
    assert cached_req1.freshness.startswith("cached")

    # Prepare req3 -> capacity exceeded, least recently used (req2) must be evicted
    res3 = await service.prepare_environmental_input(req3)
    assert res3.is_valid is True
    assert len(service._cache) == 2
    # req1 and req3 remain, req2 was evicted
    assert any("15.3171" in k for k in service._cache)
    assert any("15.3173" in k for k in service._cache)
    assert not any("15.3172" in k for k in service._cache)


# --- 13. Soil Provenance and Depth Preservation ---
@pytest.mark.asyncio
async def test_soil_provenance_and_depth_preservation():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
        soil_target_depth_cm=30.0,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is True
    c1 = res.c1_input
    assert c1 is not None

    # Verify data sources contain both weather and soil
    assert "open-meteo:forecast" in c1.data_source_ids
    assert "isric-soilgrids" in c1.data_source_ids

    # Verify SoilGrids is identified as modelled/gridded estimates
    soilgrids_prov = next((p for p in c1.provenance if p.source_id == "isric-soilgrids"), None)
    assert soilgrids_prov is not None
    assert "modelled/gridded predictions, not in-situ field measurements" in (soilgrids_prov.reference or "")
    assert c1.soil.depth_cm.value == 30.0
    assert c1.soil.depth_cm.unit == "cm"


# --- 14. Missing Values Never Converted to Zero ---
@pytest.mark.asyncio
async def test_missing_values_never_converted_to_zero():
    weather_res = _build_test_weather_result(
        date(2026, 6, 1),
        date(2026, 6, 2),
        rainfall=None,  # Provider returned null rainfall
    )
    service = _setup_service(weather_result=weather_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.c1_input is not None
    for dw in res.c1_input.daily_weather:
        assert dw.rainfall_mm.value is None
        assert dw.rainfall_mm.value != 0
        assert dw.rainfall_mm.value != 0.0
        assert dw.rainfall_mm.availability.status == DataStatus.MISSING


# --- 15. Correct C1 Contract Serialization ---
@pytest.mark.asyncio
async def test_c1_contract_serialization():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.c1_input is not None
    dumped = res.c1_input.model_dump(by_alias=True, mode="json")

    # Match fixture schema keys exactly
    fixture_keys = set(SAMPLE_C1_FIXTURE.keys())
    dumped_keys = set(dumped.keys())
    assert fixture_keys == dumped_keys

    # Re-validate dumped dictionary against C1EnvironmentalInput
    validated = C1EnvironmentalInput.model_validate(dumped)
    assert validated.farm_id == SAMPLE_FARM_ID
    assert validated.availability.status == DataStatus.AVAILABLE


# --- 16. Crop Query Ambiguity Handling ---
@pytest.mark.asyncio
async def test_crop_query_ambiguity_handling():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_query="millet",  # Matches Pearl Millet, Finger Millet, Foxtail Millet
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert any("ambiguous" in err for err in res.errors)
    assert any("Confirmation is required" in err or "confirmation" in err.lower() for err in res.errors)


# --- 17. Crop Query Exact Match Resolution ---
@pytest.mark.asyncio
async def test_crop_query_exact_match_resolution():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_query="turmeric",
        requested_outputs=["actualEvapotranspiration"],
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is True
    assert res.capability is not None
    assert res.capability.selected_engine == "FAO-56"
    assert res.capability.crop_id == TURMERIC_CROP_ID


# --- 18. Weather Dates Gap Detection ---
@pytest.mark.asyncio
async def test_weather_dates_gap_detection():
    # Only returns June 1 and June 3, leaving a gap on June 2
    d1 = _build_test_daily_weather(date(2026, 6, 1))
    d3 = _build_test_daily_weather(date(2026, 6, 3))
    weather_res = WeatherResult(
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        retrieved_at=datetime.now(UTC),
        deterministic_daily=[d1, d3],
        deterministic_available=True,
        data_source_ids=["open-meteo:forecast"],
        provenance=[],
    )

    service = _setup_service(weather_result=weather_res)
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is False
    assert "daily_weather:dates" in res.missing_fields
    assert any("2026-06-02" in err for err in res.errors)


# --- 19. AquaCrop Supported Crop (Maize) Execution ---
@pytest.mark.asyncio
async def test_maize_aquacrop_supported():
    service = _setup_service()
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=MAIZE_CROP_ID,
        requested_outputs=["canopyCover", "biomass", "yield"],
    )

    res = await service.prepare_environmental_input(req)

    assert res.is_valid is True
    assert res.capability is not None
    assert res.capability.selected_engine == "AquaCrop"
    assert len(res.unsupported_outputs) == 0
    assert len(res.errors) == 0


# --- 20. Plot ID Preservation and Cache Isolation ---
@pytest.mark.asyncio
async def test_plot_id_preserved_and_cache_isolated():
    service = _setup_service()
    plot_a = UUID("00000000-0000-0000-0000-0000000000aa")
    plot_b = UUID("00000000-0000-0000-0000-0000000000bb")

    req_a = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        plot_id=plot_a,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )
    req_b = req_a.model_copy(update={"plot_id": plot_b})

    res_a = await service.prepare_environmental_input(req_a)
    assert res_a.is_valid is True
    assert res_a.plot_id == plot_a
    assert res_a.c1_input is not None
    assert res_a.c1_input.farm_id == SAMPLE_FARM_ID
    # Verify C1EnvironmentalInput strictly lacks plot_id field
    assert "plot_id" not in C1EnvironmentalInput.model_fields
    assert "plotId" not in C1EnvironmentalInput.model_fields

    res_b = await service.prepare_environmental_input(req_b)
    assert res_b.is_valid is True
    assert res_b.plot_id == plot_b
    assert res_b.c1_input.farm_id == SAMPLE_FARM_ID

    # Both requests must exist as separate cache entries
    assert len(service._cache) == 2
    keys = list(service._cache.keys())
    assert any(str(plot_a) in k for k in keys)
    assert any(str(plot_b) in k for k in keys)


# --- 21. Soil Aggregation Depth Priority ---
@pytest.mark.asyncio
async def test_soil_aggregation_depth_priority():
    weather_mock = AsyncMock(spec=OpenMeteoWeatherAdapter)
    weather_mock.fetch_weather.return_value = _build_test_weather_result(
        date(2026, 6, 1), date(2026, 6, 2)
    )
    soil_mock = AsyncMock(spec=SoilGridsAdapter)
    soil_mock.fetch_soil.return_value = _build_test_soil_result()

    service = EnvironmentalInputService(
        weather_adapter=weather_mock,
        soil_adapter=soil_mock,
    )

    # Priority 1: Explicit caller depth overrides everything
    req_explicit = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=MAIZE_CROP_ID,
        soil_target_depth_cm=45.0,
    )
    await service.prepare_environmental_input(req_explicit)
    assert soil_mock.fetch_soil.call_args.kwargs["target_depth_cm"] == 45.0

    # Priority 2: Crop-specific max rooting depth from C7 capability (when caller depth is None)
    crop_cap = C7ModelCapability(
        contract_version="1.0",
        crop_id=MAIZE_CROP_ID,
        canonical_name="Maize",
        accepted_crop_names=["Maize"],
        scientific_name="Zea mays",
        selected_engine="AquaCrop",
        engine_version="3.1.0",
        supported_outputs=["yield"],
        model_parameters={"max_rooting_depth_m": 1.2},
        parameter_sources=[],
        parameter_versions=[],
        known_limitations=[],
        provenance_references=[],
    )
    depth_calc = service._determine_soil_target_depth_cm(None, crop_cap)
    assert depth_calc == 120.0

    # Also test with camelCase "maxRootingDepthM": 0.8 -> 80.0
    crop_cap_camel = crop_cap.model_copy(
        update={"model_parameters": {"maxRootingDepthM": "0.8"}}
    )
    assert service._determine_soil_target_depth_cm(None, crop_cap_camel) == 80.0

    # Priority 3: Default fallback of 30.0 cm when neither is provided
    crop_cap_none = crop_cap.model_copy(update={"model_parameters": {}})
    assert service._determine_soil_target_depth_cm(None, crop_cap_none) == 30.0
    assert service._determine_soil_target_depth_cm(None, None) == 30.0

    # Fallback when explicit depth <= 0
    assert service._determine_soil_target_depth_cm(0.0, crop_cap_none) == 30.0
    assert service._determine_soil_target_depth_cm(-5.0, crop_cap) == 120.0


# --- 22. Complete Weather Outage Dated Records ---
@pytest.mark.asyncio
async def test_complete_weather_outage_dated_records():
    weather_mock = AsyncMock(spec=OpenMeteoWeatherAdapter)
    weather_mock.fetch_weather.side_effect = WeatherProviderError(
        status_code=503, message="Open-Meteo Gateway Timeout"
    )
    soil_mock = AsyncMock(spec=SoilGridsAdapter)
    soil_mock.fetch_soil.return_value = _build_test_soil_result()

    service = EnvironmentalInputService(
        weather_adapter=weather_mock,
        soil_adapter=soil_mock,
    )

    start = date(2026, 6, 1)
    end = date(2026, 6, 5)  # 5 days
    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(start_date=start, end_date=end),
        crop_id=TURMERIC_CROP_ID,
    )

    res = await service.prepare_environmental_input(req)

    # Validation must fail and not cache
    assert res.is_valid is False
    assert res.status == DataStatus.MISSING
    assert len(service._cache) == 0
    assert any("outage" in err.lower() or "retrieval failed" in err.lower() for err in res.errors)

    # C1 input must be present with dated DailyWeather records for all 5 simulation days
    assert res.c1_input is not None
    daily = res.c1_input.daily_weather
    assert len(daily) == 5

    expected_dates = [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 3),
        date(2026, 6, 4),
        date(2026, 6, 5),
    ]
    assert [dw.date for dw in daily] == expected_dates

    # Check that measurements have value=None and status=MISSING (never 0)
    for dw in daily:
        assert dw.temperature_min_c.value is None
        assert dw.temperature_min_c.availability.status == DataStatus.MISSING
        assert dw.temperature_max_c.value is None
        assert dw.temperature_max_c.availability.status == DataStatus.MISSING
        assert dw.rainfall_mm.value is None
        assert dw.rainfall_mm.availability.status == DataStatus.MISSING
        assert dw.ensemble_member_id is None

    # Soil data should remain uncorrupted
    assert res.soil_result is not None
    assert res.c1_input.soil.field_capacity.value == 0.28

    # Serialization must succeed
    dumped = res.c1_input.model_dump(by_alias=True, mode="json")
    validated = C1EnvironmentalInput.model_validate(dumped)
    assert len(validated.daily_weather) == 5
    assert validated.availability.status == DataStatus.MISSING


# --- 23. Ensemble Batch Preparation Helper ---
@pytest.mark.asyncio
async def test_prepare_ensemble_batch_single_fetch_and_independent_trajectories():
    weather_mock = AsyncMock(spec=OpenMeteoWeatherAdapter)
    weather_mock.fetch_weather.return_value = _build_test_weather_result(
        date(2026, 6, 1), date(2026, 6, 2), include_ensemble=True
    )
    soil_mock = AsyncMock(spec=SoilGridsAdapter)
    soil_mock.fetch_soil.return_value = _build_test_soil_result()

    service = EnvironmentalInputService(
        weather_adapter=weather_mock,
        soil_adapter=soil_mock,
    )

    req = EnvironmentalInputRequest(
        farm_id=SAMPLE_FARM_ID,
        plot_id=UUID("00000000-0000-0000-0000-000000000009"),
        location=Coordinates(latitude=15.3173, longitude=75.7139, crs="EPSG:4326"),
        timezone="Asia/Kolkata",
        simulation_period=SimulationPeriod(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2)
        ),
        crop_id=TURMERIC_CROP_ID,
    )

    # 1. Automatic discovery of all members when member_ids is None
    batch_results = await service.prepare_ensemble_batch(req, member_ids=None)

    # Exactly 1 weather fetch (with include_ensemble=True) and exactly 1 soil fetch
    assert weather_mock.fetch_weather.call_count == 1
    call_kwargs = weather_mock.fetch_weather.call_args.kwargs
    assert call_kwargs["include_ensemble"] is True
    assert soil_mock.fetch_soil.call_count == 1

    assert sorted(batch_results.keys()) == ["member-01", "member-02"]
    m1_res = batch_results["member-01"]
    m2_res = batch_results["member-02"]

    assert m1_res.is_valid is True
    assert m2_res.is_valid is True
    assert m1_res.plot_id == req.plot_id
    assert m2_res.plot_id == req.plot_id

    # Verify trajectories are independent and unblended
    m1_tmin = m1_res.c1_input.daily_weather[0].temperature_min_c.value
    m2_tmin = m2_res.c1_input.daily_weather[0].temperature_min_c.value
    assert m1_tmin == 22.0
    assert m2_tmin == 23.0  # +1.0 in test weather fixture
    assert m1_tmin != m2_tmin

    # Verify both members are independently cached
    assert len(service._cache) == 2

    # 2. Explicit member_ids filter (serves from cache without new network calls)
    batch_subset = await service.prepare_ensemble_batch(
        req, member_ids=["member-01"]
    )
    assert list(batch_subset.keys()) == ["member-01"]
    assert weather_mock.fetch_weather.call_count == 1
    assert soil_mock.fetch_soil.call_count == 1

    # 3. Requesting an unknown member
    batch_unknown = await service.prepare_ensemble_batch(
        req, member_ids=["member-99"]
    )
    assert "member-99" in batch_unknown
    assert batch_unknown["member-99"].is_valid is False
    assert any("member-99" in err for err in batch_unknown["member-99"].errors)

    # 4. Outage during ensemble batch with specified member_ids
    weather_fail_mock = AsyncMock(spec=OpenMeteoWeatherAdapter)
    weather_fail_mock.fetch_weather.side_effect = WeatherProviderError(
        status_code=500, message="Total Outage"
    )
    fail_service = EnvironmentalInputService(
        weather_adapter=weather_fail_mock,
        soil_adapter=soil_mock,
    )
    outage_batch = await fail_service.prepare_ensemble_batch(
        req, member_ids=["member-01", "member-02"]
    )
    assert len(outage_batch) == 2
    assert outage_batch["member-01"].is_valid is False
    assert outage_batch["member-02"].is_valid is False
    assert len(outage_batch["member-01"].c1_input.daily_weather) == 2
    assert (
        outage_batch["member-01"].c1_input.daily_weather[0].temperature_min_c.value
        is None
    )

    # 5. Outage with member_ids=None returns empty dict
    outage_batch_empty = await fail_service.prepare_ensemble_batch(
        req, member_ids=None
    )
    assert outage_batch_empty == {}
