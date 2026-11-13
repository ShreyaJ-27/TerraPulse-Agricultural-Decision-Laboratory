from __future__ import annotations

import unicodedata

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
    "virus", "rust", "smut", "borer", "infestation", "brown spots", "yellow leaves",
    # Hindi
    "रोग", "कीट", "फंगस", "फफूंद", "धब्बा", "सड़न", "झुलसा", "इल्ली", "कीड़ा", "बीमारी",
    # Kannada
    "ರೋಗ", "ಕೀಟ", "ಹುಳು", "ಬೂಜು", "ಸೊರಗು ರೋಗ", "ಎಲೆ ಚುಕ್ಕೆ", "ರೋಗ ಬಾಧೆ",
    "ಹಳದಿ ಎಲೆ", "ಕಂದು ಚುಕ್ಕೆ",
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
    "उपज", "पैदावार", "उत्पादन", "फसल की मात्रा",
    # Kannada
    "ಇಳುವರಿ", "ಉತ್ಪಾದನೆ",
}


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    current: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category[0] in {"L", "M", "N"}:
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _contains_topic(text_tokens: list[str], phrases: set[str]) -> bool:
    for phrase in phrases:
        phrase_tokens = _tokens(phrase)
        width = len(phrase_tokens)
        if not width:
            continue
        for start in range(len(text_tokens) - width + 1):
            candidate = text_tokens[start : start + width]
            if all(word.startswith(prefix) for word, prefix in zip(candidate, phrase_tokens)):
                return True
    return False


