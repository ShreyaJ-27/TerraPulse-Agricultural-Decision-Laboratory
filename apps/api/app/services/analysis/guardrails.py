from __future__ import annotations

from app.services.analysis.models import (
    EscalationNotice,
    EvidenceBundle,
    GuardrailStatus,
    ScientificLimitation,
)

DISEASE_KEYWORDS = {
    # English
    "disease", "pest", "pathogen", "fungus", "fungal", "rot", "blight", "infection",
    "wilt", "leaf spot", "leaf curl", "insect", "caterpillar", "aphid", "mildew",
    "virus", "rust", "smut", "borer", "infestation",
    # Hindi
    "रोग", "कीट", "फंगस", "फफूंद", "धब्बा", "सड़न", "झुलसा", "इल्ली", "कीड़ा", "बीमारी",
    # Kannada
    "ರೋಗ", "ಕೀಟ", "ಹುಳು", "ಬೂಜು", "ಸೊರಗು ರೋಗ", "ಎಲೆ ಚುಕ್ಕೆ", "ರೋಗ ಬಾಧೆ",
}

PRICING_KEYWORDS = {
    # English
    "price", "market price", "mandi", "rate", "quintal", "sell price", "selling price",
    "profit", "revenue", "cost", "trading", "commodity", "bhav",
    # Hindi
    "भाव", "दाम", "कीमत", "मंडी", "बिक्री", "क्विंटल", "मुनाफा", "बाजार",
    # Kannada
    "ಬೆಲೆ", "ದರ", "ಮಾರುಕಟ್ಟೆ", "ಮಾರಾಟ", "ಕ್ವಿಂಟಾಲ್ ಬೆಲೆ", "ಲಾಭ",
}

YIELD_KEYWORDS = {
    # English
    "yield", "production", "tonnes", "harvest quantity", "output", "bushels", "quintals per acre",
    # Hindi
    "उपज", "पैदावार", "उत्पादन",
    # Kannada
    "ಇಳುವರಿ", "ಉತ್ಪಾದನೆ",
}


class GuardrailEvaluator:
    """Evaluates user requests and evidence context against scientific limitations and domain boundaries."""

    @classmethod
    def evaluate(
        cls,
        question: str | None,
        bundle: EvidenceBundle,
    ) -> tuple[GuardrailStatus, list[ScientificLimitation], list[EscalationNotice]]:
        flags: list[str] = []
        restricted_topics: list[str] = []
        limitations: list[ScientificLimitation] = []
        escalations: list[EscalationNotice] = []
        escalation_required = False

        q_lower = (question or "").lower()

        # 1. Check Plant Pathology / Disease
        has_disease_query = any(k in q_lower for k in DISEASE_KEYWORDS)
        if has_disease_query:
            flags.append("RESTRICTED_QUERY_PLANT_PATHOLOGY")
            restricted_topics.append("plant_pathology")
            escalation_required = True
            escalations.append(
                EscalationNotice(
                    category="plant_pathology",
                    reason=(
                        "Plant disease and pest diagnosis cannot be determined from environmental sensors, "
                        "gridded soil data, or water balance simulations. In-field visual and laboratory "
                        "leaf/tissue examination is required."
                    ),
                    recommendedAction=(
                        "Take clear leaf/stem photos or bring fresh physical plant samples to the nearest "
                        "Krishi Vigyan Kendra (KVK) or contact your block agricultural extension officer."
                    ),
                    recommendedAuthority="Krishi Vigyan Kendra (KVK) / Block Agricultural Extension Office",
                )
            )

        # 2. Check Commodity Pricing / Market Speculation
        has_pricing_query = any(k in q_lower for k in PRICING_KEYWORDS)
        if has_pricing_query:
            flags.append("RESTRICTED_QUERY_COMMODITY_PRICING")
            restricted_topics.append("commodity_pricing")
            escalation_required = True
            escalations.append(
                EscalationNotice(
                    category="commodity_pricing",
                    reason=(
                        "Commodity market prices and mandi rates are volatile economic variables governed by "
                        "external supply-chain factors outside biophysical agro-ecological simulation."
                    ),
                    recommendedAction="Check current APMC mandi prices on the e-NAM portal or consult local APMC yard boards.",
                    recommendedAuthority="e-NAM Portal / Local Agricultural Produce Market Committee (APMC)",
                )
            )

        # 3. Model Engine Capabilities & Limitations
        crop_engine = bundle.crop_capability.selected_engine
        has_yield_query = any(k in q_lower for k in YIELD_KEYWORDS)

        if crop_engine == "FAO-56":
            limitations.append(
                ScientificLimitation(
                    category="crop_simulation",
                    code="FAO56_YIELD_UNSUPPORTED",
                    description=(
                        "The FAO-56 dual crop coefficient model evaluates daily soil-water balance, "
                        "evapotranspiration, and water stress; it does not model carbon assimilation, "
                        "biomass accumulation, or harvestable yield."
                    ),
                    implications=(
                        "Harvest yield forecasts are withheld. Water stress index (Ks) should be utilized "
                        "as the indicator for moisture deficit impact."
                    ),
                )
            )
            if has_yield_query:
                flags.append("UNSUPPORTED_YIELD_REQUEST_FAO56")
                restricted_topics.append("yield_forecasting")
        elif crop_engine == "identity/ecology-only":
            limitations.append(
                ScientificLimitation(
                    category="crop_simulation",
                    code="ECOLOGY_ONLY_NO_SIMULATION",
                    description=(
                        f"Crop '{bundle.crop_canonical_name}' has an ecological profile but lacks calibrated "
                        "crop coefficient parameters for dynamic daily water balance simulation."
                    ),
                    implications="Dynamic soil moisture and stress trajectories cannot be calculated.",
                )
            )
            if has_yield_query:
                flags.append("UNSUPPORTED_YIELD_REQUEST_ECOLOGY_ONLY")
                restricted_topics.append("yield_forecasting")

        # 4. Soil Modeling Gridded Prediction Baseline
        if bundle.c1_input is not None and bundle.c1_input.soil is not None:
            limitations.append(
                ScientificLimitation(
                    category="soil_modeling",
                    code="SOILGRIDS_GRIDDED_ESTIMATE",
                    description=(
                        "Soil physical parameters (field capacity, wilting point, bulk density) are derived from "
                        "ISRIC SoilGrids 250m machine-learning gridded spatial estimates, not direct in-situ sensor measurements."
                    ),
                    implications="Local micro-topography, recent tilling, organic mulching, or compaction layers may vary from model values.",
                )
            )

        # 5. Weather Horizon & NWP Uncertainty
        if bundle.c1_input is not None and bundle.c1_input.daily_weather:
            limitations.append(
                ScientificLimitation(
                    category="weather_forecast",
                    code="WEATHER_FORECAST_HORIZON",
                    description=(
                        "Numerical weather predictions exhibit increasing ensemble dispersion beyond 5 days. "
                        "Atmospheric inputs reflect Open-Meteo operational model runs."
                    ),
                    implications="Near-term irrigation decisions should prioritize 1-3 day forecast trends.",
                )
            )

        # 6. Check for missing critical inputs
        if bundle.missing_evidence:
            flags.append("INCOMPLETE_EVIDENCE_BUNDLE")

        passed = len(restricted_topics) == 0

        status = GuardrailStatus(
            passed=passed,
            flags=flags,
            restrictedTopics=restricted_topics,
            escalationRequired=escalation_required,
        )

        return status, limitations, escalations
