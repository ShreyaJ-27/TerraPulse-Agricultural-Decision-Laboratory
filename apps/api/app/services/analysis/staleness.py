from __future__ import annotations

from datetime import UTC, datetime

from app.contracts import DataStatus, Measurement
from app.services.analysis.models import (
    EvidenceBundle,
    StalenessAssessment,
)

FRESHNESS_MESSAGES = {
    "en": {
        "weather_historical": "Weather evidence describes a past simulation period; it is not a live forecast. Retrieved {age:.1f} hours ago for a {days}-day period.",
        "weather_stale": "Weather evidence was retrieved {age:.1f} hours ago; it may no longer represent current conditions.",
        "weather_missing": "Weather forecast data was not retrieved or is missing.",
        "soil_static": "Static gridded SoilGrids baseline; not a current in-situ measurement.",
        "soil_unavailable": "Soil properties are present in C1 but unavailable.",
        "soil_missing": "Soil data was not retrieved or is missing.",
        "snapshot": "This persisted snapshot is the input used by the selected run; it is not a refreshed live input.",
        "environmental_preparation": "Environmental evidence was prepared for this analysis; it is not a past run's input.",
        "simulation_completed": "This is a completed historical simulation, not a live or newly executed result.",
        "simulation_incomplete": "The selected simulation is {status}; no completed scientific result is available.",
        "simulation_missing": "No completed scientific simulation states are available for this plot and branch.",
        "states_historical": "Scientific states are historical simulation outputs; state dates are not observation times.",
        "comparison_historical": "Persisted comparison evidence is historical and reflects its recorded runs and inputs.",
    },
    "kn": {
        "weather_historical": "ಹವಾಮಾನ ಸಾಕ್ಷ್ಯವು ಹಿಂದಿನ ಸಿಮ್ಯುಲೇಶನ್ ಅವಧಿಗೆ ಸೇರಿದ್ದು; ಇದು ಪ್ರಸ್ತುತ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ. {days} ದಿನಗಳ ಅವಧಿಗೆ {age:.1f} ಗಂಟೆಗಳ ಹಿಂದೆ ಪಡೆಯಲಾಗಿದೆ.",
        "weather_stale": "ಹವಾಮಾನ ಸಾಕ್ಷ್ಯವನ್ನು {age:.1f} ಗಂಟೆಗಳ ಹಿಂದೆ ಪಡೆಯಲಾಗಿದೆ; ಅದು ಈಗಿನ ಪರಿಸ್ಥಿತಿಯನ್ನು ಪ್ರತಿನಿಧಿಸದೇ ಇರಬಹುದು.",
        "weather_missing": "ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ ಪಡೆಯಲಾಗಿಲ್ಲ ಅಥವಾ ಲಭ್ಯವಿಲ್ಲ.",
        "soil_static": "ಇದು ಸ್ಥಿರ SoilGrids ಗ್ರಿಡ್ ಆಧಾರಿತ ಅಂದಾಜು; ಇತ್ತೀಚಿನ ಸ್ಥಳೀಯ ಮಣ್ಣಿನ ಮಾಪನವಲ್ಲ.",
        "soil_unavailable": "C1 ದತ್ತಾಂಶದಲ್ಲಿ ಮಣ್ಣಿನ ಗುಣಲಕ್ಷಣಗಳಿವೆ, ಆದರೆ ಅವು ಲಭ್ಯವಿಲ್ಲ.",
        "soil_missing": "ಮಣ್ಣಿನ ದತ್ತಾಂಶ ಪಡೆಯಲಾಗಿಲ್ಲ ಅಥವಾ ಲಭ್ಯವಿಲ್ಲ.",
        "snapshot": "ಈ ಸಂಗ್ರಹಿತ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್ ಆಯ್ದ ರನ್‌ನ ಇನ್‌ಪುಟ್ ಆಗಿದೆ; ಇದು ಹೊಸ ಪ್ರಸ್ತುತ ಇನ್‌ಪುಟ್ ಅಲ್ಲ.",
        "environmental_preparation": "ಈ ವಿಶ್ಲೇಷಣೆಗಾಗಿ ಪರಿಸರ ಸಾಕ್ಷ್ಯವನ್ನು ಸಿದ್ಧಪಡಿಸಲಾಗಿದೆ; ಇದು ಹಿಂದಿನ ರನ್‌ನ ಇನ್‌ಪುಟ್ ಅಲ್ಲ.",
        "simulation_completed": "ಇದು ಪೂರ್ಣಗೊಂಡ ಹಿಂದಿನ ಸಿಮ್ಯುಲೇಶನ್ ಫಲಿತಾಂಶ; ಪ್ರಸ್ತುತ ಅಥವಾ ಹೊಸದಾಗಿ ನಡೆಸಿದ ಫಲಿತಾಂಶವಲ್ಲ.",
        "simulation_incomplete": "ಆಯ್ದ ಸಿಮ್ಯುಲೇಶನ್ ಪೂರ್ಣಗೊಂಡಿಲ್ಲ; ಪೂರ್ಣ ವೈಜ್ಞಾನಿಕ ಫಲಿತಾಂಶ ಲಭ್ಯವಿಲ್ಲ.",
        "simulation_missing": "ಈ ಪ್ಲಾಟ್ ಮತ್ತು ಶಾಖೆಗೆ ಪೂರ್ಣಗೊಂಡ ವೈಜ್ಞಾನಿಕ ಸಿಮ್ಯುಲೇಶನ್ ಸ್ಥಿತಿಗಳು ಲಭ್ಯವಿಲ್ಲ.",
        "states_historical": "ವೈಜ್ಞಾನಿಕ ಸ್ಥಿತಿಗಳು ಹಿಂದಿನ ಸಿಮ್ಯುಲೇಶನ್ ಫಲಿತಾಂಶಗಳು; ಸ್ಥಿತಿಯ ದಿನಾಂಕಗಳು ನೇರ ವೀಕ್ಷಣೆಯ ಸಮಯವಲ್ಲ.",
        "comparison_historical": "ಸಂಗ್ರಹಿತ ಹೋಲಿಕೆ ಅದರ ದಾಖಲಾದ ರನ್‌ಗಳು ಮತ್ತು ಇನ್‌ಪುಟ್‌ಗಳನ್ನು ಪ್ರತಿನಿಧಿಸುವ ಹಿಂದಿನ ಸಾಕ್ಷ್ಯವಾಗಿದೆ.",
    },
    "hi": {
        "weather_historical": "मौसम साक्ष्य पिछली सिमुलेशन अवधि का है; यह लाइव पूर्वानुमान नहीं है। {days} दिनों की अवधि के लिए इसे {age:.1f} घंटे पहले प्राप्त किया गया था।",
        "weather_stale": "मौसम साक्ष्य {age:.1f} घंटे पहले प्राप्त हुआ था; यह अब वर्तमान स्थितियों का प्रतिनिधित्व नहीं कर सकता।",
        "weather_missing": "मौसम पूर्वानुमान प्राप्त नहीं हुआ या उपलब्ध नहीं है।",
        "soil_static": "यह स्थिर ग्रिड-आधारित SoilGrids अनुमान है; वर्तमान खेत-मृदा माप नहीं।",
        "soil_unavailable": "C1 में मृदा गुण मौजूद हैं, लेकिन उपलब्ध नहीं हैं।",
        "soil_missing": "मृदा डेटा प्राप्त नहीं हुआ या उपलब्ध नहीं है।",
        "snapshot": "यह सहेजा गया स्नैपशॉट चुने गए रन का इनपुट है; यह नया लाइव इनपुट नहीं है।",
        "environmental_preparation": "इस विश्लेषण के लिए पर्यावरणीय साक्ष्य तैयार किया गया; यह पुराने रन का इनपुट नहीं है।",
        "simulation_completed": "यह पुराना पूर्ण सिमुलेशन परिणाम है, लाइव या अभी-अभी चलाया गया परिणाम नहीं।",
        "simulation_incomplete": "चुना गया सिमुलेशन पूर्ण नहीं है; पूर्ण वैज्ञानिक परिणाम उपलब्ध नहीं है।",
        "simulation_missing": "इस खेत और शाखा के लिए पूर्ण वैज्ञानिक सिमुलेशन स्थिति उपलब्ध नहीं है।",
        "states_historical": "वैज्ञानिक स्थिति पुराने सिमुलेशन परिणाम हैं; स्थिति की तारीखें अवलोकन का समय नहीं हैं।",
        "comparison_historical": "सहेजी गई तुलना उसके दर्ज रन और इनपुट दर्शाने वाला पुराना साक्ष्य है।",
    },
}


