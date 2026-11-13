"""Deterministic, provider-agnostic advisory signals from trusted C1/C3/calendar data.

Rules and thresholds are pilot *notification filters*, not agronomic diagnoses.
Every emitted event carries evidence/provenance and a stable duplicate key.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from typing import Any, Literal
from uuid import UUID

from .calendar import CropCalendarProfile, PlantingDate

Category = Literal["calendar", "weather", "science"]

@dataclass(frozen=True)
class AdvisoryEvent:
    farm_id: UUID
    plot_id: UUID
    crop_name: str
    category: Category
    kind: str
    event_date: date
    title: str
    evidence: str
    suggested_action: str
    source_id: str
    source_version: str
    evidence_hash: str
    uncertainty: str
    revision: str = ""

    @property
    def dedupe_key(self) -> str:
        # Deliberately exclude raw forecast snapshot ID to suppress repeat alerts
        # when a provider refreshes the same day's evidence. Meaningful revised
        # advice may set revision explicitly after comparing evidence changes.
        identity = [str(self.farm_id), str(self.plot_id), self.category,
                    self.kind, self.event_date.isoformat(), self.revision]
        return hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()

    def payload(self) -> dict[str, str]:
        return {"farmId": str(self.farm_id), "plotId": str(self.plot_id),
                "cropName": self.crop_name, "category": self.category,
                "kind": self.kind, "eventDate": self.event_date.isoformat(),
                "title": self.title, "evidence": self.evidence,
                "suggestedAction": self.suggested_action, "sourceId": self.source_id,
                "sourceVersion": self.source_version, "evidenceHash": self.evidence_hash,
                "uncertainty": self.uncertainty}


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def evaluate_calendar(*, farm_id: UUID, plot_id: UUID, crop_name: str,
                      planting: PlantingDate, on_date: date,
                      profile: CropCalendarProfile | None = None,
                      crop_id: UUID | None = None,
                      region_id: str | None = None) -> list[AdvisoryEvent]:
    """Recorded sowing reminders plus optional genuinely sourced stage milestones."""
    events: list[AdvisoryEvent] = []
    if planting.date is not None and planting.date - on_date in (
            timedelta(days=7), timedelta(days=3), timedelta(days=1), timedelta(days=0)):
        days = (planting.date - on_date).days
        when = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        events.append(AdvisoryEvent(
            farm_id, plot_id, crop_name, "calendar", f"planting-reminder-{days}d", on_date,
            f"Review your planned {crop_name} planting {when}",
            f"The plot records planting on {planting.date.isoformat()} ({planting.certainty}).",
            "Check field readiness and verify the recorded date before planting.",
            "farm-plan", "recorded-date-v1", _sha([planting.date, planting.certainty]),
            "Calendar reminder from farmer-entered data; not a planting-date recommendation."))
    if profile is None:
        return events
    if profile.crop_id != crop_id or profile.region_id != region_id:
        # No geographic inference: imported Punjab calendar must not affect Mysuru.
        return events
    # A farmer who already planted does not need next-season sowing nudges.
    for window in profile.planting_windows:
        days_to_start = (window.start - on_date).days
        if planting.date is not None and planting.date <= window.end:
            continue
        if days_to_start in (7, 3, 1, 0):
            when = "today" if days_to_start == 0 else f"in {days_to_start} days"
            events.append(AdvisoryEvent(
                farm_id, plot_id, crop_name, "calendar", "regional-window-" + window.code,
                window.start, f"{crop_name}: planting window starts {when}",
                f"Regional window {window.start.isoformat()} to {window.end.isoformat()} "
                f"from {window.source_id} ({window.evidence_version}).",
                "Review your field, local conditions and planting plan; the window is guidance, not a guarantee.",
                window.source_id, window.evidence_version,
                _sha([window.code, window.start, window.end, window.evidence_version]),
                "Published regional guidance; field conditions and actual planting dates can differ."))
    for milestone in profile.milestones:
        due = profile.date_for(planting, milestone)
        if due != on_date:
            continue
        events.append(AdvisoryEvent(
            farm_id, plot_id, crop_name, "calendar", f"stage-{milestone.code}", due,
            f"{crop_name}: {milestone.label}",
            f"Regional calendar milestone from {milestone.source_id}; "
            f"calculated from your {planting.certainty} planting date.",
            milestone.guidance or "Review crop condition and regional guidance.",
            milestone.source_id, milestone.evidence_version,
            _sha([profile.region_id, crop_id, milestone.code, due, milestone.evidence_version]),
            "Milestone timing is indicative; actual crop development depends on field conditions."))
    return events


def _available_measurement(item: Any, *, unit: str) -> float | None:
    if not isinstance(item, dict) or item.get("unit") != unit:
        return None
    availability = item.get("availability")
    if not isinstance(availability, dict) or availability.get("status") != "available":
        return None
    v = item.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v):
        return None
    return float(v)


def _parse_aware_date(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    except ValueError:
        return None
    if not isinstance(dt, datetime) or dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def evaluate_weather(*, farm_id: UUID, plot_id: UUID, crop_name: str,
                     c1: dict[str, Any], on_date: date, now: datetime,
                     heavy_rain_mm: float = 20.0, max_age_hours: float = 24.0) -> list[AdvisoryEvent]:
    """Forecast review prompt, never a claim that rain *will* occur."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not 1 <= heavy_rain_mm <= 500 or not 0 < max_age_hours <= 168:
        raise ValueError("invalid weather policy")
    if c1.get("availability", {}).get("status") != "available":
        return []
    retrieved = _parse_aware_date(c1.get("retrievedAt"))
    if retrieved is None or not timedelta(0) <= now.astimezone(timezone.utc) - retrieved <= timedelta(hours=max_age_hours):
        return []
    provenance = c1.get("provenance")
    if not isinstance(provenance, list) or not provenance or not c1.get("dataSourceIds"):
        return []
    # Do not merge or average multiple ensemble members into a fake forecast.
    weather = c1.get("dailyWeather")
    if not isinstance(weather, list):
        return []
    members = {r.get("ensembleMemberId") for r in weather if isinstance(r, dict)}
    if len(members) != 1:
        return []
    events: list[AdvisoryEvent] = []
    for row in weather:
        if not isinstance(row, dict):
            continue
        try:
            d = date.fromisoformat(row["date"])
        except (KeyError, ValueError, TypeError):
            continue
        if not on_date <= d <= on_date + timedelta(days=2):
            continue
        mm = _available_measurement(row.get("rainfallMm"), unit="mm")
        if mm is None or mm < heavy_rain_mm:
            continue
        member = next(iter(members))
        events.append(AdvisoryEvent(
            farm_id, plot_id, crop_name, "weather", "forecast-rain-review", d,
            f"Review forecast rain for {crop_name} on {d.isoformat()}",
            f"A weather model projects {mm:.1f} mm of rain for {d.isoformat()}"
            f" (member {member or 'deterministic'}; retrieved {retrieved.date().isoformat()}).",
            "Recheck the latest forecast and field conditions before changing irrigation or planting.",
            ",".join(str(v) for v in c1["dataSourceIds"]), "weather-c1-v1", _sha([row, retrieved]),
            "Forecast, not an observation or guaranteed rainfall. Local field conditions may differ."))
    return events


