from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from app.contracts import Availability, C1EnvironmentalInput, DataStatus, SoilProperties
from app.services.weather import (
    InvalidCoordinatesError,
    OpenMeteoClient,
    OpenMeteoWeatherAdapter,
    WeatherNetworkError,
    WeatherProviderError,
    WeatherResponseMalformedError,
    WeatherTimeoutError,
    normalize_member_id,
)

FIXTURES_DIR = Path(__file__).parents[2] / "packages" / "contracts" / "fixtures"
SAMPLE_SOIL_DATA = json.loads((FIXTURES_DIR / "c1.json").read_text(encoding="utf-8"))["soil"]


def _sample_deterministic_payload() -> dict[str, Any]:
    return {
        "latitude": 15.3125,
        "longitude": 75.75,
        "generationtime_ms": 0.245,
        "utc_offset_seconds": 19800,
        "timezone": "Asia/Kolkata",
        "timezone_abbreviation": "IST",
        "elevation": 648.0,
        "daily_units": {
            "time": "iso8601",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "et0_fao_evapotranspiration": "mm",
            "wind_speed_10m_max": "km/h",
            "wind_direction_10m_dominant": "°",
            "shortwave_radiation_sum": "MJ/m²",
            "relative_humidity_2m_mean": "%",
        },
        "daily": {
            "time": ["2026-06-01", "2026-06-02"],
            "temperature_2m_max": [31.5, 32.2],
            "temperature_2m_min": [22.0, 21.8],
            "precipitation_sum": [0.0, 4.5],
            "et0_fao_evapotranspiration": [4.2, 4.0],
            "wind_speed_10m_max": [14.0, 12.5],
            "wind_direction_10m_dominant": [245.0, 230.0],
            "shortwave_radiation_sum": [22.0, 19.5],
            "relative_humidity_2m_mean": [65.0, 72.0],
        },
    }


def _sample_ensemble_payload() -> dict[str, Any]:
    return {
        "latitude": 15.3125,
        "longitude": 75.75,
        "generationtime_ms": 0.45,
        "utc_offset_seconds": 19800,
        "timezone": "Asia/Kolkata",
        "elevation": 648.0,
        "daily_units": {
            "time": "iso8601",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "et0_fao_evapotranspiration": "mm",
        },
        "daily": {
            "time": ["2026-06-01", "2026-06-02"],
            "temperature_2m_max_member01": [31.0, 31.8],
            "temperature_2m_max_member02": [32.5, 33.1],
            "temperature_2m_min_member01": [21.5, 22.0],
            "temperature_2m_min_member02": [22.2, 22.8],
            "precipitation_sum_member01": [0.0, 2.0],
            "precipitation_sum_member02": [1.5, 5.0],
            "et0_fao_evapotranspiration_member01": [4.1, 3.9],
            "et0_fao_evapotranspiration_member02": [4.4, 4.2],
        },
    }


def _create_mock_client(
    deterministic_handler=None, ensemble_handler=None
) -> OpenMeteoClient:
    async def transport_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "ensemble" in url_str:
            if callable(ensemble_handler):
                return ensemble_handler(request)
            return httpx.Response(200, json=_sample_ensemble_payload())
        else:
            if callable(deterministic_handler):
                return deterministic_handler(request)
            return httpx.Response(200, json=_sample_deterministic_payload())

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(transport_handler))
    return OpenMeteoClient(http_client=http_client)


# --- 1. Successful deterministic weather retrieval ---
@pytest.mark.asyncio
async def test_successful_deterministic_weather_retrieval():
    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(
        latitude=15.3173,
        longitude=75.7139,
        timezone="Asia/Kolkata",
        include_ensemble=False,
    )

    assert result.deterministic_available is True
    assert len(result.deterministic_daily) == 2
    assert result.timezone == "Asia/Kolkata"
    assert result.location.latitude == 15.3173
    assert result.location.longitude == 75.7139

    first_day = result.deterministic_daily[0]
    assert first_day.date == date(2026, 6, 1)
    assert first_day.temperature_min_c.value == 22.0
    assert first_day.temperature_max_c.value == 31.5
    assert first_day.rainfall_mm.value == 0.0
    assert first_day.rainfall_mm.availability.status == DataStatus.AVAILABLE
    assert first_day.reference_evapotranspiration_mm.value == 4.2
    assert first_day.ensemble_member_id is None

    # Check supplementary variables
    assert len(result.deterministic_supplementary) == 2
    first_supp = result.deterministic_supplementary[0]
    assert first_supp.relative_humidity_mean.value == 65.0
    assert first_supp.wind_speed_max.value == 14.0
    assert first_supp.wind_direction_dominant.value == 245.0
    assert first_supp.shortwave_radiation_sum.value == 22.0