class StalenessEvaluator:
    """Evaluates data freshness and enforces strict scientific missingness preservation."""

    WEATHER_STALENESS_HOURS = 24.0

    @classmethod
    def evaluate(
        cls,
        bundle: EvidenceBundle,
        now: datetime | None = None,
        language: str = "en",
    ) -> list[StalenessAssessment]:
        current_time = now or datetime.now(UTC)
        messages = FRESHNESS_MESSAGES.get(language, FRESHNESS_MESSAGES["en"])
        assessments: list[StalenessAssessment] = []
        environmental = bundle.environmental_metadata
        simulation = bundle.simulation_metadata or {}
        comparison = bundle.comparison_metadata or {}

        def as_datetime(value: object) -> datetime | None:
            if isinstance(value, datetime):
                result = value
            elif isinstance(value, str):
                try:
                    result = datetime.fromisoformat(value)
                except ValueError:
                    return None
            else:
                return None
            return result.replace(tzinfo=UTC) if result.tzinfo is None else result

        def _age_hours(value: object) -> float | None:
            timestamp = as_datetime(value)
            if timestamp is None:
                return None
            return max(0.0, (current_time - timestamp).total_seconds() / 3600.0)

        # 1. Weather Data Freshness
        if bundle.c1_input is not None and bundle.c1_input.daily_weather:
            # Check C1 retrieved_at timestamp
            retrieved_at = bundle.c1_input.retrieved_at
            if retrieved_at.tzinfo is None:
                retrieved_at = retrieved_at.replace(tzinfo=UTC)

            weather_age_hours = max(0.0, (current_time - retrieved_at).total_seconds() / 3600.0)
            period_end = bundle.c1_input.simulation_period.end_date
            is_historical_period = period_end < current_time.date()
            is_stale = weather_age_hours > cls.WEATHER_STALENESS_HOURS
            if is_historical_period:
                freshness_label = "historical"
                warning = (
                    messages["weather_historical"].format(
                        age=weather_age_hours,
                        days=(period_end - bundle.c1_input.simulation_period.start_date).days + 1,
                    )
                )
            else:
                freshness_label = "stale" if is_stale else "fresh"
                warning = (
                    messages["weather_stale"].format(age=weather_age_hours)
                    if is_stale
                    else None
                )

            assessments.append(
                StalenessAssessment(
                    sourceId="open-meteo",
                    dataType="daily_weather_forecast",
                    isStale=is_stale,
                    ageHours=round(weather_age_hours, 1),
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
                    freshnessLabel="missing",
                    warning=messages["weather_missing"],
                )
            )

        # 2. Soil Data (Static Gridded Baseline)
        if bundle.c1_input is not None and bundle.c1_input.soil is not None:
            soil_available = any(
                safe_measurement_val(value) is not None
                for value in (
                    bundle.c1_input.soil.depth_cm,
                    bundle.c1_input.soil.field_capacity,
                    bundle.c1_input.soil.wilting_point,
                    bundle.c1_input.soil.bulk_density,
                )
            )
            assessments.append(
                StalenessAssessment(
                    sourceId="soilgrids-250m",
                    dataType="soil_properties",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="static_modelled_baseline" if soil_available else "unavailable",
                    warning=(
                        messages["soil_static"]
                        if soil_available
                        else messages["soil_unavailable"]
                    ),
                )
            )
        else:
            assessments.append(
                StalenessAssessment(
                    sourceId="soilgrids-250m",
                    dataType="soil_properties",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="missing",
                    warning=messages["soil_missing"],
                )
            )

        snapshot_age = _age_hours(environmental.get("snapshotCreatedAt"))
        if environmental.get("snapshotId") is not None:
            snapshot_stale = snapshot_age is not None and snapshot_age > cls.WEATHER_STALENESS_HOURS
            assessments.append(
                StalenessAssessment(
                    sourceId=str(environmental.get("snapshotId")),
                    dataType="environmental_snapshot",
                    isStale=snapshot_stale,
                    ageHours=round(snapshot_age, 1) if snapshot_age is not None else None,
                    freshnessLabel="stale" if snapshot_stale else "historical",
                    warning=messages["snapshot"],
                )
            )
        elif environmental.get("source") == "new_or_cached_environmental_preparation":
            assessments.append(
                StalenessAssessment(
                    sourceId="environmental-input-service",
                    dataType="environmental_input",
                    isStale=False,
                    ageHours=_age_hours(environmental.get("retrievedAt")),
                    freshnessLabel="new_or_cached",
                    warning=messages["environmental_preparation"],
                )
            )

        if simulation:
            completed_age = _age_hours(simulation.get("completedAt"))
            assessments.append(
                StalenessAssessment(
                    sourceId=str(simulation.get("simulationRunId")),
                    dataType="scientific_simulation_run",
                    isStale=False,
                    ageHours=round(completed_age, 1) if completed_age is not None else None,
                    freshnessLabel="historical",
                    warning=(
                        messages["simulation_completed"]
                        if simulation.get("status") == "completed"
                        else messages["simulation_incomplete"].format(
                            status=simulation.get("status")
                        )
                    ),
                )
            )
        elif not bundle.c3_states:
            assessments.append(
                StalenessAssessment(
                    sourceId="scientific-orchestrator",
                    dataType="scientific_simulation_states",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="missing",
                    warning=messages["simulation_missing"],
                )
            )
        elif bundle.c3_states:
            assessments.append(
                StalenessAssessment(
                    sourceId=bundle.c3_states[-1].engine.name,
                    dataType="scientific_simulation_states",
                    isStale=False,
                    ageHours=None,
                    freshnessLabel="historical",
                    warning=messages["states_historical"],
                )
            )

        if comparison:
            created_age = _age_hours(comparison.get("createdAt"))
            assessments.append(
                StalenessAssessment(
                    sourceId=str(comparison.get("comparisonId")),
                    dataType="simulation_comparison",
                    isStale=False,
                    ageHours=round(created_age, 1) if created_age is not None else None,
                    freshnessLabel="historical",
                    warning=messages["comparison_historical"],
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
