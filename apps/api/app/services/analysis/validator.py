from __future__ import annotations

import math
import re
from typing import Any

from app.contracts import DataStatus
from app.services.analysis.models import (
    EvidenceBundle,
    GroundedClaim,
)
from app.services.analysis.staleness import safe_measurement_val

# Recognized date expressions: ISO dates, slash dates, and month-name calendar dates
DATE_REGEX = re.compile(
    r"\b(?:"
    r"\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD
    r"|\d{2}/\d{2}/\d{4}"  # DD/MM/YYYY
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)(?:\s+\d{4})?"
    r")\b",
    re.IGNORECASE,
)

# Legitimate system metadata patterns in explicit linguistic contexts
CONTEXTUAL_METADATA_REGEXES = [
    # SoilGrids 250m resolution
    re.compile(r"\b250\s*(?:-|–)?\s*(?:m|meter|meters|ಮೀ|ಮೀಟರ್|मीटर)\b", re.IGNORECASE),
    # EPSG:4326 coordinate system
    re.compile(r"\bEPSG[:\s]4326\b", re.IGNORECASE),
    # 24, 48, 72 hour forecast windows
    re.compile(
        r"\b(?:24|48|72)\s*(?:-|–)?\s*(?:h|hr|hrs|hour|hours|ಗಂಟೆ|ಗಂಟೆಗಳ|घंटे|घंटा)\b",
        re.IGNORECASE,
    ),
    # Year in isolated 2024-2030 range
    re.compile(r"\b(?:202[4-9]|2030)\b"),
    # Section numbers e.g. "Section 1", "ಹಂತ 1", "भाग 1"
    re.compile(r"\b(?:Section|ಹಂತ|भाग)\s+\d+\b", re.IGNORECASE),
]


def _are_units_compatible(unit_a: str, unit_b: str) -> bool:
    """Checks whether two units are equivalent or standard synonyms."""
    u1 = unit_a.strip().lower().replace(" ", "")
    u2 = unit_b.strip().lower().replace(" ", "")
    if u1 == u2:
        return True
    temp_units = {"degc", "°c", "c", "celsius"}
    if u1 in temp_units and u2 in temp_units:
        return True
    coord_units = {"degrees", "deg", "degree"}
    if u1 in coord_units and u2 in coord_units:
        return True
    area_units = {"m2", "m^2", "sqm", "meter2"}
    return bool(u1 in area_units and u2 in area_units)


