import json
from datetime import datetime
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
ADVISORY = "/api/v1/advisory/regions"
FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "packages/contracts/fixtures/advisory-punjab.json"
)
MAIZE_ID = "00000000-0000-0000-0000-000000000010"
COTTON_ID = "00000000-0000-0000-0000-000000000050"


def test_offline_profiles_match_api_and_catalogue():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    region = fixture["regionId"]
    catalogue = client.get("/api/v1/crops").json()["data"]["crops"]
    assert [profile["regionalContext"]["season"] for profile in fixture["profiles"]] == [
        "kharif",
        "rabi",
    ]

    for profile in fixture["profiles"]:
        crop_id = profile["crop"]["cropId"]
        response = client.get(
            f"{ADVISORY}/{region}/crops/{crop_id}",
            headers={"X-Correlation-ID": "advisory-test"},
        )
        assert response.status_code == 200
        assert response.json() == {
            "contractVersion": "1.0",
            "correlationId": "advisory-test",
            "data": profile,
        }
        crop = next(item for item in catalogue if item["cropId"] == crop_id)
        assert profile["crop"] == {key: crop[key] for key in profile["crop"]}
        context = profile["regionalContext"]
        assert context["source"]["url"].startswith("https://pau.edu/")
        assert context["plantingWindow"]["kind"] == "typical_regional_window"
        assert all(milestone["sourceSection"] for milestone in context["milestones"])
        assert profile["capabilities"] == {
            "regionalPlantingWindow": True,
            "cultivationMilestones": True,
            "numericalIrrigationAdvice": False,
            "harvestDatePrediction": False,
            "yieldPrediction": False,
            "simulation": False,
        }

    assert fixture["weatherEvents"]
    for event in fixture["weatherEvents"]:
        assert event["regionId"] == region
        assert event["source"] == {
            "kind": "synthetic_fixture",
            "fixtureId": fixture["fixtureId"],
        }
        assert datetime.fromisoformat(event["startsAt"]) < datetime.fromisoformat(event["endsAt"])


@pytest.mark.parametrize(
    ("region", "crop_id", "status"),
    [
        ("IN-KA", MAIZE_ID, "region_unsupported"),
        ("IN-PB", COTTON_ID, "crop_context_unavailable"),
    ],
)
def test_context_unavailable_preserves_crop_identity(region, crop_id, status):
    response = client.get(f"{ADVISORY}/{region}/crops/{crop_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == status
    assert data["crop"]["cropId"] == crop_id
    assert data["regionalContext"] is None
    assert not any(data["capabilities"].values())


@pytest.mark.parametrize(
    ("region", "crop_id", "code"),
    [
        ("IN-PB", "ffffffff-ffff-ffff-ffff-ffffffffffff", 404),
        ("IN-PB", "maize", 422),
        ("Punjab", MAIZE_ID, 422),
    ],
)
def test_invalid_advisory_lookups(region, crop_id, code):
    assert client.get(f"{ADVISORY}/{region}/crops/{crop_id}").status_code == code
