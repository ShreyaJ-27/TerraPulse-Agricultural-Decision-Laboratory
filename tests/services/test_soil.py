from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from app.contracts import Availability, C1EnvironmentalInput, DataStatus
from app.services.soil import (
    InvalidCoordinatesError,
    SoilGridsAdapter,
    SoilGridsClient,
    SoilNetworkError,
    SoilProviderError,
    SoilResponseMalformedError,
    SoilTimeoutError,
    classify_usda_texture,
)

FIXTURES_DIR = Path(__file__).parents[2] / "packages" / "contracts" / "fixtures"
SAMPLE_C1_FIXTURE = json.loads((FIXTURES_DIR / "c1.json").read_text(encoding="utf-8"))


def _sample_soilgrids_payload() -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [75.7139, 15.3173],
        },
        "properties": {
            "layers": [
                {
                    "name": "clay",
                    "unit_measure": {
                        "mapped_units": "g/kg",
                        "target_units": "g/100g",
                        "d_factor": 10,
                    },
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 200, "Q0.05": 160, "Q0.95": 240, "uncertainty": 20},
                        },
                        {
                            "label": "5-15cm",
                            "range": {"top_depth": 5, "bottom_depth": 15},
                            "values": {"mean": 200, "Q0.05": 160, "Q0.95": 240, "uncertainty": 20},
                        },
                        {
                            "label": "15-30cm",
                            "range": {"top_depth": 15, "bottom_depth": 30},
                            "values": {"mean": 200, "Q0.05": 160, "Q0.95": 240, "uncertainty": 20},
                        },
                    ],
                },
                {
                    "name": "silt",
                    "unit_measure": {"mapped_units": "g/kg", "target_units": "g/100g", "d_factor": 10},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 400},
                        },
                        {
                            "label": "5-15cm",
                            "range": {"top_depth": 5, "bottom_depth": 15},
                            "values": {"mean": 400},
                        },
                        {
                            "label": "15-30cm",
                            "range": {"top_depth": 15, "bottom_depth": 30},
                            "values": {"mean": 400},
                        },
                    ],
                },
                {
                    "name": "sand",
                    "unit_measure": {"mapped_units": "g/kg", "target_units": "g/100g", "d_factor": 10},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 400},
                        },
                        {
                            "label": "5-15cm",
                            "range": {"top_depth": 5, "bottom_depth": 15},
                            "values": {"mean": 400},
                        },
                        {
                            "label": "15-30cm",
                            "range": {"top_depth": 15, "bottom_depth": 30},
                            "values": {"mean": 400},
                        },
                    ],
                },
                {
                    "name": "bdod",
                    "unit_measure": {"mapped_units": "cg/cm3", "target_units": "kg/dm3", "d_factor": 100},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 135},
                        },
                        {
                            "label": "5-15cm",
                            "range": {"top_depth": 5, "bottom_depth": 15},
                            "values": {"mean": 135},
                        },
                        {
                            "label": "15-30cm",
                            "range": {"top_depth": 15, "bottom_depth": 30},
                            "values": {"mean": 135},
                        },
                    ],
                },
                {
                    "name": "phh2o",
                    "unit_measure": {"mapped_units": "pH*10", "target_units": "pH", "d_factor": 10},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 65},
                        }
                    ],
                },
                {
                    "name": "soc",
                    "unit_measure": {"mapped_units": "dg/kg", "target_units": "g/kg", "d_factor": 10},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 120},
                        }
                    ],
                },
                {
                    "name": "cfvo",
                    "unit_measure": {"mapped_units": "cm3/dm3", "target_units": "cm3/100cm3", "d_factor": 10},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 0},
                        }
                    ],
                },
                {
                    "name": "wv0033",
                    "unit_measure": {"mapped_units": "10^-3 cm3/cm3", "target_units": "cm3/cm3", "d_factor": 1000},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 280},
                        },
                        {
                            "label": "5-15cm",
                            "range": {"top_depth": 5, "bottom_depth": 15},
                            "values": {"mean": 280},
                        },
                        {
                            "label": "15-30cm",
                            "range": {"top_depth": 15, "bottom_depth": 30},
                            "values": {"mean": 280},
                        },
                    ],
                },
                {
                    "name": "wv1500",
                    "unit_measure": {"mapped_units": "10^-3 cm3/cm3", "target_units": "cm3/cm3", "d_factor": 1000},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "range": {"top_depth": 0, "bottom_depth": 5},
                            "values": {"mean": 120},
                        },
                        {
                            "label": "5-15cm",
                            "range": {"top_depth": 5, "bottom_depth": 15},
                            "values": {"mean": 120},
                        },
                        {
                            "label": "15-30cm",
                            "range": {"top_depth": 15, "bottom_depth": 30},
                            "values": {"mean": 120},
                        },
                    ],
                },
            ]
        },
    }


