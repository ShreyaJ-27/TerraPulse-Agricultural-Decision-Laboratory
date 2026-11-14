"""A visibly marked scenario, never a live agronomic advisory.

This module has no external side effects. Pitch messages are intentionally
separate from the farmer_alerts/telegram_deliveries evidence-backed pipeline.
"""
from __future__ import annotations

import re


def rainfall_watch_message(crop_name: str) -> str:
    """One concise, human-friendly illustrative warning for an opted-in farmer."""
    crop = re.sub(r"[\r\n\t\x00-\x1f\x7f]+", " ", str(crop_name or "your crop"))
    crop = re.sub(r"\s+", " ", crop).strip()[:55] or "your crop"
    return (
        "⚠️ TerraPulse | Heavy Rainfall Watch\n\n"
        f"Crop: {crop}\n"
        "Risk: Intense rainfall can cause waterlogging and disrupt soil conditions.\n"
        "Recommended action: Check field drainage and review planned irrigation "
        "before watering.\n\n"
        "Scenario illustration · Not a live weather forecast"
    )
