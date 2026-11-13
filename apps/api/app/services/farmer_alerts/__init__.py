"""Developer A's agricultural calendar, proactive advisories and Telegram service.

This package imports no live providers at import-time; explicit workers perform
network calls. Farm persistence is shared with the existing TerraPulse backend.
"""
from .calendar import CropCalendarProfile, CalendarMilestone, PlantingDate
from .decision import AdvisoryEvent, evaluate_calendar, evaluate_weather, evaluate_science
from .telegram import TelegramClient, create_deep_link

__all__ = ["CropCalendarProfile", "CalendarMilestone", "PlantingDate", "AdvisoryEvent",
           "evaluate_calendar", "evaluate_weather", "evaluate_science", "TelegramClient",
           "create_deep_link"]
