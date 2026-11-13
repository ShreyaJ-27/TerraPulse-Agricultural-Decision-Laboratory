from uuid import UUID
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DEMO_FARM_ID = "00000000-0000-0000-0000-000000000001"
MAIZE_ID = "00000000-0000-0000-0000-000000000010"


def test_agri_calendar_seasons():
    res = client.get("/api/v1/agri-calendar/seasons")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "seasons" in data
    assert len(data["seasons"]) == 3
    season_ids = [s["id"] for s in data["seasons"]]
    assert "kharif" in season_ids
    assert "rabi" in season_ids
    assert "zaid" in season_ids


def test_agri_calendar_regional():
    res = client.get("/api/v1/agri-calendar/regional/IN-PB")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["regionId"] == "IN-PB"
    assert len(data["profiles"]) >= 1


def test_agri_calendar_generate():
    payload = {
        "cropId": MAIZE_ID,
        "plantingDate": "2026-06-15",
        "regionId": "IN-PB",
        "certainty": "confirmed"
    }
    res = client.post("/api/v1/agri-calendar/generate", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["cropName"] == "Maize"
    assert data["regionId"] == "IN-PB"
    assert "season" in data
    assert data["season"]["id"] == "kharif"


def test_notifications_endpoints():
    # 1. Telegram status
    res = client.get(f"/api/v1/notifications/telegram/status/{DEMO_FARM_ID}")
    assert res.status_code == 200
    status_data = res.json()["data"]
    assert status_data["farmId"] == DEMO_FARM_ID
    assert "botUsername" in status_data

    # 2. List notifications
    res = client.get(f"/api/v1/notifications/farms/{DEMO_FARM_ID}")
    assert res.status_code == 200
    list_data = res.json()["data"]
    assert "notifications" in list_data

    # 3. Trigger test notification
    test_payload = {
        "category": "weather",
        "kind": "test-extreme-heat",
        "cropName": "Maize",
        "title": "Review extreme heat advisory",
        "suggestedAction": "Apply protective light mulching.",
        "evidence": "Forecast temp > 40 C."
    }
    res = client.post(f"/api/v1/notifications/farms/{DEMO_FARM_ID}/test", json=test_payload)
    assert res.status_code == 201
    trigger_data = res.json()["data"]
    assert trigger_data["status"] == "triggered_and_delivered"
    assert trigger_data["deliveriesSent"] >= 1

    # 4. List deliveries
    res = client.get(f"/api/v1/notifications/deliveries/{DEMO_FARM_ID}")
    assert res.status_code == 200
    deliv_data = res.json()["data"]
    assert "deliveries" in deliv_data
    assert len(deliv_data["deliveries"]) >= 1