# --- 2. Successful ensemble retrieval ---
@pytest.mark.asyncio
async def test_successful_ensemble_retrieval():
    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(
        latitude=15.3173,
        longitude=75.7139,
        include_ensemble=True,
    )

    assert result.ensemble_available is True
    assert "member-01" in result.ensemble_members
    assert "member-02" in result.ensemble_members
    assert len(result.ensemble_members["member-01"]) == 2
    assert len(result.ensemble_members["member-02"]) == 2

    m1_d1 = result.ensemble_members["member-01"][0]
    assert m1_d1.ensemble_member_id == "member-01"
    assert m1_d1.temperature_max_c.value == 31.0
    assert m1_d1.rainfall_mm.value == 0.0

    m2_d1 = result.ensemble_members["member-02"][0]
    assert m2_d1.ensemble_member_id == "member-02"
    assert m2_d1.temperature_max_c.value == 32.5
    assert m2_d1.rainfall_mm.value == 1.5


# --- 3. Correct unit normalization ---
@pytest.mark.asyncio
async def test_correct_unit_normalization():
    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(latitude=15.3173, longitude=75.7139)

    det_day = result.deterministic_daily[0]
    # °C must be normalized to degC per C1 contract
    assert det_day.temperature_min_c.unit == "degC"
    assert det_day.temperature_max_c.unit == "degC"
    assert det_day.rainfall_mm.unit == "mm"
    assert det_day.reference_evapotranspiration_mm.unit == "mm"

    supp_day = result.deterministic_supplementary[0]
    assert supp_day.relative_humidity_mean.unit == "%"
    assert supp_day.wind_speed_max.unit == "km/h"
    assert supp_day.wind_direction_dominant.unit == "deg"
    # MJ/m² must be normalized to MJ/m2
    assert supp_day.shortwave_radiation_sum.unit == "MJ/m2"


# --- 4. Correct timestamp and timezone handling ---
@pytest.mark.asyncio
async def test_timestamp_and_timezone_handling():
    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(
        latitude=15.3173,
        longitude=75.7139,
        timezone="Asia/Kolkata",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )

    assert result.timezone == "Asia/Kolkata"
    assert result.deterministic_daily[0].date == date(2026, 6, 1)
    assert result.deterministic_daily[1].date == date(2026, 6, 2)
    assert result.retrieved_at.tzinfo is not None


# --- 5. Correct ensemble member preservation ---
@pytest.mark.asyncio
async def test_ensemble_member_preservation():
    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(latitude=15.3173, longitude=75.7139)

    # Members must remain separate, never averaged
    m1 = result.get_daily_weather_for_member("member-01")
    m2 = result.get_daily_weather_for_member("member-02")
    assert len(m1) == 2
    assert len(m2) == 2
    assert m1[0].temperature_max_c.value != m2[0].temperature_max_c.value
    assert m1[0].ensemble_member_id == "member-01"
    assert m2[0].ensemble_member_id == "member-02"

    all_records = result.all_daily_weather()
    assert len(all_records) == len(result.deterministic_daily) + len(m1) + len(m2)


# --- 6. Missing variables and unavailable measurements ---
@pytest.mark.asyncio
async def test_missing_variables_and_unavailable_measurements():
    # Payload with None / null in rainfall and missing et0
    sparse_payload = _sample_deterministic_payload()
    sparse_payload["daily"]["precipitation_sum"] = [None, 3.2]
    sparse_payload["daily"].pop("et0_fao_evapotranspiration", None)

    def sparse_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=sparse_payload)

    client = _create_mock_client(deterministic_handler=sparse_handler)
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(latitude=15.3173, longitude=75.7139, include_ensemble=False)

    d1 = result.deterministic_daily[0]
    # Null observation must be MISSING and value must NEVER become 0.0
    assert d1.rainfall_mm.value is None
    assert d1.rainfall_mm.availability.status == DataStatus.MISSING
    assert "missing" in d1.rainfall_mm.availability.reason.lower()

    # Missing variable in payload must also be MISSING
    assert d1.reference_evapotranspiration_mm.value is None
    assert d1.reference_evapotranspiration_mm.availability.status == DataStatus.MISSING

    # Second day has valid rainfall
    d2 = result.deterministic_daily[1]
    assert d2.rainfall_mm.value == 3.2
    assert d2.rainfall_mm.availability.status == DataStatus.AVAILABLE


