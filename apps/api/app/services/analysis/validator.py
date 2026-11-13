from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

from app.contracts import C3ScientificState
from app.services.analysis.models import EvidenceBundle, GroundedClaim
from app.services.analysis.staleness import safe_measurement_val

DATE_REGEX = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+"
    r"\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\b",
    re.IGNORECASE,
)
CONTEXTUAL_METADATA_REGEXES = [
    re.compile(r"\b250\s*(?:-|–)?\s*(?:m|meter|meters|ಮೀ|ಮೀಟರ್|मीटर)\b", re.IGNORECASE),
    re.compile(r"\bEPSG[:\s]4326\b", re.IGNORECASE),
    re.compile(
        r"\b(?:24|48|72)\s*(?:-|–)?\s*(?:h|hr|hrs|hour|hours|ಗಂಟೆ|ಗಂಟೆಗಳ|घंटे|घंटा)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:202[4-9]|2030)\b"),
    re.compile(r"\b(?:FAO|C[1-8]|v)\s*[-:]?\s*\d+(?:\.\d+)*\b", re.IGNORECASE),
    re.compile(r"\b(?:Section|ಹಂತ|भाग)\s+\d+\b", re.IGNORECASE),
]
VALUE_TOLERANCE = 0.00005


def c1_source_id(bundle: EvidenceBundle, kind: str) -> str:
    if bundle.c1_input is not None:
        for source in bundle.c1_input.provenance:
            source_id = source.source_id.casefold()
            if kind in source_id or (kind == "weather" and "meteo" in source_id):
                return source.source_id
        for source_id in bundle.c1_input.data_source_ids:
            folded = source_id.casefold()
            if kind in folded or (kind == "weather" and "meteo" in folded):
                return source_id
    return "open-meteo" if kind == "weather" else "soilgrids-250m"


def c3_source_id(bundle: EvidenceBundle, state: C3ScientificState) -> str:
    run_id = (bundle.simulation_metadata or {}).get("simulationRunId")
    return f"simulation:{run_id or state.simulation_run_id}"


def c5_source_id(bundle: EvidenceBundle) -> str:
    comparison_id = (bundle.comparison_metadata or {}).get("comparisonId")
    return f"comparison:{comparison_id}" if comparison_id else "terrapulse-compare-1.0"


def _are_units_compatible(unit_a: str, unit_b: str) -> bool:
    normalize = lambda unit: unit.strip().casefold().replace(" ", "").replace("²", "2")
    u1, u2 = normalize(unit_a), normalize(unit_b)
    if u1 == u2:
        return True
    synonyms = (
        {"degc", "°c", "c", "celsius"},
        {"degrees", "deg", "degree"},
        {"m2", "m^2", "sqm", "meter2"},
        {"m3/m3", "m³/m³"},
        {"mm/day", "mmperday"},
    )
    return any(u1 in group and u2 in group for group in synonyms)