def _create_mock_client(handler=None) -> SoilGridsClient:
    async def transport_handler(request: httpx.Request) -> httpx.Response:
        if callable(handler):
            return handler(request)
        return httpx.Response(200, json=_sample_soilgrids_payload())

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(transport_handler))
    return SoilGridsClient(http_client=http_client)


# --- 1. Successful soil retrieval ---
@pytest.mark.asyncio
async def test_successful_soil_retrieval():
    client = _create_mock_client()
    adapter = SoilGridsAdapter(client=client)

    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139, target_depth_cm=30.0)

    assert result.location.latitude == 15.3173
    assert result.location.longitude == 75.7139
    assert result.profile_depth_cm == 30.0

    soil = result.soil_properties
    assert soil.depth_cm.value == 30.0
    assert soil.depth_cm.unit == "cm"
    assert soil.texture == "loam"

    assert soil.field_capacity.value == 0.28
    assert soil.field_capacity.unit == "m3/m3"
    assert soil.field_capacity.availability.status == DataStatus.AVAILABLE

    assert soil.wilting_point.value == 0.12
    assert soil.wilting_point.unit == "m3/m3"
    assert soil.wilting_point.availability.status == DataStatus.AVAILABLE

    assert soil.bulk_density is not None
    assert soil.bulk_density.value == 1.35
    assert soil.bulk_density.unit == "g/cm3"


# --- 2. Coordinate validation ---
@pytest.mark.asyncio
async def test_coordinate_validation():
    adapter = SoilGridsAdapter(_create_mock_client())

    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_soil(latitude=91.0, longitude=75.0)

    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_soil(latitude=-90.5, longitude=75.0)

    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_soil(latitude=15.0, longitude=180.5)

    with pytest.raises(InvalidCoordinatesError):
        await adapter.fetch_soil(latitude=15.0, longitude=-181.0)


# --- 3. Correct property and depth parsing ---
@pytest.mark.asyncio
async def test_property_and_depth_parsing():
    client = _create_mock_client()
    adapter = SoilGridsAdapter(client=client)

    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    assert "clay" in result.layers
    clay_layer = result.layers["clay"]
    assert len(clay_layer.depths) == 3

    d0_5 = clay_layer.depths[0]
    assert d0_5.depth_label == "0-5cm"
    assert d0_5.top_depth_cm == 0.0
    assert d0_5.bottom_depth_cm == 5.0
    assert d0_5.raw_mean == 200
    assert d0_5.converted_value == 20.0
    assert d0_5.target_unit == "%"
    assert d0_5.uncertainty == 20
    assert d0_5.quantiles == {"Q0.05": 16.0, "Q0.5": None, "Q0.95": 24.0}


# --- 4. Unit and scale-factor normalization ---
@pytest.mark.asyncio
async def test_unit_and_scale_factor_normalization():
    client = _create_mock_client()
    adapter = SoilGridsAdapter(client=client)

    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    # clay raw 200 / 10 = 20.0 %
    assert result.layers["clay"].depths[0].converted_value == 20.0
    # phh2o raw 65 / 10 = 6.5 pH
    assert result.layers["phh2o"].depths[0].converted_value == 6.5
    # bdod raw 135 / 100 = 1.35 g/cm3
    assert result.layers["bdod"].depths[0].converted_value == 1.35
    # soc raw 120 / 10 = 12.0 g/kg
    assert result.layers["soc"].depths[0].converted_value == 12.0
    # wv0033 raw 280 / 1000 = 0.28 m3/m3
    assert result.layers["wv0033"].depths[0].converted_value == 0.28
    # wv1500 raw 120 / 1000 = 0.12 m3/m3
    assert result.layers["wv1500"].depths[0].converted_value == 0.12