# --- 7. Partial ensemble responses ---
@pytest.mark.asyncio
async def test_partial_ensemble_responses():
    # member02 only has 1 day while time array has 2 days
    partial_ensemble = _sample_ensemble_payload()
    partial_ensemble["daily"]["temperature_2m_max_member02"] = [32.5]  # truncated

    def partial_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=partial_ensemble)

    client = _create_mock_client(ensemble_handler=partial_handler)
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(latitude=15.3173, longitude=75.7139, include_ensemble=True)

    m2 = result.ensemble_members["member-02"]
    assert len(m2) == 2
    assert m2[0].temperature_max_c.value == 32.5
    assert m2[0].temperature_max_c.availability.status == DataStatus.AVAILABLE

    # Day 2 was truncated: must be MISSING, value must be None
    assert m2[1].temperature_max_c.value is None
    assert m2[1].temperature_max_c.availability.status == DataStatus.MISSING


# --- 8. Invalid coordinates validation ---
@pytest.mark.asyncio
async def test_invalid_coordinates():
    adapter = OpenMeteoWeatherAdapter(_create_mock_client())

    # Latitude > 90
    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_weather(latitude=91.0, longitude=75.0)

    # Latitude < -90
    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_weather(latitude=-90.1, longitude=75.0)

    # Longitude > 180
    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_weather(latitude=15.0, longitude=180.5)

    # Longitude < -180
    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_weather(latitude=15.0, longitude=-181.0)


# --- 9. Network errors and timeouts ---
@pytest.mark.asyncio
async def test_network_errors_and_timeouts():
    def timeout_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Connection timed out")

    def connect_error_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to connect")

    timeout_client = OpenMeteoClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler))
    )
    timeout_adapter = OpenMeteoWeatherAdapter(client=timeout_client)

    with pytest.raises(WeatherTimeoutError):
        await timeout_adapter.fetch_weather(latitude=15.0, longitude=75.0, include_ensemble=False)

    connect_client = OpenMeteoClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(connect_error_handler))
    )
    connect_adapter = OpenMeteoWeatherAdapter(client=connect_client)

    with pytest.raises(WeatherNetworkError):
        await connect_adapter.fetch_weather(latitude=15.0, longitude=75.0, include_ensemble=False)


# --- 10. HTTP errors ---
@pytest.mark.asyncio
async def test_http_errors():
    def http_500_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    def http_400_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text='{"error": true, "reason": "Invalid parameter"}')

    err_client = OpenMeteoClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(http_500_handler))
    )
    adapter = OpenMeteoWeatherAdapter(client=err_client)

    with pytest.raises(WeatherProviderError) as exc_info:
        await adapter.fetch_weather(latitude=15.0, longitude=75.0, include_ensemble=False)
    assert exc_info.value.status_code == 500

    err400_client = OpenMeteoClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(http_400_handler))
    )
    adapter400 = OpenMeteoWeatherAdapter(client=err400_client)

    with pytest.raises(WeatherProviderError) as exc_info400:
        await adapter400.fetch_weather(latitude=15.0, longitude=75.0, include_ensemble=False)
    assert exc_info400.value.status_code == 400


# --- 11. Malformed provider responses ---
@pytest.mark.asyncio
async def test_malformed_provider_responses():
    # Missing daily section
    def no_daily_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"latitude": 15.0, "longitude": 75.0})

    client = OpenMeteoClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(no_daily_handler))
    )
    adapter = OpenMeteoWeatherAdapter(client=client)

    with pytest.raises(WeatherResponseMalformedError):
        await adapter.fetch_weather(latitude=15.0, longitude=75.0, include_ensemble=False)

    # Invalid non-json body
    def invalid_json_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Not JSON <html/>")

    bad_client = OpenMeteoClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(invalid_json_handler))
    )
    bad_adapter = OpenMeteoWeatherAdapter(client=bad_client)

    with pytest.raises(WeatherResponseMalformedError):
        await bad_adapter.fetch_weather(latitude=15.0, longitude=75.0, include_ensemble=False)