def _localized_limitation(
    language: str,
    category: str,
    code: str,
    description: str,
    implications: str,
    crop_name: str | None = None,
) -> ScientificLimitation:
    localized = {
        "kn": {
            "FAO56_YIELD_UNSUPPORTED": (
                "FAO-56 ದೈನಂದಿನ ಮಣ್ಣಿನ-ನೀರಿನ ಸಮತೋಲನ, ಬಾಷ್ಪೀಕರಣ ಮತ್ತು ನೀರಿನ ಒತ್ತಡವನ್ನು ಲೆಕ್ಕಹಾಕುತ್ತದೆ; "
                + "ಇದು ಜೈವಭಾರ ಅಥವಾ ಕೊಯ್ಲಿನ ಇಳುವರಿಯನ್ನು ಲೆಕ್ಕಿಸುವುದಿಲ್ಲ.",
                "ಇಳುವರಿ ಮುನ್ಸೂಚನೆಯನ್ನು ನೀಡಲಾಗುವುದಿಲ್ಲ. ತೇವಾಂಶ ಕೊರತೆಯ ಸೂಚಕವಾಗಿ ನೀರಿನ ಒತ್ತಡವನ್ನು ಬಳಸಿ.",
            ),
            "ECOLOGY_ONLY_NO_SIMULATION": (
                f"'{crop_name}' ಬೆಳೆಗೆ ಪರಿಸರ ಗುರುತು ಇದೆ, ಆದರೆ ದೈನಂದಿನ ನೀರಿನ ಸಮತೋಲನಕ್ಕೆ ಮಾಪನಾಂಕಿತ "
                + "ಬೆಳೆ ಗುಣಾಂಕಗಳಿಲ್ಲ.",
                "ಚಲನೆಯಲ್ಲಿರುವ ಮಣ್ಣಿನ ತೇವಾಂಶ ಮತ್ತು ಒತ್ತಡದ ಪಥಗಳನ್ನು ಲೆಕ್ಕಿಸಲಾಗುವುದಿಲ್ಲ.",
            ),
            "SOILGRIDS_GRIDDED_ESTIMATE": (
                "ಮಣ್ಣಿನ ಗುಣಲಕ್ಷಣಗಳು ISRIC SoilGrids 250m ಗ್ರಿಡ್ ಅಂದಾಜುಗಳಿಂದ ಬಂದಿವೆ; ಸ್ಥಳದಲ್ಲಿನ "
                + "ಸಂವೇದಕ ಮಾಪನಗಳಲ್ಲ.",
                "ಸ್ಥಳೀಯ ಭೂಸ್ವರೂಪ, ಇತ್ತೀಚಿನ ಉಳುಮೆ, ಸಾವಯವ ಹೊದಿಕೆ ಅಥವಾ ಮಣ್ಣಿನ ಗಟ್ಟಿತನವು ಅಂದಾಜಿನಿಂದ ಭಿನ್ನವಾಗಿರಬಹುದು.",
            ),
            "WEATHER_FORECAST_HORIZON": (
                "ಸಂಖ್ಯಾತ್ಮಕ ಹವಾಮಾನ ಮುನ್ಸೂಚನೆಯಲ್ಲಿ 5 ದಿನಗಳ ನಂತರ ಅನಿಶ್ಚಿತತೆ ಹೆಚ್ಚಬಹುದು.",
                "ನೀರಾವರಿ ನಿರ್ಧಾರಗಳಿಗೆ ಸಮೀಪದ 1–3 ದಿನಗಳ ಮುನ್ಸೂಚನೆಗೆ ಆದ್ಯತೆ ನೀಡಿ.",
            ),
        },
        "hi": {
            "FAO56_YIELD_UNSUPPORTED": (
                "FAO-56 दैनिक मृदा-जल संतुलन, वाष्पोत्सर्जन और जल तनाव की गणना करता है; यह जैवभार "
                + "या कटाई उपज की गणना नहीं करता।",
                "उपज का पूर्वानुमान नहीं दिया जाता। नमी की कमी के संकेतक के रूप में जल तनाव का उपयोग करें।",
            ),
            "ECOLOGY_ONLY_NO_SIMULATION": (
                f"'{crop_name}' की पारिस्थितिक पहचान है, लेकिन दैनिक जल संतुलन के लिए कैलिब्रेटेड "
                + "फसल गुणांक उपलब्ध नहीं हैं।",
                "गतिशील मृदा नमी और तनाव पथों की गणना नहीं की जा सकती।",
            ),
            "SOILGRIDS_GRIDDED_ESTIMATE": (
                "मृदा गुण ISRIC SoilGrids 250m ग्रिड अनुमान हैं; खेत में किए गए सेंसर माप नहीं।",
                "स्थानीय भू-आकृति, जुताई, जैविक मल्च या सघनता इन अनुमानों से अलग हो सकती है।",
            ),
            "WEATHER_FORECAST_HORIZON": (
                "संख्यात्मक मौसम पूर्वानुमान में 5 दिनों के बाद अनिश्चितता बढ़ सकती है।",
                "सिंचाई निर्णयों में अगले 1–3 दिनों के पूर्वानुमान को प्राथमिकता दें।",
            ),
        },
    }
    description, implications = localized.get(language, {}).get(
        code, (description, implications)
    )
    return ScientificLimitation(
        category=category,
        code=code,
        description=description,
        implications=implications,
    )


