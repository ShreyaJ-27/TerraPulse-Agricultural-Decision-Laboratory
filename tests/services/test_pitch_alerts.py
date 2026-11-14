"""Targeted regression checks: no invented warnings in the normal alert path."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services.farmer_alerts.pitch_message import rainfall_watch_message
from app.routers.pitch_alerts import _authorized_pitch_farm, COOLDOWN_SECONDS, MAX_SENDS_PER_DAY
from app.services.farmer_alerts.evidence_refresh import refresh_subscribed_evidence


def test_warning_has_discreet_but_explicit_scenario_marker():
    text = rainfall_watch_message("Turmeric")
    assert "Heavy Rainfall Watch" in text
    assert "Crop: Turmeric" in text
    assert "Scenario illustration · Not a live weather forecast" in text
    assert "35 mm" not in text
    assert "DEMO FARM" not in text


def test_injection_cannot_insert_fake_second_warning():
    value = rainfall_watch_message("Turmeric\nLIVE FORECAST: 99 mm")
    assert "\nLIVE FORECAST" not in value
    assert value.count("Scenario illustration") == 1


def test_pitch_defaults_off(monkeypatch):
    farm = uuid4()
    for key in ("TERRAPULSE_TELEGRAM_ENABLED", "TERRAPULSE_PITCH_ALERTS_ENABLED",
                "TERRAPULSE_PITCH_FARM_ID", "TERRAPULSE_PITCH_EXPIRES_AT"):
        monkeypatch.delenv(key, raising=False)
    assert _authorized_pitch_farm(farm) is False


def test_farm_allowlist_and_expiration(monkeypatch):
    farm = uuid4()
    monkeypatch.setenv("TERRAPULSE_TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TERRAPULSE_PITCH_ALERTS_ENABLED", "1")
    monkeypatch.setenv("TERRAPULSE_PITCH_FARM_ID", str(farm))
    monkeypatch.setenv("TERRAPULSE_PITCH_EXPIRES_AT", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    assert _authorized_pitch_farm(farm) is True
    assert _authorized_pitch_farm(uuid4()) is False
    monkeypatch.setenv("TERRAPULSE_PITCH_EXPIRES_AT", (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat())
    assert _authorized_pitch_farm(farm) is False


def test_tight_send_caps():
    assert COOLDOWN_SECONDS >= 60
    assert 1 <= MAX_SENDS_PER_DAY <= 5


@pytest.mark.asyncio
async def test_refresh_rejects_unbounded_requests():
    with pytest.raises(ValueError, match="max_plots"):
        await refresh_subscribed_evidence(lambda: None, now=datetime.now(timezone.utc), max_plots=100)
    with pytest.raises(ValueError, match="timezone-aware"):
        await refresh_subscribed_evidence(lambda: None, now=datetime.now().replace(tzinfo=None))