class QuantitativeClaimValidator:
    """Validates claims against one exact, available evidence field."""

    @staticmethod
    def _weather_stale(bundle: EvidenceBundle) -> bool:
        if bundle.c1_input is None:
            return False
        retrieved_at = bundle.c1_input.retrieved_at
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=UTC)
        return (datetime.now(UTC) - retrieved_at).total_seconds() > 24 * 60 * 60

    @classmethod
    def resolve_source_field_spec(
        cls, source_field: str, bundle: EvidenceBundle
    ) -> dict[str, Any] | None:
        farm_source = f"terrapulse-onboarding-c2-{bundle.farm.farm_id}"
        if source_field == "c2.farm.location.latitude":
            return cls._spec(bundle.farm.location.latitude, "degrees", "observation", farm_source, "latitude")
        if source_field == "c2.farm.location.longitude":
            return cls._spec(bundle.farm.location.longitude, "degrees", "observation", farm_source, "longitude")
        if source_field == "c2.plot.areaM2":
            measurement = bundle.plot.area_m2
            value = safe_measurement_val(measurement)
            if value is not None:
                return cls._spec(value, measurement.unit, "observation", farm_source, "plot_area")

        c1 = bundle.c1_input
        if c1 is not None:
            soil = c1.soil
            soil_fields = {
                "c1.soil.depthCm": (soil.depth_cm, "soil_depth"),
                "c1.soil.fieldCapacity": (soil.field_capacity, "field_capacity"),
                "c1.soil.wiltingPoint": (soil.wilting_point, "wilting_point"),
                "c1.soil.bulkDensity": (soil.bulk_density, "bulk_density"),
            }
            if source_field in soil_fields:
                measurement, metric = soil_fields[source_field]
                value = safe_measurement_val(measurement)
                if value is not None and measurement is not None:
                    return cls._spec(
                        value,
                        measurement.unit,
                        "gridded_modelled",
                        c1_source_id(bundle, "soil"),
                        metric,
                    )

            days = c1.daily_weather
            if days:
                weather_id = c1_source_id(bundle, "weather")
                stale = cls._weather_stale(bundle)
                rainfall_by_member: dict[str | None, list[float]] = {}
                for day in days:
                    value = safe_measurement_val(day.rainfall_mm)
                    if value is not None:
                        rainfall_by_member.setdefault(day.ensemble_member_id, []).append(value)
                rainfall_totals = [sum(values) for values in rainfall_by_member.values()]
                common_total = (
                    bool(rainfall_totals)
                    and all(
                        math.isclose(value, rainfall_totals[0], rel_tol=0.0, abs_tol=VALUE_TOLERANCE)
                        for value in rainfall_totals[1:]
                    )
                )
                if source_field == "c1.daily_weather.rainfall_mm.sum" and (
                    len(rainfall_totals) == 1 or common_total
                ):
                    missing = any(
                        safe_measurement_val(day.rainfall_mm) is None for day in days
                    )
                    spec = cls._spec(
                        rainfall_totals[0], "mm", "gridded_modelled", weather_id, "total_rainfall", stale
                    )
                    if missing:
                        spec["required_qualifications"] = ["incomplete_daily_coverage"]
                    return spec
                if source_field == "c1.daily_weather.rainfall_mm.min" and len(rainfall_totals) > 1:
                    spec = cls._spec(
                        min(rainfall_totals), "mm", "gridded_modelled", weather_id, "min_ensemble_rainfall", stale
                    )
                    if any(safe_measurement_val(day.rainfall_mm) is None for day in days):
                        spec["required_qualifications"] = ["incomplete_daily_coverage"]
                    return spec
                if source_field == "c1.daily_weather.rainfall_mm.max" and len(rainfall_totals) > 1:
                    spec = cls._spec(
                        max(rainfall_totals), "mm", "gridded_modelled", weather_id, "max_ensemble_rainfall", stale
                    )
                    if any(safe_measurement_val(day.rainfall_mm) is None for day in days):
                        spec["required_qualifications"] = ["incomplete_daily_coverage"]
                    return spec
                weather_specs = (
                    (
                        "c1.daily_weather.temperature_min_c.min",
                        [safe_measurement_val(day.temperature_min_c) for day in days],
                        "min_temperature",
                        "degC",
                    ),
                    (
                        "c1.daily_weather.temperature_max_c.max",
                        [safe_measurement_val(day.temperature_max_c) for day in days],
                        "max_temperature",
                        "degC",
                    ),
                    (
                        "c1.daily_weather.reference_evapotranspiration_mm.mean",
                        [safe_measurement_val(day.reference_evapotranspiration_mm) for day in days],
                        "mean_et0",
                        "mm/day",
                    ),
                )
                for field, values, metric, unit in weather_specs:
                    valid = [value for value in values if value is not None]
                    if source_field == field and valid:
                        value = sum(valid) / len(valid) if metric == "mean_et0" else (
                            min(valid) if metric == "min_temperature" else max(valid)
                        )
                        spec = cls._spec(value, unit, "gridded_modelled", weather_id, metric, stale)
                        if len(valid) < len(days):
                            spec["required_qualifications"] = ["incomplete_daily_coverage"]
                        return spec

        if bundle.c3_states:
            latest = max(bundle.c3_states, key=lambda state: state.date)
            c3_fields = {
                "c3.cropWaterDemand": (latest.crop_water_demand, "crop_water_demand"),
                "c3.actualEvapotranspiration": (
                    latest.actual_evapotranspiration,
                    "actual_evapotranspiration",
                ),
                "c3.waterStress": (latest.water_stress, "water_stress"),
                "c3.soilWater": (latest.soil_water, "soil_water"),
                "c3.irrigation": (latest.irrigation, "irrigation"),
            }
            if source_field in c3_fields:
                measurement, metric = c3_fields[source_field]
                value = safe_measurement_val(measurement)
                if value is not None:
                    return cls._spec(
                        value,
                        measurement.unit,
                        "simulation_state",
                        c3_source_id(bundle, latest),
                        metric,
                    )

        if bundle.c5_comparison is not None:
            source_id = c5_source_id(bundle)
            for metric in bundle.c5_comparison.metrics:
                if source_field == f"c5.metrics[{metric.metric}].difference":
                    value = safe_measurement_val(metric.difference)
                    if value is not None:
                        return cls._spec(
                            value,
                            metric.difference.unit,
                            "comparison_derived",
                            source_id,
                            f"{metric.metric}_difference",
                        )
        return None

    @classmethod
    def available_source_specs(cls, bundle: EvidenceBundle) -> list[dict[str, Any]]:
        fields = [
            "c2.plot.areaM2",
            "c1.soil.depthCm",
            "c1.soil.fieldCapacity",
            "c1.soil.wiltingPoint",
            "c1.soil.bulkDensity",
            "c1.daily_weather.rainfall_mm.sum",
            "c1.daily_weather.rainfall_mm.min",
            "c1.daily_weather.rainfall_mm.max",
            "c1.daily_weather.temperature_min_c.min",
            "c1.daily_weather.temperature_max_c.max",
            "c1.daily_weather.reference_evapotranspiration_mm.mean",
            "c3.cropWaterDemand",
            "c3.actualEvapotranspiration",
            "c3.waterStress",
            "c3.soilWater",
            "c3.irrigation",
        ]
        if bundle.c5_comparison is not None:
            fields.extend(
                f"c5.metrics[{metric.metric}].difference"
                for metric in bundle.c5_comparison.metrics
            )
        return [
            {
                "sourceField": field,
                "metric": spec["metric"],
                "value": spec["value"],
                "unit": spec["unit"],
                "sourceId": spec["source_id"],
                "category": spec["category"],
                "isStale": spec["is_stale"],
                "qualifications": spec["required_qualifications"],
            }
            for field in fields
            if (spec := cls.resolve_source_field_spec(field, bundle)) is not None
        ]

    @staticmethod
    def _spec(
        value: float,
        unit: str,
        category: str,
        source_id: str,
        metric: str,
        is_stale: bool = False,
    ) -> dict[str, Any]:
        return {
            "value": value,
            "unit": unit,
            "category": category,
            "source_id": source_id,
            "metric": metric,
            "is_stale": is_stale,
            "required_qualifications": [],
        }

    @classmethod
    def validate_claims(
        cls, claims: list[GroundedClaim], bundle: EvidenceBundle
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []
        seen_ids: set[str] = set()
        for claim in claims:
            if claim.claim_id in seen_ids:
                errors.append(f"Claim ID '{claim.claim_id}' is repeated.")
            seen_ids.add(claim.claim_id)
            spec = cls.resolve_source_field_spec(claim.source_field, bundle)
            if spec is None:
                errors.append(
                    f"Claim '{claim.claim_id}' cites a source field that is missing or unavailable."
                )
                continue
            if not math.isclose(
                claim.value, spec["value"], rel_tol=0.0, abs_tol=VALUE_TOLERANCE
            ):
                errors.append(
                    f"Claim '{claim.claim_id}' does not match the value at its cited source field."
                )
            if not _are_units_compatible(claim.unit, spec["unit"]):
                errors.append(f"Claim '{claim.claim_id}' uses a unit incompatible with its source.")
            if claim.source_id != spec["source_id"]:
                errors.append(f"Claim '{claim.claim_id}' cites the wrong source ID.")
            if claim.category != spec["category"]:
                errors.append(f"Claim '{claim.claim_id}' has the wrong evidence category.")
            if claim.metric != spec["metric"]:
                errors.append(f"Claim '{claim.claim_id}' metric does not correspond to its source field.")
            if claim.is_stale != spec["is_stale"]:
                errors.append(f"Claim '{claim.claim_id}' did not preserve source staleness.")
            if not set(spec["required_qualifications"]).issubset(claim.qualifications):
                errors.append(f"Claim '{claim.claim_id}' omitted a required evidence qualification.")
        return not errors, errors

    @classmethod
    def validate_text(
        cls, text: str, bundle: EvidenceBundle, claims: list[GroundedClaim]
    ) -> tuple[bool, list[str]]:
        """Only numbers represented by validated claims may appear in generated prose."""
        del bundle
        masked = DATE_REGEX.sub(" <DATE> ", text)
        for pattern in CONTEXTUAL_METADATA_REGEXES:
            masked = pattern.sub(" <METADATA> ", masked)
        tokens = re.findall(r"(?<![\w])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b", masked)
        claim_values = [claim.value for claim in claims]
        unverified: list[str] = []
        for token in tokens:
            value = float(token)
            if not any(
                math.isclose(value, claim_value, rel_tol=0.0, abs_tol=VALUE_TOLERANCE)
                for claim_value in claim_values
            ):
                unverified.append(token)
        return not unverified, unverified
