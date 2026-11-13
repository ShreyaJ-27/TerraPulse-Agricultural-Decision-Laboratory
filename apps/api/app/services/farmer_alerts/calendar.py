"""Agricultural calendar contracts. Sourced schedules only; no invented crop stages."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal
from uuid import UUID

DateCertainty = Literal["confirmed", "estimated", "unconfirmed", "recorded"]

@dataclass(frozen=True)
class PlantingDate:
    date: date | None
    certainty: DateCertainty = "recorded"

    @classmethod
    def from_plot(cls, planting_date: date | None, management: dict) -> PlantingDate:
        certainty = management.get("plantingDateCertainty", "recorded")
        if planting_date is None:
            return cls(None, "unconfirmed")
        if certainty not in ("recorded", "confirmed", "estimated"):
            certainty = "recorded"
        return cls(planting_date, certainty)

    def __post_init__(self):
        if self.certainty == "unconfirmed" and self.date is not None:
            raise ValueError("unconfirmed planting date must be absent")
        if self.certainty != "unconfirmed" and self.date is None:
            raise ValueError("dated planting requires a date; use unconfirmed otherwise")

@dataclass(frozen=True)
class CalendarMilestone:
    """Source-backed relative milestone. None means not dateable and not alertable."""
    code: str
    label: str
    days_after_planting: int | None
    source_id: str
    guidance: str
    evidence_version: str

    def __post_init__(self):
        if not self.code or not self.label or not self.source_id or not self.evidence_version:
            raise ValueError("milestone name and scientific provenance required")
        if self.days_after_planting is not None and not 0 <= self.days_after_planting <= 1095:
            raise ValueError("invalid crop milestone offset")

@dataclass(frozen=True)
class CalendarWindow:
    """Exact sourced regional calendar dates; no approximation from season names."""
    code: str
    label: str
    start: date
    end: date
    source_id: str
    evidence_version: str

    def __post_init__(self):
        if not self.code or not self.label or not self.source_id or not self.evidence_version:
            raise ValueError("dated window requires name and provenance")
        if self.start > self.end:
            raise ValueError("calendar window end precedes start")


@dataclass(frozen=True)
class CropCalendarProfile:
    """Explicit regional coverage; never infer a profile from a crop name or district."""
    region_id: str
    crop_id: UUID
    milestones: tuple[CalendarMilestone, ...]
    source_id: str
    source_version: str
    planting_window_note: str | None = None
    planting_windows: tuple[CalendarWindow, ...] = ()
    source_url: str | None = None

    def __post_init__(self):
        if not self.region_id or not self.source_id or not self.source_version:
            raise ValueError("regional calendar requires source and version")
        if len({m.code for m in self.milestones}) != len(self.milestones):
            raise ValueError("duplicate milestone code")
        if len({w.code for w in self.planting_windows}) != len(self.planting_windows):
            raise ValueError("duplicate regional planting window")

    def date_for(self, planting: PlantingDate, milestone: CalendarMilestone) -> date | None:
        if planting.date is None or milestone.days_after_planting is None:
            return None
        return planting.date + timedelta(days=milestone.days_after_planting)