class QuantitativeClaimValidator:
    """Validates quantitative assertions against authoritative EvidenceBundle values.

    Guarantees that no invented, ungrounded, or hallucinated numbers enter the explanation,
    and enforces strict field-to-metric correspondence.
    """

    @classmethod
    def collect_evidence_numbers(cls, bundle: EvidenceBundle) -> set[float]:
        """Harvests all valid numerical measurements and dimensions from the EvidenceBundle."""
        numbers: set[float] = set()

        # Coordinates
        numbers.add(round(bundle.farm.location.latitude, 4))
        numbers.add(round(bundle.farm.location.longitude, 4))

        # Plot Area
        if bundle.plot.area_m2 and bundle.plot.area_m2.value is not None:
            numbers.add(round(bundle.plot.area_m2.value, 2))

        # C1 Environmental Input
        if bundle.c1_input is not None:
            # Soil
            soil = bundle.c1_input.soil
            if soil is not None:
                for m in (soil.depth_cm, soil.field_capacity, soil.wilting_point, soil.bulk_density):
                    if m is not None and m.availability.status == DataStatus.AVAILABLE and m.value is not None:
                        numbers.add(round(m.value, 4))
                        numbers.add(round(m.value, 2))
                        numbers.add(round(m.value, 1))

            # Daily Weather
            for w in bundle.c1_input.daily_weather:
                for m in (w.temperature_min_c, w.temperature_max_c, w.rainfall_mm, w.reference_evapotranspiration_mm):
                    if m is not None and m.availability.status == DataStatus.AVAILABLE and m.value is not None:
                        numbers.add(round(m.value, 4))
                        numbers.add(round(m.value, 2))
                        numbers.add(round(m.value, 1))

        # C3 Simulation States
        for state in bundle.c3_states:
            for m in (
                state.soil_water,
                state.root_zone,
                state.crop_water_demand,
                state.actual_evapotranspiration,
                state.water_stress,
                state.irrigation,
                state.rainfall,
                state.drainage,
                state.runoff,
                state.biomass,
                state.yield_,
            ):
                if m is not None and m.availability.status == DataStatus.AVAILABLE and m.value is not None:
                    numbers.add(round(m.value, 4))
                    numbers.add(round(m.value, 2))
                    numbers.add(round(m.value, 1))

        # C5 Comparison Metrics
        if bundle.c5_comparison is not None:
            for cm in bundle.c5_comparison.metrics:
                for m in (cm.value_a, cm.value_b, cm.difference):
                    if m is not None and m.availability.status == DataStatus.AVAILABLE and m.value is not None:
                        numbers.add(round(m.value, 4))
                        numbers.add(round(m.value, 2))
                        numbers.add(round(m.value, 1))

        return numbers

    @classmethod
    def resolve_source_field_spec(cls, source_field: str, bundle: EvidenceBundle) -> dict[str, Any] | None:
        """Resolves the authoritative value, unit, category, and source ID for a specific source_field dot-path."""
        # 1. Farm Coordinates
        if source_field == "c2.farm.location.latitude":
            return {
                "value": bundle.farm.location.latitude,
                "unit": "degrees",
                "category": "observation",
                "source_id": "c2-farm-coordinates",
            }
        if source_field == "c2.farm.location.longitude":
            return {
                "value": bundle.farm.location.longitude,
                "unit": "degrees",
                "category": "observation",
                "source_id": "c2-farm-coordinates",
            }

        # 2. Plot Area
        if source_field == "c2.plot.areaM2":
            val = safe_measurement_val(bundle.plot.area_m2)
            if val is not None:
                return {
                    "value": val,
                    "unit": bundle.plot.area_m2.unit,
                    "category": "observation",
                    "source_id": "c2-farm-plot",
                }

        # 3. C1 Soil Properties
        if bundle.c1_input is not None and bundle.c1_input.soil is not None:
            soil = bundle.c1_input.soil
            if source_field == "c1.soil.depthCm":
                val = safe_measurement_val(soil.depth_cm)
                if val is not None:
                    return {"value": val, "unit": soil.depth_cm.unit, "category": "gridded_modelled", "source_id": "soilgrids-250m"}
            if source_field == "c1.soil.fieldCapacity":
                val = safe_measurement_val(soil.field_capacity)
                if val is not None:
                    return {"value": val, "unit": soil.field_capacity.unit, "category": "gridded_modelled", "source_id": "soilgrids-250m"}
            if source_field == "c1.soil.wiltingPoint":
                val = safe_measurement_val(soil.wilting_point)
                if val is not None:
                    return {"value": val, "unit": soil.wilting_point.unit, "category": "gridded_modelled", "source_id": "soilgrids-250m"}
            if source_field == "c1.soil.bulkDensity":
                val = safe_measurement_val(soil.bulk_density)
                if val is not None and soil.bulk_density is not None:
                    return {"value": val, "unit": soil.bulk_density.unit, "category": "gridded_modelled", "source_id": "soilgrids-250m"}

        # 4. C1 Daily Weather Aggregates
        if bundle.c1_input is not None and bundle.c1_input.daily_weather:
            days = bundle.c1_input.daily_weather
            if source_field == "c1.daily_weather.rainfall_mm.sum":
                valid_rains = [safe_measurement_val(d.rainfall_mm) for d in days if safe_measurement_val(d.rainfall_mm) is not None]
                if valid_rains:
                    return {"value": sum(valid_rains), "unit": "mm", "category": "gridded_modelled", "source_id": "open-meteo"}
            if source_field == "c1.daily_weather.temperature_min_c.min":
                tmins = [safe_measurement_val(d.temperature_min_c) for d in days if safe_measurement_val(d.temperature_min_c) is not None]
                if tmins:
                    return {"value": min(tmins), "unit": "degC", "category": "gridded_modelled", "source_id": "open-meteo"}
            if source_field == "c1.daily_weather.temperature_max_c.max":
                tmaxs = [safe_measurement_val(d.temperature_max_c) for d in days if safe_measurement_val(d.temperature_max_c) is not None]
                if tmaxs:
                    return {"value": max(tmaxs), "unit": "degC", "category": "gridded_modelled", "source_id": "open-meteo"}
            if source_field == "c1.daily_weather.reference_evapotranspiration_mm.mean":
                et0s = [safe_measurement_val(d.reference_evapotranspiration_mm) for d in days if safe_measurement_val(d.reference_evapotranspiration_mm) is not None]
                if et0s:
                    return {"value": sum(et0s) / len(et0s), "unit": "mm/day", "category": "gridded_modelled", "source_id": "open-meteo"}

        # 5. C3 Scientific States
        if bundle.c3_states:
            latest = bundle.c3_states[-1]
            engine_id = f"terrapulse-{latest.engine.name.lower()}-{latest.engine.version}"
            if source_field == "c3.cropWaterDemand":
                val = safe_measurement_val(latest.crop_water_demand)
                if val is not None:
                    return {"value": val, "unit": latest.crop_water_demand.unit, "category": "simulation_state", "source_id": engine_id}
            if source_field == "c3.actualEvapotranspiration":
                val = safe_measurement_val(latest.actual_evapotranspiration)
                if val is not None:
                    return {"value": val, "unit": latest.actual_evapotranspiration.unit, "category": "simulation_state", "source_id": engine_id}
            if source_field == "c3.waterStress":
                val = safe_measurement_val(latest.water_stress)
                if val is not None:
                    return {"value": val, "unit": latest.water_stress.unit, "category": "simulation_state", "source_id": engine_id}
            if source_field == "c3.soilWater":
                val = safe_measurement_val(latest.soil_water)
                if val is not None:
                    return {"value": val, "unit": latest.soil_water.unit, "category": "simulation_state", "source_id": engine_id}
            if source_field == "c3.irrigation":
                val = safe_measurement_val(latest.irrigation)
                if val is not None:
                    return {"value": val, "unit": latest.irrigation.unit, "category": "simulation_state", "source_id": engine_id}

        # 6. C5 Comparison Metrics
        if bundle.c5_comparison is not None:
            for cm in bundle.c5_comparison.metrics:
                if source_field in (f"c5.metrics[{cm.metric}].difference", f"c5.metrics[{cm.metric}_difference].difference"):
                    val = safe_measurement_val(cm.difference)
                    if val is not None:
                        return {"value": val, "unit": cm.difference.unit, "category": "comparison_derived", "source_id": "terrapulse-compare-1.0"}

        return None

    @classmethod
    def validate_claims(
        cls,
        claims: list[GroundedClaim],
        bundle: EvidenceBundle,
    ) -> tuple[bool, list[str]]:
        """Verifies each GroundedClaim against the exact source field in the EvidenceBundle.

        Guarantees that a claim cannot validate against an unrelated numerical value.
        """
        errors: list[str] = []

        for claim in claims:
            spec = cls.resolve_source_field_spec(claim.source_field, bundle)
            if spec is None:
                errors.append(
                    f"Claim '{claim.claim_id}' cites source field '{claim.source_field}', "
                    f"which does not exist or is unavailable in the evidence bundle."
                )
                continue

            # Verify numeric value matches the specific source field (within tolerance)
            expected_val = spec["value"]
            if not math.isclose(claim.value, expected_val, rel_tol=1e-2, abs_tol=1e-2):
                errors.append(
                    f"Claim '{claim.claim_id}' ({claim.metric}={claim.value}) does not match "
                    f"the actual value ({expected_val}) at source field '{claim.source_field}'."
                )

            # Verify units match
            if not _are_units_compatible(claim.unit, spec["unit"]):
                errors.append(
                    f"Claim '{claim.claim_id}' specifies unit '{claim.unit}', but the source field "
                    f"'{claim.source_field}' has unit '{spec['unit']}'."
                )

            # Verify category matches
            if claim.category != spec["category"]:
                errors.append(
                    f"Claim '{claim.claim_id}' specifies category '{claim.category}', but expected '{spec['category']}'."
                )

        return len(errors) == 0, errors

    @classmethod
    def validate_text(
        cls,
        text: str,
        bundle: EvidenceBundle,
        claims: list[GroundedClaim],
    ) -> tuple[bool, list[str]]:
        """Extracts signed numeric tokens from generated text and checks that each has an authoritative evidence source.

        Recognized calendar date expressions and contextual system metadata (e.g. 250m SoilGrids, EPSG:4326)
        are masked prior to extraction. Arbitrary bare integers (such as 25 bags, 10 quintals, 30 rupees) are NOT exempted.
        """
        evidence_numbers = cls.collect_evidence_numbers(bundle)
        for c in claims:
            evidence_numbers.add(round(c.value, 4))
            evidence_numbers.add(round(c.value, 2))
            evidence_numbers.add(round(c.value, 1))

        # 1. Mask valid calendar dates
        masked_text = DATE_REGEX.sub(" <CALENDAR_DATE> ", text)

        # 2. Mask contextual system metadata
        for pattern in CONTEXTUAL_METADATA_REGEXES:
            masked_text = pattern.sub(" <SYS_METADATA> ", masked_text)

        # 3. Extract signed number tokens: integers, decimals, and scientific notation
        tokens = re.findall(r"(?<![\w])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b", masked_text)
        unmatched: list[str] = []

        for token in tokens:
            try:
                num = float(token)
            except ValueError:
                continue

            num_r4 = round(num, 4)
            num_r2 = round(num, 2)
            num_r1 = round(num, 1)

            matched = (
                num_r4 in evidence_numbers
                or num_r2 in evidence_numbers
                or num_r1 in evidence_numbers
                or any(math.isclose(num, ev, rel_tol=1e-2, abs_tol=1e-2) for ev in evidence_numbers)
            )

            if not matched:
                unmatched.append(token)

        return len(unmatched) == 0, unmatched
