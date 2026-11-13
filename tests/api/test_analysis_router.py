from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from app.contracts import Coordinates
from app.main import app
from app.routers.analysis import get_analysis_service
from app.schemas import FarmCreateRequest, PlotAreaInput, PlotCreateRequest
from app.services.analysis import (
    EvidenceGroundedAnalysisService,
)
from app.services.crop_lens.registry import CROP_REGISTRY
from app.services.crop_lens.resolver import CropLensResolver
from app.services.environmental import EnvironmentalInputService
from app.services.onboarding import OnboardingService
from fastapi.testclient import TestClient

TURMERIC_ID = UUID("00000000-0000-0000-0000-000000000003")

# Set up test dependencies with in-memory service
onboarding_service = OnboardingService()
crop_resolver = CropLensResolver(CROP_REGISTRY)
environmental_service = EnvironmentalInputService(crop_resolver=crop_resolver)

analysis_service = EvidenceGroundedAnalysisService(
    onboarding_service=onboarding_service,
    crop_resolver=crop_resolver,
    environmental_service=environmental_service,
)

app.dependency_overrides[get_analysis_service] = lambda: analysis_service
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_in_memory():
    onboarding_service._in_memory_farms.clear()
    onboarding_service._in_memory_plots.clear()


@pytest.mark.asyncio
async def _seed_farm_and_plot():
    farm = await onboarding_service.create_farm(
        FarmCreateRequest(
            name="Mysuru Agri Station",
            timezone="Asia/Kolkata",
            location=Coordinates(latitude=12.2958, longitude=76.6394, crs="EPSG:4326"),
            locationConfirmed=True,
        )
    )
    plot = await onboarding_service.create_plot(
        farm.farm_id,
        PlotCreateRequest(
            areaM2=PlotAreaInput(value=15000.0, unit="m2"),
            cropId=TURMERIC_ID,
            plantingDate=date(2026, 6, 1),
        ),
    )
    return farm, plot


def test_analysis_endpoint_success():
    import asyncio
    farm, plot = asyncio.run(_seed_farm_and_plot())

    payload = {
        "farmId": str(farm.farm_id),
        "plotId": str(plot.plot_id),
        "question": "What is the water requirement for this plot?",
        "language": "en",
        "includeWeather": False,
        "includeSoil": False,
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 200

    body = res.json()
    assert body["contractVersion"] == "1.0"
    assert "correlationId" in body

    data = body["data"]
    assert data["farmId"] == str(farm.farm_id)
    assert data["plotId"] == str(plot.plot_id)
    assert data["language"] == "en"
    assert "Mysuru Agri Station" in data["summary"]
    assert len(data["sections"]) >= 4
    assert data["guardrailStatus"]["passed"] is True
    assert data["generationMode"] in ("deterministic", "deterministic_fallback")


def test_analysis_endpoint_unknown_farm_returns_404():
    unknown_farm_id = uuid4()
    unknown_plot_id = uuid4()

    payload = {
        "farmId": str(unknown_farm_id),
        "plotId": str(unknown_plot_id),
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 404
    assert f"Farm with ID '{unknown_farm_id}' was not found" in res.json()["detail"]


def test_analysis_endpoint_unknown_plot_returns_404():
    import asyncio
    farm, _ = asyncio.run(_seed_farm_and_plot())
    unknown_plot_id = uuid4()

    payload = {
        "farmId": str(farm.farm_id),
        "plotId": str(unknown_plot_id),
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 404
    assert f"Plot with ID '{unknown_plot_id}' was not found" in res.json()["detail"]


def test_analysis_endpoint_plant_pathology_escalation():
    import asyncio
    farm, plot = asyncio.run(_seed_farm_and_plot())

    payload = {
        "farmId": str(farm.farm_id),
        "plotId": str(plot.plot_id),
        "question": "My crop has fungal leaf blight and root rot, how do I cure it?",
        "language": "en",
        "includeWeather": False,
        "includeSoil": False,
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 200

    data = res.json()["data"]
    assert data["guardrailStatus"]["passed"] is False
    assert data["guardrailStatus"]["escalationRequired"] is True
    assert "plant_pathology" in data["guardrailStatus"]["restrictedTopics"]

    escalations = data["escalations"]
    assert len(escalations) > 0
    assert escalations[0]["category"] == "plant_pathology"
    assert "KVK" in escalations[0]["recommendedAuthority"]


def test_analysis_endpoint_kannada_language():
    import asyncio
    farm, plot = asyncio.run(_seed_farm_and_plot())

    payload = {
        "farmId": str(farm.farm_id),
        "plotId": str(plot.plot_id),
        "language": "kn",
        "includeWeather": False,
        "includeSoil": False,
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 200

    data = res.json()["data"]
    assert data["language"] == "kn"
    assert "ಕ್ಷೇತ್ರ" in data["summary"] or "ಬೆಳೆ" in data["summary"]


def test_analysis_endpoint_hindi_language():
    import asyncio
    farm, plot = asyncio.run(_seed_farm_and_plot())

    payload = {
        "farmId": str(farm.farm_id),
        "plotId": str(plot.plot_id),
        "language": "hi",
        "includeWeather": False,
        "includeSoil": False,
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 200

    data = res.json()["data"]
    assert data["language"] == "hi"
    assert "खेत" in data["summary"] or "फसल" in data["summary"]


def test_analysis_endpoint_validation_error():
    # Missing required field plotId
    payload = {
        "farmId": str(uuid4()),
    }
    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_analysis_endpoint_cross_farm_plot_access_rejected_404():
    """Verify that accessing Plot B through Farm A's ID is rejected with 404."""
    import asyncio

    # Create Farm A with Plot A
    farm_a, _plot_a = asyncio.run(_seed_farm_and_plot())

    # Create Farm B with Plot B
    farm_b = asyncio.run(
        onboarding_service.create_farm(
            FarmCreateRequest(
                name="Second Farm",
                timezone="Asia/Kolkata",
                location=Coordinates(latitude=13.0, longitude=77.0, crs="EPSG:4326"),
                locationConfirmed=True,
            )
        )
    )
    plot_b = asyncio.run(
        onboarding_service.create_plot(
            farm_b.farm_id,
            PlotCreateRequest(
                areaM2=PlotAreaInput(value=5000.0, unit="m2"),
                cropId=TURMERIC_ID,
                plantingDate=date(2026, 6, 1),
            ),
        )
    )

    # Request with farmId = Farm A, but plotId = Plot B (cross-tenant mismatch)
    payload = {
        "farmId": str(farm_a.farm_id),
        "plotId": str(plot_b.plot_id),
    }

    res = client.post("/api/v1/analysis", json=payload)
    assert res.status_code == 404
    assert f"Plot with ID '{plot_b.plot_id}' was not found under farm '{farm_a.farm_id}'" in res.json()["detail"]