def evaluate_science(*, farm_id: UUID, plot_id: UUID, crop_name: str,
                     c3: dict[str, Any], on_date: date, run_id: UUID,
                     stress_review_threshold: float = .35) -> list[AdvisoryEvent]:
    """C3 waterStress = 1-Ks (higher = more modelled stress), NOT soil measurement."""
    if not 0 < stress_review_threshold <= 1:
        raise ValueError("invalid scientific alert policy")
    if (c3.get("farmId") != str(farm_id) or c3.get("plotId") != str(plot_id) or
        c3.get("simulationRunId") != str(run_id) or c3.get("date") != on_date.isoformat()):
        return []
    if c3.get("availability", {}).get("status") != "available" or not c3.get("provenance"):
        return []
    stress = _available_measurement(c3.get("waterStress"), unit="fraction")
    if stress is None or not 0 <= stress <= 1 or stress < stress_review_threshold:
        return []
    engine = c3.get("engine")
    if not isinstance(engine, dict) or not engine.get("name") or not engine.get("version"):
        return []
    return [AdvisoryEvent(
        farm_id, plot_id, crop_name, "science", "modelled-water-stress", on_date,
        f"Review modeled water stress for {crop_name}",
        f"{engine['name']} {engine['version']} estimates water-stress severity "
        f"(1-Ks) at {stress:.2f} for {on_date.isoformat()} (run {run_id}).",
        "Check actual soil and crop conditions before deciding whether irrigation is needed.",
        f"science-run:{run_id}", str(engine["version"]), _sha(c3),
        "Simulation under model inputs; not a sensor observation or a prescribed irrigation volume.")]
