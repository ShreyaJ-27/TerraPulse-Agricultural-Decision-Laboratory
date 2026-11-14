from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient
from app.core.config import get_settings
from app.core.db import get_session
from app.main import app
from app.services.farmer_alerts.calendar import CalendarWindow, CropCalendarProfile, PlantingDate
from app.services.farmer_alerts.calendar_view import build_calendar_view

client = TestClient(app)

DEMO_FARM_ID = "00000000-0000-0000-0000-000000000001"
MAIZE_ID = "00000000-0000-0000-0000-000000000010"


def test_calendar_keeps_active_regional_window_without_inventing_planting_date():
    crop_id = UUID(MAIZE_ID)
    profile = CropCalendarProfile(
        "IN-PB", crop_id, (), "Source", "v1",
        planting_windows=(
            CalendarWindow("active", "Active", date(2026, 11, 1), date(2026, 11, 20), "Source", "v1"),
            CalendarWindow("outside", "Outside", date(2026, 12, 15), date(2026, 12, 16), "Source", "v1"),
        ),
    )
    view = build_calendar_view(
        farm_id=UUID(DEMO_FARM_ID), plot_id=UUID(int=2), crop_id=crop_id,
        crop_name="Maize", region_id="IN-PB", planting=PlantingDate(None, "unconfirmed"),
        on_date=date(2026, 11, 14), profile=profile,
    )
    assert view["plantingDate"] is None
    assert [(event["date"], event["endDate"]) for event in view["next31Days"]] == [
        ("2026-11-14", "2026-11-20"),
    ]


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


def test_agri_calendar_generate(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    session = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(canonical_name="Maize")))

    async def get_test_session():
        yield session

    monkeypatch.setitem(app.dependency_overrides, get_session, get_test_session)
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


def test_private_notifications_and_legacy_writes(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    for route in ("farms", "telegram/status", "deliveries"):
        res = client.get(f"/api/v1/notifications/{route}/{DEMO_FARM_ID}")
        assert res.status_code == 401

    assert client.post(f"/api/v1/notifications/farms/{DEMO_FARM_ID}/test", json={}).status_code == 404
    assert client.post(f"/api/v1/notifications/telegram/link/{DEMO_FARM_ID}").status_code == 404