# --- 5. Missing properties handling ---
@pytest.mark.asyncio
async def test_missing_properties_handling():
    payload = _sample_soilgrids_payload()
    # Remove bulk density and soc
    payload["properties"]["layers"] = [
        l for l in payload["properties"]["layers"] if l["name"] not in ("bdod", "soc")
    ]

    def missing_prop_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    adapter = SoilGridsAdapter(_create_mock_client(missing_prop_handler))
    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    # Core properties still computed
    assert result.soil_properties.field_capacity.value == 0.28
    assert result.soil_properties.texture == "loam"
    # Bulk density is None because bdod layer was omitted
    assert result.soil_properties.bulk_density is None
    assert "bdod" not in result.layers


# --- 6. Missing depth intervals ---
@pytest.mark.asyncio
async def test_missing_depth_intervals():
    payload = _sample_soilgrids_payload()
    # Set wv0033 depths to empty list
    for layer in payload["properties"]["layers"]:
        if layer["name"] == "wv0033":
            layer["depths"] = []

    def empty_depth_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    adapter = SoilGridsAdapter(_create_mock_client(empty_depth_handler))
    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    # fieldCapacity must become MISSING
    assert result.soil_properties.field_capacity.value is None
    assert result.soil_properties.field_capacity.availability.status == DataStatus.MISSING


# --- 7. NoData handling — never convert to zero ---
@pytest.mark.asyncio
async def test_nodata_never_converts_to_zero():
    payload = _sample_soilgrids_payload()
    # Set wv0033 values.mean to None (NoData / masked coordinate)
    for layer in payload["properties"]["layers"]:
        if layer["name"] == "wv0033":
            for d in layer["depths"]:
                d["values"]["mean"] = None

    def null_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    adapter = SoilGridsAdapter(_create_mock_client(null_handler))
    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    fc = result.soil_properties.field_capacity
    assert fc.value is None
    assert fc.value != 0.0
    assert fc.availability.status == DataStatus.MISSING
    assert "missing" in (fc.availability.reason or "").lower()

    # Test sentinel value -32768 (SoilGrids standard integer NoData sentinel)
    sentinel_payload = _sample_soilgrids_payload()
    for layer in sentinel_payload["properties"]["layers"]:
        if layer["name"] == "wv0033":
            for d in layer["depths"]:
                d["values"]["mean"] = -32768

    sentinel_adapter = SoilGridsAdapter(
        _create_mock_client(lambda _req: httpx.Response(200, json=sentinel_payload))
    )
    sentinel_result = await sentinel_adapter.fetch_soil(latitude=15.3173, longitude=75.7139)
    sentinel_fc = sentinel_result.soil_properties.field_capacity
    assert sentinel_fc.value is None
    assert sentinel_fc.availability.status == DataStatus.MISSING
    assert sentinel_result.layers["wv0033"].depths[0].availability.status == DataStatus.MISSING
    assert sentinel_result.layers["wv0033"].depths[0].converted_value is None


# --- 8. Genuine zero-value preservation ---
@pytest.mark.asyncio
async def test_genuine_zero_preservation():
    client = _create_mock_client()
    adapter = SoilGridsAdapter(client=client)

    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    cfvo_obs = result.layers["cfvo"].depths[0]
    # cfvo raw mean was 0 -> converted value must be 0.0 and AVAILABLE
    assert cfvo_obs.raw_mean == 0
    assert cfvo_obs.converted_value == 0.0
    assert cfvo_obs.availability.status == DataStatus.AVAILABLE


# --- 9. Invalid values and quality status ---
@pytest.mark.asyncio
async def test_invalid_values_and_quality_status():
    payload = _sample_soilgrids_payload()
    # Set pH to 180 (18.0 pH > 14.0 max bounds)
    for layer in payload["properties"]["layers"]:
        if layer["name"] == "phh2o":
            layer["depths"][0]["values"]["mean"] = 180

    def invalid_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    adapter = SoilGridsAdapter(_create_mock_client(invalid_handler))
    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    ph_obs = result.layers["phh2o"].depths[0]
    assert ph_obs.converted_value == 18.0
    assert ph_obs.availability.status == DataStatus.INVALID
    assert "exceeds bounds" in (ph_obs.availability.reason or "")


