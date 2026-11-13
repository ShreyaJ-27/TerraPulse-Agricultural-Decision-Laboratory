"""Versioned, JSON-serializable boundaries around Developer D's C1/C3/C5/C7/C8.

Existing Developer D v0.1 wire types are not replaced. The v0.2 response
contains a v0.1-compatible C3 view and a separate scientific envelope.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Any
import hashlib
import json
import math
import re

CONTRACT_VERSION = "science-0.2"
FAO_ENGINE_VERSION = "fao56-single-kc-1.0"
BALANCE_TOL_MM = 1e-9

class ScienceError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message

def fail(code: str, message: str):
    raise ScienceError(code, message)

def real(value: Any, field: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail("INVALID_NUMBER", f"{field} must be a finite number")
    x = float(value)
    if minimum is not None and x < minimum:
        fail("INVALID_RANGE", f"{field} must be >= {minimum}")
    if maximum is not None and x > maximum:
        fail("INVALID_RANGE", f"{field} must be <= {maximum}")
    return x

def iso_date(value: Any, field: str = "date") -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        fail("INVALID_DATE", f"{field} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail("INVALID_DATE", f"{field} is not a calendar date")

def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail("MISSING_IDENTITY", f"{field} is required")
    return value

def stable_hash(obj: Any) -> str:
    encoded = json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

@dataclass(frozen=True)
class WeatherDay:
    date: str
    rainfall_mm: float
    reference_et_mm: float
    provenance: dict[str, Any]
    member_id: str | None = None
    min_temp_c: float | None = None
    max_temp_c: float | None = None
    runoff_mm: float = 0.0

    def validate(self):
        iso_date(self.date)
        real(self.rainfall_mm, "rainfall_mm", minimum=0)
        real(self.reference_et_mm, "reference_et_mm", minimum=0)
        real(self.runoff_mm, "runoff_mm", minimum=0)
        if self.runoff_mm > self.rainfall_mm:
            fail("RUNOFF_EXCEEDS_RAIN", "runoff must not exceed rainfall")
        if self.min_temp_c is not None:
            real(self.min_temp_c, "min_temp_c")
        if self.max_temp_c is not None:
            real(self.max_temp_c, "max_temp_c")
        if self.min_temp_c is not None and self.max_temp_c is not None and self.max_temp_c < self.min_temp_c:
            fail("INVALID_TEMPERATURE", "max_temp_c below min_temp_c")
        if not isinstance(self.provenance, dict) or any(not self.provenance.get(k) for k in ("provider","kind","reference","acquiredAt")):
            fail("MISSING_PROVENANCE", f"weather provenance missing for {self.date}")
        if self.provenance["kind"] not in {"observation", "model-estimate", "forecast", "assumption"}:
            fail("INVALID_PROVENANCE", f"weather provenance kind invalid for {self.date}")
        if self.member_id is not None and (not isinstance(self.member_id, str) or not self.member_id):
            fail("INVALID_MEMBER", "ensemble member must be a non-empty string or null")

@dataclass(frozen=True)
class Soil:
    root_depth_m: float
    field_capacity: float
    wilting_point: float
    depletion_fraction: float
    parameter_source: str
    parameter_version: str

    def validate(self):
        zr = real(self.root_depth_m, "root_depth_m")
        fc = real(self.field_capacity, "field_capacity")
        wp = real(self.wilting_point, "wilting_point")
        p = real(self.depletion_fraction, "depletion_fraction")
        if not (zr > 0 and 0 <= wp < fc <= 1 and 0 <= p < 1):
            fail("INVALID_SOIL", "require rootDepth>0, 0<=WP<FC<=1 and 0<=p<1")
        nonempty(self.parameter_source, "soil.parameter_source")
        nonempty(self.parameter_version, "soil.parameter_version")

    @property
    def taw_mm(self) -> float:
        return 1000 * (self.field_capacity - self.wilting_point) * self.root_depth_m

@dataclass(frozen=True)
class CropKc:
    scientific_name: str
    parameter_version: str
    parameter_source: str
    kc_initial: float
    kc_mid: float
    kc_end: float
    stage_lengths_days: tuple[int, int, int, int]
    mapping_status: str = "provisional"

    def validate(self):
        nonempty(self.scientific_name, "crop.scientific_name")
        nonempty(self.parameter_version, "crop.parameter_version")
        nonempty(self.parameter_source, "crop.parameter_source")
        for name in ("kc_initial", "kc_mid", "kc_end"):
            real(getattr(self, name), name, minimum=0)
        if len(self.stage_lengths_days) != 4 or any(type(x) is not int or x <= 0 for x in self.stage_lengths_days):
            fail("INVALID_STAGE_LENGTHS", "exactly four positive integer stage lengths required")
        if self.mapping_status not in {"provisional", "calibrated"}:
            fail("INVALID_MAPPING_STATUS", "mapping status must be provisional or calibrated")

    @property
    def duration_days(self) -> int:
        return sum(self.stage_lengths_days)

@dataclass(frozen=True)
class FaoRequest:
    plot_id: str
    branch_id: str
    area_m2: float
    planting_date: str
    start_date: str
    end_date: str
    weather_realization_id: str
    input_snapshot_id: str
    initial_depletion_mm: float
    soil: Soil
    crop: CropKc
    weather: tuple[WeatherDay, ...]
    irrigation_mm_by_date: dict[str, float]
    irrigation_source: str
    fallow_kc: float | None

    def validate(self):
        nonempty(self.plot_id, "plot_id")
        nonempty(self.branch_id, "branch_id")
        nonempty(self.weather_realization_id, "weather_realization_id")
        nonempty(self.input_snapshot_id, "input_snapshot_id")
        real(self.area_m2, "area_m2", minimum=0)
        if self.area_m2 == 0:
            fail("INVALID_AREA", "area_m2 must be strictly positive")
        start = iso_date(self.start_date, "start_date")
        end = iso_date(self.end_date, "end_date")
        planting = iso_date(self.planting_date, "planting_date")
        if not start <= planting <= end:
            fail("INVALID_WINDOW", "common start must be <= planting <= end")
        if (end-start).days > 4000:
            fail("INVALID_WINDOW", "simulation exceeds 4001 days")
        self.soil.validate()
        self.crop.validate()
        dep = real(self.initial_depletion_mm, "initial_depletion_mm", minimum=0)
        if dep > self.soil.taw_mm + BALANCE_TOL_MM:
            fail("INVALID_DEPLETION", "initial depletion > TAW")
        if self.fallow_kc is None and start < planting:
            fail("FALLOW_ASSUMPTION_REQUIRED", "declare explicit fallow Kc for dates before planting")
        if self.fallow_kc is None and end >= planting + timedelta(days=self.crop.duration_days):
            fail("FALLOW_ASSUMPTION_REQUIRED", "declare explicit fallow Kc for dates after crop season")
        if self.fallow_kc is not None:
            real(self.fallow_kc, "fallow_kc", minimum=0)
        if self.irrigation_source not in {"c8-ledger", "explicit-fixture"}:
            fail("INVALID_IRRIGATION_SOURCE", "source must be c8-ledger or explicit-fixture")
        dates = [w.date for w in self.weather]
        if len(set(dates)) != len(dates):
            fail("DUPLICATE_WEATHER", "duplicate dated weather inputs")
        expected = [(start + timedelta(days=i)).isoformat() for i in range((end-start).days+1)]
        if dates != expected:
            fail("WEATHER_COVERAGE", "weather must cover every calendar day exactly, sorted, with no gaps")
        members = set()
        for w in self.weather:
            w.validate()
            members.add(w.member_id)
        if len(members) > 1:
            fail("MIXED_WEATHER_MEMBERS", "weather cannot mix ensemble members")
        for day, val in self.irrigation_mm_by_date.items():
            iso_date(day, "irrigation date")
            if day < self.start_date or day > self.end_date:
                fail("IRRIGATION_WINDOW", "irrigation outside simulation window")
            real(val, "effective irrigation depth", minimum=0)

    def comparable_baseline(self) -> dict:
        """Identity of inputs that must match for management comparisons.

        Crop and planting date are intentionally omitted so users can change them.
        Distinct crop or parameter versions are still flagged by compare_runs.
        """
        return {"plotId": self.plot_id, "areaM2": self.area_m2,
                "weatherRealizationId": self.weather_realization_id,
                "weatherHash": stable_hash([asdict(w) for w in self.weather]),
                "startDate": self.start_date, "endDate": self.end_date,
                "soil": asdict(self.soil), "initialDepletionMm": self.initial_depletion_mm,
                "inputSnapshotId": self.input_snapshot_id, "fallowKc": self.fallow_kc}

    def input_hash(self) -> str:
        return stable_hash(asdict(self))


def request_from_dict(raw: dict) -> FaoRequest:
    if not isinstance(raw, dict):
        fail("INVALID_REQUEST", "expected object")
    try:
        soil = Soil(**raw["soil"])
        crop_raw = dict(raw["crop"])
        crop_raw["stage_lengths_days"] = tuple(crop_raw["stage_lengths_days"])
        crop = CropKc(**crop_raw)
        weather = tuple(WeatherDay(**w) for w in raw["weather"])
        request = FaoRequest(soil=soil, crop=crop, weather=weather,
                             plot_id=raw["plot_id"], branch_id=raw["branch_id"],
                             area_m2=raw["area_m2"], planting_date=raw["planting_date"],
                             start_date=raw["start_date"], end_date=raw["end_date"],
                             weather_realization_id=raw["weather_realization_id"],
                             input_snapshot_id=raw["input_snapshot_id"],
                             initial_depletion_mm=raw["initial_depletion_mm"],
                             irrigation_mm_by_date=raw.get("irrigation_mm_by_date", {}),
                             irrigation_source=raw.get("irrigation_source", "explicit-fixture"),
                             fallow_kc=raw.get("fallow_kc"))
    except (KeyError, TypeError, AttributeError) as exc:
        fail("INVALID_REQUEST", f"incomplete or invalid request structure: {exc}")
    request.validate()
    return request
