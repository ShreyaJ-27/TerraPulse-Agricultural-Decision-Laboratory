"""Import sourced regional crop calendars, never manufacture stage offsets.

The separate Developer C advisory endpoint returns a different structured
profile. This loader is a conservative normalized adapter: only a genuinely
sourced, dated window or source-backed days-after-planting offset is alertable.
"""
from __future__ import annotations
from datetime import date
import json
from pathlib import Path
from uuid import UUID
from app.services.advisory import DEMO_REGION_ID, PUNJAB_CONTEXT

from .calendar import CalendarMilestone, CalendarWindow, CropCalendarProfile


def load_profiles(raw: list[dict]) -> dict[tuple[str, UUID], CropCalendarProfile]:
    profiles = {}
    for item in raw:
        region, crop = item["regionId"], UUID(item["cropId"])
        windows = []
        for v in item.get("plantingWindows", []):
            if not all(v.get(k) for k in ("startDate", "endDate", "sourceId", "sourceVersion")):
                continue  # Undated regional windows remain human-readable, not alert triggers.
            windows.append(CalendarWindow(v.get("code", "planting"),
                v.get("label", "Planting window"), date.fromisoformat(v["startDate"]),
                date.fromisoformat(v["endDate"]), v["sourceId"], v["sourceVersion"]))
        milestones = []
        for v in item.get("milestones", []):
            source = v.get("sourceId") or item.get("sourceId")
            version = v.get("sourceVersion") or item.get("sourceVersion")
            offset = v.get("daysAfterPlanting")
            # A qualitative milestone with no verified days offset stays undated.
            if not all((v.get("code"), v.get("label"), source, version)):
                continue
            milestones.append(CalendarMilestone(v["code"], v["label"], offset,
                source, v.get("guidance", "Review your crop and local conditions."), version))
        profile = CropCalendarProfile(region, crop, tuple(milestones),
            item["sourceId"], item["sourceVersion"],
            item.get("plantingWindowNote"), tuple(windows), item.get("sourceUrl"))
        key = (region, crop)
        if key in profiles:
            raise ValueError("duplicate crop-region calendar profile")
        profiles[key] = profile
    return profiles


def load_profiles_file(path: str | Path | None) -> dict:
    # Extension guidance publishes qualitative windows and milestones. These
    # remain undated unless an explicit schedule with provenance is supplied.
    profiles = {}
    for crop_id, context in PUNJAB_CONTEXT.items():
        source = context.source
        milestones = tuple(
            CalendarMilestone(
                item.id, item.label, None, item.source_section, item.definition, source.edition
            )
            for item in context.milestones
        )
        profiles[(DEMO_REGION_ID, crop_id)] = CropCalendarProfile(
            DEMO_REGION_ID, crop_id, milestones, source.publisher, source.edition,
            f"{context.planting_window.label}. {context.planting_window.applicability}",
            source_url=source.url,
        )
    if path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Calendar profiles file must be a JSON list")
        profiles.update(load_profiles(raw))
    return profiles