# --- 10. Partial provider responses ---
@pytest.mark.asyncio
async def test_partial_provider_responses():
    # Only particle sizes, no hydraulic parameters
    partial_payload = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [75.7139, 15.3173]},
        "properties": {
            "layers": [
                {
                    "name": "clay",
                    "unit_measure": {"d_factor": 10},
                    "depths": [{"range": {"top_depth": 0, "bottom_depth": 30}, "values": {"mean": 450}}],
                },
                {
                    "name": "silt",
                    "unit_measure": {"d_factor": 10},
                    "depths": [{"range": {"top_depth": 0, "bottom_depth": 30}, "values": {"mean": 200}}],
                },
                {
                    "name": "sand",
                    "unit_measure": {"d_factor": 10},
                    "depths": [{"range": {"top_depth": 0, "bottom_depth": 30}, "values": {"mean": 350}}],
                },
            ]
        },
    }

    def partial_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=partial_payload)

    adapter = SoilGridsAdapter(_create_mock_client(partial_handler))
    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    # Clay 45%, Silt 20%, Sand 35% -> USDA "clay"
    assert result.soil_properties.texture == "clay"
    # wv0033 and wv1500 were not in response
    assert result.soil_properties.field_capacity.availability.status == DataStatus.MISSING
    assert result.soil_properties.wilting_point.availability.status == DataStatus.MISSING


# --- 11. Network errors and timeouts ---
@pytest.mark.asyncio
async def test_network_errors_and_timeouts():
    def timeout_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("SoilGrids connection timeout")

    def connect_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to reach SoilGrids host")

    timeout_adapter = SoilGridsAdapter(
        SoilGridsClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)))
    )
    with pytest.raises(SoilTimeoutError):
        await timeout_adapter.fetch_soil(latitude=15.0, longitude=75.0)

    connect_adapter = SoilGridsAdapter(
        SoilGridsClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(connect_handler)))
    )
    with pytest.raises(SoilNetworkError):
        await connect_adapter.fetch_soil(latitude=15.0, longitude=75.0)


# --- 12. HTTP errors ---
@pytest.mark.asyncio
async def test_http_errors():
    def err_500_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    def err_400_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": True, "detail": "Invalid coordinates"})

    adapter_500 = SoilGridsAdapter(
        SoilGridsClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(err_500_handler)))
    )
    with pytest.raises(SoilProviderError) as exc_500:
        await adapter_500.fetch_soil(latitude=15.0, longitude=75.0)
    assert exc_500.value.status_code == 500

    adapter_400 = SoilGridsAdapter(
        SoilGridsClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(err_400_handler)))
    )
    with pytest.raises(SoilProviderError) as exc_400:
        await adapter_400.fetch_soil(latitude=15.0, longitude=75.0)
    assert exc_400.value.status_code == 400


# --- 13. Malformed provider responses ---
@pytest.mark.asyncio
async def test_malformed_provider_responses():
    # Not JSON
    def html_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>502 Bad Gateway</html>")

    adapter_html = SoilGridsAdapter(
        SoilGridsClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(html_handler)))
    )
    with pytest.raises(SoilResponseMalformedError):
        await adapter_html.fetch_soil(latitude=15.0, longitude=75.0)

    # Missing properties.layers
    def bad_json_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"type": "Feature", "properties": {}})

    adapter_bad = SoilGridsAdapter(
        SoilGridsClient(http_client=httpx.AsyncClient(transport=httpx.MockTransport(bad_json_handler)))
    )
    with pytest.raises(SoilResponseMalformedError):
        await adapter_bad.fetch_soil(latitude=15.0, longitude=75.0)


