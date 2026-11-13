from __future__ import annotations

from datetime import UTC, datetime

from app.contracts import DataStatus, Measurement
from app.services.analysis.models import (
    EvidenceBundle,
    StalenessAssessment,
)


class StalenessEvaluator:
    """Evaluates data freshness and enforces strict scientific missingness preservation."""

    WEATHER_STALENESS_HOURS = 24.0

    @classmethod
    def evaluate(
        cls,
        bundle: EvidenceBundle,
        now: datetime | None = None,
    ) -> list[StalenessAssessment]:
        current_time = now or datetime.now(UTC)
        assessments: list[StalenessAssessment] = []

        # 1. Weather Data Freshness
        if bundle.c1_input is not None and bundle.c1_input.daily_weather:
            # Check C1 retrieved_at timestamp
            retrieved_at = bundle.c1_input.retrieved_at
            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(tzinfo=UTC)

            age_hours = max(0.0, (current_time - retrieved_at).total_seconds() / 3600.0)
            is_stale = age_hours > cls.WEATHER_STALENESS_HOURS

            freshness_label = f"stale (> {cls.WEATHER_STALENESS_HOURS:.0f}h)" if is_stale else "fresh (< 24h)"
            warning = (
                f"Weather forecast is {age_hours:.1f} hours old (threshold: {cls.WEATHER_STALENESS_HOURS:.0f}h). "
                "Conditions and numerical weather predictions may have shifted."
                if is_stale
                else None
            )

            assessments.append(
                StalenessAssessment(
                    sourceId="open-meteo",
                    dataType="daily_weather_forecast",
                    isStale=is_stale,
                    ageHours=round(age_hours, 1),
                    freshnessLabel=freshness_label,
                    warning=warning,
                )
            )
        else:
            assessments.append(
                StalenessAssessment(
                    sourceId="open-meteo",
                    dataType="daily_weather_forecast",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="not_retrieved",
                    warning="Weather forecast data was not retrieved or is missing.",
                )
            )

        # 2. Soil Data (Static Gridded Baseline)
        if bundle.c1_input is not None and bundle.c1_input.soil is not None:
            assessments.append(
                StalenessAssessment(
                    sourceId="soilgrids-250m",
                    dataType="soil_properties",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="static_modelled_baseline",
                    warning="Static 250m gridded SoilGrids baseline; not real-time in-situ telemetry.",
                )
            )
        else:
            assessments.append(
                StalenessAssessment(
                    sourceId="soilgrids-250m",
                    dataType="soil_properties",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="not_retrieved",
                    warning="Soil data was not retrieved or is missing.",
                )
            )

        # 3. Scientific Simulation States (C3)
        if bundle.c3_states:
            # Check latest state date or simulation timestamp
            assessments.append(
                StalenessAssessment(
                    sourceId=bundle.c3_states[0].engine.name,
                    dataType="scientific_simulation_states",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="active_simulation_run",
                    warning=None,
                )
            )
        else:
            assessments.append(
                StalenessAssessment(
                    sourceId="scientific-orchestrator",
                    dataType="scientific_simulation_states",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="no_active_simulation",
                    warning="Biophysical crop simulation states have not been executed for this plot.",
                )
            )

        return assessments


def safe_measurement_val(measurement: Measurement | None) -> float | None:
    """Safely extracts value from Measurement, guaranteeing None is returned for missing or unavailable."""
    if measurement is None:
        return None
    if measurement.availability.status != DataStatus.AVAILABLE:
        return None
    return measurement.value


def format_measurement_str(
    measurement: Measurement | None,
    unit_override: str | None = None,
    decimal_places: int = 1,
    unavailable_text: str = "Not available",
) -> str:
    """Formats measurement preserving missingness — NEVER converting None or MISSING into 0."""
    val = safe_measurement_val(measurement)
    if val is None:
        return unavailable_text
    unit = unit_override or (measurement.unit if measurement else "")
    formatted_num = f"{val:.{decimal_places}f}".rstrip("0").rstrip(".") if decimal_places > 0 else f"{val:.0f}"
    return f"{formatted_num} {unit}".strip()