# --- 12. Provenance correctness ---
@pytest.mark.asyncio
async def test_provenance_correctness():
    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(latitude=15.3173, longitude=75.7139, include_ensemble=True)

    assert "open-meteo:forecast" in result.data_source_ids
    assert "open-meteo:ensemble" in result.data_source_ids
    assert len(result.provenance) == 2

    p_det = next(p for p in result.provenance if p.source_id == "open-meteo:forecast")
    assert p_det.source_version == "v1"
    assert p_det.retrieved_at is not None
    assert "open-meteo.com" in (p_det.reference or "")

    p_ens = next(p for p in result.provenance if p.source_id == "open-meteo:ensemble")
    assert p_ens.source_version == "gfs_seamless"
    assert p_ens.retrieved_at is not None


# --- 13. C1 contract validation ---
@pytest.mark.asyncio
async def test_c1_contract_validation():
    # Verify full C1EnvironmentalInput composition with C1 soil properties
    soil_data = SoilProperties.model_validate(SAMPLE_SOIL_DATA)

    client = _create_mock_client()
    adapter = OpenMeteoWeatherAdapter(client=client)

    result = await adapter.fetch_weather(
        latitude=15.3173,
        longitude=75.7139,
        timezone="Asia/Kolkata",
        include_ensemble=True,
    )

    # Use deterministic daily weather in C1EnvironmentalInput
    c1_doc = C1EnvironmentalInput(
        contractVersion="1.0",
        farmId=uuid4(),
        location=result.location,
        timezone=result.timezone,
        simulationPeriod={
            "startDate": str(result.deterministic_daily[0].date),
            "endDate": str(result.deterministic_daily[-1].date),
        },
        dailyWeather=result.deterministic_daily,
        soil=soil_data,
        dataSourceIds=result.data_source_ids,
        retrievedAt=result.retrieved_at,
        availability=Availability(status=DataStatus.AVAILABLE),
        provenance=result.provenance,
    )

    assert c1_doc.contract_version == "1.0"
    assert len(c1_doc.daily_weather) == 2

    # Also test with ensemble member
    c1_member_doc = C1EnvironmentalInput(
        contractVersion="1.0",
        farmId=uuid4(),
        location=result.location,
        timezone=result.timezone,
        simulationPeriod={
            "startDate": str(result.ensemble_members["member-01"][0].date),
            "endDate": str(result.ensemble_members["member-01"][-1].date),
        },
        dailyWeather=result.get_daily_weather_for_member("member-01"),
        soil=soil_data,
        dataSourceIds=result.data_source_ids,
        retrievedAt=result.retrieved_at,
        availability=Availability(status=DataStatus.AVAILABLE),
        provenance=result.provenance,
    )

    assert c1_member_doc.daily_weather[0].ensemble_member_id == "member-01"


# --- 14. Independent handling of deterministic and ensemble failures ---
@pytest.mark.asyncio
async def test_independent_handling_of_deterministic_and_ensemble_failures():
    # Scenario A: Deterministic succeeds, ensemble fails (e.g. 500 error)
    def fail_ensemble(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Ensemble service unavailable")

    client_a = _create_mock_client(ensemble_handler=fail_ensemble)
    adapter_a = OpenMeteoWeatherAdapter(client=client_a)

    result_a = await adapter_a.fetch_weather(
        latitude=15.3173, longitude=75.7139, include_ensemble=True
    )

    # Deterministic data MUST NOT be discarded
    assert result_a.deterministic_available is True
    assert len(result_a.deterministic_daily) == 2
    assert result_a.ensemble_available is False
    assert result_a.ensemble_error is not None
    assert "500" in result_a.ensemble_error
    assert len(result_a.ensemble_members) == 0

    # Scenario B: Deterministic fails (500), ensemble succeeds
    def fail_deterministic(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Forecast service down")

    client_b = _create_mock_client(deterministic_handler=fail_deterministic)
    adapter_b = OpenMeteoWeatherAdapter(client=client_b)

    result_b = await adapter_b.fetch_weather(
        latitude=15.3173, longitude=75.7139, include_ensemble=True
    )

    # Ensemble data MUST NOT be discarded
    assert result_b.deterministic_available is False
    assert result_b.deterministic_error is not None
    assert result_b.ensemble_available is True
    assert "member-01" in result_b.ensemble_members


def test_member_id_normalization():
    assert normalize_member_id("member01") == "member-01"
    assert normalize_member_id("member_02") == "member-02"
    assert normalize_member_id("member-03") == "member-03"
    assert normalize_member_id("member10") == "member-10"
    assert normalize_member_id("control") == "control"
    assert normalize_member_id("mean") == "mean"