# --- 14. Provenance correctness ---
@pytest.mark.asyncio
async def test_provenance_correctness():
    client = _create_mock_client()
    adapter = SoilGridsAdapter(client=client)

    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    assert result.data_source_ids == ["isric:soilgrids"]
    assert len(result.provenance) == 1

    prov = result.provenance[0]
    assert prov.source_id == "isric:soilgrids"
    assert prov.source_version == "v2.0"
    assert prov.retrieved_at is not None
    assert "isric.org" in (prov.reference or "")
    assert "modelled" in (prov.reference or "").lower() or "gridded" in (prov.reference or "").lower()
    assert result.raw_metadata["dataType"] == "modelled_gridded"


# --- 15. C1 contract compatibility ---
@pytest.mark.asyncio
async def test_c1_contract_compatibility():
    client = _create_mock_client()
    adapter = SoilGridsAdapter(client=client)

    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139, target_depth_cm=30.0)

    # Use SoilProperties from adapter inside C1EnvironmentalInput
    c1_doc = C1EnvironmentalInput(
        contractVersion="1.0",
        farmId=uuid4(),
        location=result.location,
        timezone="Asia/Kolkata",
        simulationPeriod={
            "startDate": SAMPLE_C1_FIXTURE["simulationPeriod"]["startDate"],
            "endDate": SAMPLE_C1_FIXTURE["simulationPeriod"]["endDate"],
        },
        dailyWeather=copy.deepcopy(SAMPLE_C1_FIXTURE["dailyWeather"]),
        soil=result.soil_properties,
        dataSourceIds=result.data_source_ids,
        retrievedAt=result.retrieved_at,
        availability=Availability(status=DataStatus.AVAILABLE),
        provenance=result.provenance,
    )

    assert c1_doc.contract_version == "1.0"
    assert c1_doc.soil.depth_cm.value == 30.0
    assert c1_doc.soil.texture == "loam"
    assert c1_doc.soil.field_capacity.value == 0.28
    assert c1_doc.soil.wilting_point.value == 0.12


# --- 16. Independent handling of unavailable soil properties ---
@pytest.mark.asyncio
async def test_independent_handling_of_unavailable_soil_properties():
    payload = _sample_soilgrids_payload()
    # Remove only wv0033
    payload["properties"]["layers"] = [
        l for l in payload["properties"]["layers"] if l["name"] != "wv0033"
    ]

    def missing_fc_handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    adapter = SoilGridsAdapter(_create_mock_client(missing_fc_handler))
    result = await adapter.fetch_soil(latitude=15.3173, longitude=75.7139)

    # Field capacity is missing, but texture and wilting point are completely valid
    assert result.soil_properties.field_capacity.availability.status == DataStatus.MISSING
    assert result.soil_properties.wilting_point.availability.status == DataStatus.AVAILABLE
    assert result.soil_properties.wilting_point.value == 0.12
    assert result.soil_properties.texture == "loam"

    # Overall soil availability must be MISSING because mandatory fieldCapacity is missing
    assert result.availability.status == DataStatus.MISSING
    assert "missing" in (result.availability.reason or "").lower()


# --- Helper: USDA Texture Triangle Coverage ---
def test_usda_texture_classification_matrix():
    assert classify_usda_texture(sand=88, silt=7, clay=5) == "sand"
    assert classify_usda_texture(sand=82, silt=10, clay=8) == "loamy sand"
    assert classify_usda_texture(sand=65, silt=25, clay=10) == "sandy loam"
    assert classify_usda_texture(sand=40, silt=40, clay=20) == "loam"
    assert classify_usda_texture(sand=20, silt=65, clay=15) == "silt loam"
    assert classify_usda_texture(sand=5, silt=88, clay=7) == "silt"
    assert classify_usda_texture(sand=60, silt=15, clay=25) == "sandy clay loam"
    assert classify_usda_texture(sand=35, silt=35, clay=30) == "clay loam"
    assert classify_usda_texture(sand=10, silt=55, clay=35) == "silty clay loam"
    assert classify_usda_texture(sand=50, silt=10, clay=40) == "sandy clay"
    assert classify_usda_texture(sand=10, silt=45, clay=45) == "silty clay"
    assert classify_usda_texture(sand=20, silt=20, clay=60) == "clay"
    assert classify_usda_texture(sand=0, silt=0, clay=0) is None