class GuardrailEvaluator:
    """Evaluates user requests and evidence context against scientific limitations and domain boundaries."""

    @classmethod
    def evaluate(
        cls,
        question: str | None,
        bundle: EvidenceBundle,
        language: str = "en",
    ) -> tuple[GuardrailStatus, list[ScientificLimitation], list[EscalationNotice]]:
        flags: list[str] = []
        restricted_topics: list[str] = []
        limitations: list[ScientificLimitation] = []
        escalations: list[EscalationNotice] = []
        escalation_required = False

        question_tokens = _tokens(question or "")

        # 1. Check Plant Pathology / Disease
        has_disease_query = _contains_topic(question_tokens, DISEASE_KEYWORDS)
        if has_disease_query:
            flags.append("RESTRICTED_QUERY_PLANT_PATHOLOGY")
            restricted_topics.append("plant_pathology")
            escalation_required = True
            disease_messages = {
                "kn": (
                    "ಪರಿಸರ ಅಥವಾ ಜಲ-ಸಮತೋಲನ ಮಾದರಿಗಳಿಂದ ಸಸ್ಯ ರೋಗ ಅಥವಾ ಕೀಟವನ್ನು ಪತ್ತೆಹಚ್ಚಲಾಗುವುದಿಲ್ಲ; "
                    + "ಸ್ಥಳದಲ್ಲಿನ ಪರಿಶೀಲನೆ ಅಗತ್ಯ.",
                    "ಸಸ್ಯದ ಮಾದರಿಯನ್ನು ಹತ್ತಿರದ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ (KVK) ಅಥವಾ ಕೃಷಿ ವಿಸ್ತರಣಾಧಿಕಾರಿಗೆ ತೋರಿಸಿ.",
                ),
                "hi": (
                    "पर्यावरण या जल-संतुलन मॉडल से पौधों के रोग या कीट का निदान नहीं किया जा सकता; "
                    + "खेत में जांच आवश्यक है।",
                    "पौधे का नमूना नजदीकी कृषि विज्ञान केंद्र (KVK) या कृषि विस्तार अधिकारी को दिखाएं।",
                ),
            }
            reason, action = disease_messages.get(
                language,
                (
                    "Plant disease and pest diagnosis cannot be determined from environmental or water-balance models; in-field examination is required.",
                    "Bring a plant sample to the nearest Krishi Vigyan Kendra (KVK) or agricultural extension officer.",
                ),
            )
            escalations.append(EscalationNotice(
                category="plant_pathology",
                reason=reason,
                recommendedAction=action,
                recommendedAuthority="Krishi Vigyan Kendra (KVK) / Block Agricultural Extension Office",
            ))

        # 2. Check Commodity Pricing / Market Speculation
        has_pricing_query = _contains_topic(question_tokens, PRICING_KEYWORDS)
        if has_pricing_query:
            flags.append("RESTRICTED_QUERY_COMMODITY_PRICING")
            restricted_topics.append("commodity_pricing")
            escalation_required = True
            pricing_messages = {
                "kn": (
                    "ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು ಬದಲಾಗುತ್ತವೆ ಮತ್ತು ಜೈವಿಕ-ಭೌತಿಕ ಮಾದರಿಯ ವ್ಯಾಪ್ತಿಗೆ ಸೇರಿಲ್ಲ.",
                    "ಪ್ರಸ್ತುತ ಬೆಲೆಗೆ e-NAM ಅಥವಾ ಸ್ಥಳೀಯ APMC ಮಾರುಕಟ್ಟೆಯನ್ನು ಪರಿಶೀಲಿಸಿ.",
                ),
                "hi": (
                    "बाजार भाव बदलते रहते हैं और जैव-भौतिक मॉडल के दायरे में नहीं आते।",
                    "वर्तमान भाव के लिए e-NAM या स्थानीय APMC मंडी देखें।",
                ),
            }
            reason, action = pricing_messages.get(
                language,
                (
                    "Market prices change and are outside the scope of biophysical simulation.",
                    "Check current prices through e-NAM or the local APMC market.",
                ),
            )
            escalations.append(EscalationNotice(
                category="commodity_pricing",
                reason=reason,
                recommendedAction=action,
                recommendedAuthority="e-NAM Portal / Local Agricultural Produce Market Committee (APMC)",
            ))

        # 3. Model Engine Capabilities & Limitations
        crop_engine = bundle.crop_capability.selected_engine
        has_yield_query = _contains_topic(question_tokens, YIELD_KEYWORDS)

        if crop_engine == "FAO-56":
            limitations.append(
                _localized_limitation(
                    language=language,
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
                _localized_limitation(
                    language=language,
                    category="crop_simulation",
                    code="ECOLOGY_ONLY_NO_SIMULATION",
                    description=(
                        f"Crop '{bundle.crop_canonical_name}' has an ecological profile but lacks calibrated "
                        "crop coefficient parameters for dynamic daily water balance simulation."
                    ),
                    implications="Dynamic soil moisture and stress trajectories cannot be calculated.",
                    crop_name=bundle.crop_canonical_name,
                )
            )
            if has_yield_query:
                flags.append("UNSUPPORTED_YIELD_REQUEST_ECOLOGY_ONLY")
                restricted_topics.append("yield_forecasting")

        # 4. Soil Modeling Gridded Prediction Baseline
        if bundle.c1_input is not None and bundle.c1_input.soil is not None:
            limitations.append(
                _localized_limitation(
                    language=language,
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
                _localized_limitation(
                    language=language,
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
