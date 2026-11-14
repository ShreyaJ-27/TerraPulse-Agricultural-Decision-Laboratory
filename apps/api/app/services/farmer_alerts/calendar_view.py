"""Farmer-friendly calendar: relevant next activities, not a stream of reminders.

An unknown milestone date remains undated guidance. One planned sowing date
shows once in the calendar, while notification engine schedules short reminders.
"""
from __future__ import annotations
from datetime import date, timedelta
from uuid import UUID
from .calendar import CropCalendarProfile, PlantingDate


def build_calendar_view(*, farm_id: UUID, plot_id: UUID, crop_id: UUID | None,
                        crop_name: str, plot_name: str = "Plot 1", region_id: str | None, planting: PlantingDate,
                        on_date: date, profile: CropCalendarProfile | None) -> dict:
    matched = profile if profile and profile.region_id == region_id and profile.crop_id == crop_id else None
    end = on_date + timedelta(days=30)
    events = []
    if planting.date and on_date <= planting.date <= end:
        events.append({"date": planting.date.isoformat(),
            "title": f"Planned {crop_name} sowing", "action": "Confirm field readiness and your recorded plan.",
            "source": "Farmer-entered crop plan", "sourceVersion": "recorded-date-v1",
            "certainty": planting.certainty})
    if matched:
        for window in matched.planting_windows:
            if window.start <= end and on_date <= window.end and (
                    planting.date is None or planting.date > window.end):
                events.append({"date": max(window.start, on_date).isoformat(),
                    "endDate": window.end.isoformat(),
                    "title": f"{crop_name} regional planting window",
                    "action": "Consider field conditions and the published regional guidance.",
                    "source": window.source_id, "sourceVersion": window.evidence_version,
                    "certainty": "Regional guidance, not a farm-specific prediction."})
        for stage in matched.milestones:
            due = matched.date_for(planting, stage)
            if due is not None and on_date <= due <= end:
                events.append({"date": due.isoformat(), "title": stage.label,
                    "action": stage.guidance, "source": stage.source_id, "sourceVersion": stage.evidence_version,
                    "certainty": "Indicative timing; actual crop development depends on field conditions."})
    undated = [{"title": m.label, "guidance": m.guidance, "source": m.source_id,
                "sourceVersion": m.evidence_version}
               for m in matched.milestones if matched.date_for(planting, m) is None] if matched else []
    return {
        "farmId": str(farm_id), "plotId": str(plot_id), "plotName": plot_name,
        "cropId": str(crop_id) if crop_id else None,
        "cropName": crop_name, "plantingDate": planting.date.isoformat() if planting.date else None,
        "plantingCertainty": planting.certainty,
        "regionId": region_id,
        "regionalGuidanceAvailable": matched is not None,
        "regionalSource": matched.source_id if matched else None,
        "regionalSourceVersion": matched.source_version if matched else None,
        "regionalSourceUrl": matched.source_url if matched else None,
        "plantingWindowNote": matched.planting_window_note if matched else None,
        "next31Days": sorted(events, key=lambda row: (row["date"], row["title"])),
        "undatedActivities": undated,
        "note": ("Dates use your recorded crop plan and sourced calendar where available. "
                 "Unknown dates stay unknown; weather and scientific alerts are handled separately."),
    }
