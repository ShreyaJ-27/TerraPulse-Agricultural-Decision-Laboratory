from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.crop_lens.registry import CROP_REGISTRY, CropRecord
from app.services.crop_lens.resolver import (
    CandidateMatch,
    CropLensResolver,
    ResolutionResult,
    ResolutionStatus,
    _normalize,
)

LocaleType = Literal["en", "kn", "hi"]

SUPPORTED_OUTPUT_LABELS: dict[str, dict[LocaleType, str]] = {
    "actualEvapotranspiration": {
        "en": "actual evapotranspiration",
        "kn": "ವಾಸ್ತವಿಕ ವಾಷ್ಪೋತ್ಸರ್ಜನೆ (ETa)",
        "hi": "वास्तविक वाष्पोत्सर्जन (ETa)",
    },
    "waterStress": {"en": "water stress", "kn": "ನೀರಿನ ಒತ್ತಡ", "hi": "जल तनाव"},
    "irrigation": {"en": "irrigation", "kn": "ನೀರಾವರಿ", "hi": "सिंचाई"},
    "canopyCover": {"en": "canopy cover", "kn": "ಕ್ಯಾನೋಪಿ ಆವರಣ", "hi": "कैनोपी आवरण"},
    "biomass": {"en": "biomass", "kn": "ಜೈವಿಕ ರಾಶಿ", "hi": "जैवभार"},
    "yield": {"en": "yield", "kn": "ಇಳುವರಿ", "hi": "उपज"},
}
IDENTITY_ONLY_LABELS: dict[LocaleType, str] = {
    "en": "Identity and taxonomy only",
    "kn": "ಗುರುತು ಮತ್ತು ವರ್ಗೀಕರಣ ಮಾತ್ರ",
    "hi": "केवल पहचान और वर्गीकरण",
}
WHEAT_EXAMPLE_LABELS: dict[LocaleType, str] = {
    "en": "Wheat is available as the bundled Tunis AquaCrop example. Farm-scale simulation outputs are unavailable.",
    "kn": "ಗೋಧಿಗೆ ಟುನಿಸ್ AquaCrop ಉದಾಹರಣೆ ಲಭ್ಯವಿದೆ. ಜಮೀನಿನ ಮಟ್ಟದ ಸಿಮ್ಯುಲೇಶನ್ ಫಲಿತಾಂಶಗಳು ಲಭ್ಯವಿಲ್ಲ.",
    "hi": "गेहूँ के लिए AquaCrop का ट्यूनिस उदाहरण उपलब्ध है। खेत-स्तरीय सिमुलेशन के परिणाम उपलब्ध नहीं हैं।",
}
CROP_DISPLAY_NAMES: dict[str, dict[LocaleType, str]] = {
    "Turmeric": {"en": "Turmeric", "kn": "ಅರಿಶಿನ", "hi": "हल्दी"},
    "Maize": {"en": "Maize", "kn": "ಮೆಕ್ಕೆಜೋಳ", "hi": "मक्का"},
    "Wheat": {"en": "Wheat", "kn": "ಗೋಧಿ", "hi": "गेहूँ"},
    "Pearl Millet": {"en": "Pearl Millet", "kn": "ಸಜ್ಜೆ", "hi": "बाजरा"},
    "Finger Millet": {"en": "Finger Millet", "kn": "ರಾಗಿ", "hi": "रागी"},
    "Foxtail Millet": {"en": "Foxtail Millet", "kn": "ನವಣೆ", "hi": "कंगनी"},
    "Chickpea (Bengal Gram)": {"en": "Chickpea", "kn": "ಕಡಲೆ", "hi": "चना"},
    "Black Gram (Urad)": {"en": "Black Gram", "kn": "ಉದ್ದು", "hi": "उड़द"},
    "Upland Cotton": {"en": "Cotton", "kn": "ಹತ್ತಿ", "hi": "कपास"},
    "Okra": {"en": "Okra", "kn": "ಬೆಂಡೆಕಾಯಿ", "hi": "भिंडी"},
}
LIMITATION_TRANSLATIONS: dict[str, dict[LocaleType, str]] = {
    "Empty query.": {
        "en": "Empty query.",
        "kn": "ಪ್ರಶ್ನೆ ಖಾಲಿಯಾಗಿದೆ.",
        "hi": "प्रश्न खाली है।",
    },
    "No yield output": {
        "en": "No yield output",
        "kn": "ಇಳುವರಿ ಫಲಿತಾಂಶ ಲಭ್ಯವಿಲ್ಲ.",
        "hi": "उपज परिणाम उपलब्ध नहीं है।",
    },
    "No calibrated dry-matter yield or protein estimation.": {
        "en": "No calibrated dry-matter yield or protein estimation.",
        "kn": "ಮಾಪನಾಂಕಿತ ಒಣಪದಾರ್ಥ ಇಳುವರಿ ಅಥವಾ ಪ್ರೋಟೀನ್ ಅಂದಾಜು ಲಭ್ಯವಿಲ್ಲ.",
        "hi": "कैलिब्रेटेड शुष्क-पदार्थ उपज या प्रोटीन का अनुमान उपलब्ध नहीं है।",
    },
    "Water balance only.": {
        "en": "Water balance only.",
        "kn": "ನೀರಿನ ಸಮತೋಲನ ಮಾತ್ರ.",
        "hi": "केवल जल संतुलन।",
    },
    "Crop identity is supported, but no quantitative AquaCrop or FAO-56 calibration is available.": {
        "en": "Crop identity is supported, but no quantitative AquaCrop or FAO-56 calibration is available.",
        "kn": "ಬೆಳೆ ಗುರುತು ಲಭ್ಯವಿದೆ; ಆದರೆ ಪ್ರಮಾಣಾತ್ಮಕ AquaCrop ಅಥವಾ FAO-56 ಮಾಪನಾಂಕ ಲಭ್ಯವಿಲ್ಲ.",
        "hi": "फसल की पहचान उपलब्ध है, लेकिन मात्रात्मक AquaCrop या FAO-56 कैलिब्रेशन उपलब्ध नहीं है।",
    },
    "Scientific simulation must not be inferred from this identity-only record.": {
        "en": "Scientific simulation must not be inferred from this identity-only record.",
        "kn": "ಈ ಗುರುತು-ಮಾತ್ರ ದಾಖಲೆಯಿಂದ ವೈಜ್ಞಾನಿಕ ಸಿಮ್ಯುಲೇಶನ್ ಇದೆ ಎಂದು ಊಹಿಸಬಾರದು.",
        "hi": "इस पहचान-मात्र रिकॉर्ड से वैज्ञानिक सिमुलेशन का अनुमान नहीं लगाना चाहिए।",
    },
    "Root-zone water depletion only; yield estimation not supported.": {
        "en": "Root-zone water depletion only; yield estimation not supported.",
        "kn": "ಬೇರಿನ ವಲಯದ ನೀರಿನ ಕೊರತೆ ಮಾತ್ರ; ಇಳುವರಿ ಅಂದಾಜು ಬೆಂಬಲಿತವಲ್ಲ.",
        "hi": "केवल जड़-क्षेत्र की जल कमी; उपज का अनुमान समर्थित नहीं है।",
    },
    "Yield output is not supported.": {
        "en": "Yield output is not supported.",
        "kn": "ಇಳುವರಿ ಫಲಿತಾಂಶ ಬೆಂಬಲಿತವಲ್ಲ.",
        "hi": "उपज परिणाम समर्थित नहीं है।",
    },
    "No quantitative AquaCrop or FAO-56 simulation calibrated.": {
        "en": "No quantitative AquaCrop or FAO-56 simulation calibrated.",
        "kn": "ಪ್ರಮಾಣಾತ್ಮಕ AquaCrop ಅಥವಾ FAO-56 ಸಿಮ್ಯುಲೇಶನ್‌ಗೆ ಮಾಪನಾಂಕ ಮಾಡಿಲ್ಲ.",
        "hi": "मात्रात्मक AquaCrop या FAO-56 सिमुलेशन कैलिब्रेट नहीं है।",
    },
    "No yield or pod development prediction.": {
        "en": "No yield or pod development prediction.",
        "kn": "ಇಳುವರಿ ಅಥವಾ ಕಾಯಿ ಬೆಳವಣಿಗೆಯ ಮುನ್ಸೂಚನೆ ಲಭ್ಯವಿಲ್ಲ.",
        "hi": "उपज या फली-विकास का पूर्वानुमान उपलब्ध नहीं है।",
    },
    "Simulation model not currently calibrated.": {
        "en": "Simulation model not currently calibrated.",
        "kn": "ಸಿಮ್ಯುಲೇಶನ್ ಮಾದರಿಗೆ ಪ್ರಸ್ತುತ ಮಾಪನಾಂಕ ಮಾಡಿಲ್ಲ.",
        "hi": "सिमुलेशन मॉडल का फिलहाल कैलिब्रेशन नहीं है।",
    },
    "Crop not calibrated for quantitative AquaCrop or FAO-56 simulation.": {
        "en": "Crop not calibrated for quantitative AquaCrop or FAO-56 simulation.",
        "kn": "ಈ ಬೆಳೆಗೆ ಪ್ರಮಾಣಾತ್ಮಕ AquaCrop ಅಥವಾ FAO-56 ಸಿಮ್ಯುಲೇಶನ್ ಮಾಪನಾಂಕ ಮಾಡಿಲ್ಲ.",
        "hi": "इस फसल के लिए मात्रात्मक AquaCrop या FAO-56 सिमुलेशन कैलिब्रेट नहीं है।",
    },
    "Identity and taxonomic references only. Fabricated yield/growth output is strictly prohibited.": {
        "en": "Identity and taxonomic references only. Fabricated yield/growth output is strictly prohibited.",
        "kn": "ಗುರುತು ಮತ್ತು ವರ್ಗೀಕರಣ ಉಲ್ಲೇಖಗಳು ಮಾತ್ರ ಲಭ್ಯ. ಕಲ್ಪಿತ ಇಳುವರಿ ಅಥವಾ ಬೆಳವಣಿಗೆಯ ಫಲಿತಾಂಶವನ್ನು ನೀಡಬಾರದು.",
        "hi": "केवल पहचान और वर्गीकरण संदर्भ उपलब्ध हैं। मनगढ़ंत उपज या वृद्धि परिणाम सख्त वर्जित हैं।",
    },
    "Requires verified planting date and irrigation schedule.": {
        "en": "Requires verified planting date and irrigation schedule.",
        "kn": "ಪರಿಶೀಲಿಸಿದ ಬಿತ್ತನೆ ದಿನಾಂಕ ಮತ್ತು ನೀರಾವರಿ ವೇಳಾಪಟ್ಟಿ ಅಗತ್ಯ.",
        "hi": "सत्यापित बुवाई तिथि और सिंचाई अनुसूची आवश्यक है।",
    },
    "Valid only under pest-free baseline assumption.": {
        "en": "Valid only under pest-free baseline assumption.",
        "kn": "ಕೀಟರಹಿತ ಮೂಲ ಊಹೆಯಲ್ಲಷ್ಟೇ ಅನ್ವಯಿಸುತ್ತದೆ.",
        "hi": "केवल कीट-मुक्त आधारभूत मान्यता के अंतर्गत मान्य है।",
    },
    "Plant pathology and chemical/pest diagnosis are outside TerraPulse's biophysical scope.": {
        "en": "Plant pathology and chemical/pest diagnosis are outside TerraPulse's biophysical scope.",
        "kn": "ಸಸ್ಯ ರೋಗಶಾಸ್ತ್ರ ಮತ್ತು ರಾಸಾಯನಿಕ ಅಥವಾ ಕೀಟ ರೋಗನಿರ್ಣಯ TerraPulse‌ನ ಜೈವಭೌತಿಕ ವ್ಯಾಪ್ತಿಗೆ ಸೇರಿಲ್ಲ.",
        "hi": "पादप रोग विज्ञान तथा रसायन या कीट निदान TerraPulse के जैव-भौतिक दायरे से बाहर हैं।",
    },
    "Market pricing, commodity forecasting, and financial speculation are strictly excluded from TerraPulse.": {
        "en": "Market pricing, commodity forecasting, and financial speculation are strictly excluded from TerraPulse.",
        "kn": "ಮಾರುಕಟ್ಟೆ ಬೆಲೆ, ಸರಕು ಬೆಲೆ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಹಣಕಾಸು ಊಹಾಪೋಹಗಳು TerraPulse ವ್ಯಾಪ್ತಿಗೆ ಸೇರಿಲ್ಲ.",
        "hi": "बाजार भाव, कमोडिटी पूर्वानुमान और वित्तीय अटकलें TerraPulse के दायरे से बाहर हैं।",
    },
    "Yield simulation depends on engine capability: AquaCrop supports yield; FAO-56 does not.": {
        "en": "Yield simulation depends on engine capability: AquaCrop supports yield; FAO-56 does not.",
        "kn": "ಇಳುವರಿ ಸಿಮ್ಯುಲೇಶನ್ ಎಂಜಿನ್ ಸಾಮರ್ಥ್ಯವನ್ನು ಅವಲಂಬಿಸಿದೆ: AquaCrop ಬೆಂಬಲಿಸುತ್ತದೆ; FAO-56 ಬೆಂಬಲಿಸುವುದಿಲ್ಲ.",
        "hi": "उपज सिमुलेशन इंजन की क्षमता पर निर्भर है: AquaCrop समर्थित है, FAO-56 नहीं।",
    },
    "Assumes pest-free baseline.": {
        "en": "Assumes pest-free baseline.",
        "kn": "ಕೀಟರಹಿತ ಮೂಲ ಸ್ಥಿತಿಯನ್ನು ಊಹಿಸುತ್ತದೆ.",
        "hi": "कीट-मुक्त आधारभूत स्थिति मानता है।",
    },
    "No quantitative simulation calibrated for this crop.": {
        "en": "No quantitative simulation calibrated for this crop.",
        "kn": "ಈ ಬೆಳೆಗೆ ಪ್ರಮಾಣಾತ್ಮಕ ಸಿಮ್ಯುಲೇಶನ್ ಮಾಪನಾಂಕ ಮಾಡಿಲ್ಲ.",
        "hi": "इस फसल के लिए मात्रात्मक सिमुलेशन कैलिब्रेट नहीं है।",
    },
    "Identity and taxonomy reference only.": {
        "en": "Identity and taxonomy reference only.",
        "kn": "ಗುರುತು ಮತ್ತು ವರ್ಗೀಕರಣ ಉಲ್ಲೇಖ ಮಾತ್ರ.",
        "hi": "केवल पहचान और वर्गीकरण संदर्भ।",
    },
    "Quantitative water calculation requires plot location, weather data, and soil profile.": {
        "en": "Quantitative water calculation requires plot location, weather data, and soil profile.",
        "kn": "ಪ್ರಮಾಣಾತ್ಮಕ ನೀರಿನ ಲೆಕ್ಕಾಚಾರಕ್ಕೆ ಜಮೀನಿನ ಸ್ಥಳ, ಹವಾಮಾನ ಡೇಟಾ ಮತ್ತು ಮಣ್ಣಿನ ಪ್ರೊಫೈಲ್ ಅಗತ್ಯ.",
        "hi": "मात्रात्मक जल गणना के लिए खेत का स्थान, मौसम डेटा और मिट्टी की प्रोफ़ाइल आवश्यक है।",
    },
    "Standard Kc values require adjustment for local climate humidity and wind conditions.": {
        "en": "Standard Kc values require adjustment for local climate humidity and wind conditions.",
        "kn": "ಪ್ರಮಾಣಿತ Kc ಮೌಲ್ಯಗಳನ್ನು ಸ್ಥಳೀಯ ಆರ್ದ್ರತೆ ಮತ್ತು ಗಾಳಿಯ ಸ್ಥಿತಿಗೆ ಹೊಂದಿಸಬೇಕು.",
        "hi": "मानक Kc मानों को स्थानीय आर्द्रता और हवा की स्थिति के अनुसार समायोजित करना होगा।",
    },
    "Dynamic water balance requires verified planting date and weather realization.": {
        "en": "Dynamic water balance requires verified planting date and weather realization.",
        "kn": "ಚಲನೆಯಲ್ಲಿರುವ ನೀರಿನ ಸಮತೋಲನಕ್ಕೆ ಪರಿಶೀಲಿಸಿದ ಬಿತ್ತನೆ ದಿನಾಂಕ ಮತ್ತು ಹವಾಮಾನ ದಾಖಲೆ ಅಗತ್ಯ.",
        "hi": "गतिशील जल संतुलन के लिए सत्यापित बुवाई तिथि और मौसम साक्ष्य आवश्यक है।",
    },
    "No quantitative water model calibrated for this crop.": {
        "en": "No quantitative water model calibrated for this crop.",
        "kn": "ಈ ಬೆಳೆಗೆ ಪ್ರಮಾಣಾತ್ಮಕ ನೀರಿನ ಮಾದರಿಯನ್ನು ಮಾಪನಾಂಕ ಮಾಡಿಲ್ಲ.",
        "hi": "इस फसल के लिए मात्रात्मक जल मॉडल कैलिब्रेट नहीं है।",
    },
    "'ಹಳದಿ' is ambiguous between the color yellow and colloquial turmeric reference.": {
        "en": "'ಹಳದಿ' is ambiguous between the color yellow and colloquial turmeric reference.",
        "kn": "'ಹಳದಿ' ಎಂಬುದು ಹಳದಿ ಬಣ್ಣವನ್ನೂ ಅರಿಶಿನ ಬೆಳೆಯನ್ನೂ ಸೂಚಿಸಬಹುದು.",
        "hi": "'ಹಳದಿ' से पीले रंग या बोलचाल में हल्दी की फसल, दोनों का अर्थ हो सकता है।",
    },
    "Ambiguous crop identification requires explicit user confirmation.": {
        "en": "Ambiguous crop identification requires explicit user confirmation.",
        "kn": "ಅಸ್ಪಷ್ಟ ಬೆಳೆ ಗುರುತಿಗೆ ಬಳಕೆದಾರರ ಸ್ಪಷ್ಟ ದೃಢೀಕರಣ ಅಗತ್ಯ.",
        "hi": "अस्पष्ट फसल पहचान के लिए उपयोगकर्ता की स्पष्ट पुष्टि आवश्यक है।",
    },
    "General query outside recognized crop water or capability categories.": {
        "en": "General query outside recognized crop water or capability categories.",
        "kn": "ಈ ಸಾಮಾನ್ಯ ಪ್ರಶ್ನೆ ಗುರುತಿಸಲಾದ ಬೆಳೆ ನೀರು ಅಥವಾ ಸಾಮರ್ಥ್ಯದ ವಿಭಾಗಗಳಿಗೆ ಸೇರಿಲ್ಲ.",
        "hi": "यह सामान्य प्रश्न पहचानी गई फसल-जल या क्षमता श्रेणियों से बाहर है।",
    },
}


def _localized_user_text(value: str, language: LocaleType) -> str:
    if language == "en":
        return value
    for canonical, names in sorted(
        CROP_DISPLAY_NAMES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        value = value.replace(canonical, names[language])
    return value


def _localized_limitation(value: str, language: LocaleType) -> str:
    if value.startswith("No calibrated dry-matter yield output for ") and value.endswith(
        " under FAO-56."
    ):
        crop = value.removeprefix("No calibrated dry-matter yield output for ").removesuffix(
            " under FAO-56."
        )
        crop = _localized_user_text(crop, language)
        if language == "kn":
            return f"{crop} ಬೆಳೆಗೆ FAO-56 ಅಡಿಯಲ್ಲಿ ಮಾಪನಾಂಕಿತ ಒಣಪದಾರ್ಥ ಇಳುವರಿ ಫಲಿತಾಂಶ ಲಭ್ಯವಿಲ್ಲ."
        if language == "hi":
            return f"{crop} के लिए FAO-56 के अंतर्गत कैलिब्रेटेड शुष्क-पदार्थ उपज परिणाम उपलब्ध नहीं है।"
    return LIMITATION_TRANSLATIONS.get(value, {}).get(language, value)


# Keyword trigger patterns for local languages
PATHOLOGY_KEYWORDS = {
    "en": [
        "disease",
        "pest",
        "fungus",
        "fungal",
        "blight",
        "rot",
        "spots",
        "brown spots",
        "insect",
        "insects",
        "leaf spot",
        "cure",
        "spray",
        "pesticide",
        "infection",
        "yellowing",
        "yellow leaves",
        "yellow leaf",
        "chlorosis",
    ],
    "kn": [
        "ರೋಗ",
        "ಕೀಟ",
        "ಶಿಲೀಂಧ್ರ",
        "ಕೊಳೆತ",
        "ಮಚ್ಚೆ",
        "ಬಾಧೆ",
        "ಔಷಧ",
        "ಚಿಕಿತ್ಸೆ",
        "ಹುಳು",
        "ಚುಕ್ಕೆ",
        "ಹಳದಿ ಎಲೆ",
        "ಹಳದಿ ರೋಗ",
        "ಎಲೆ ಹಳದಿ",
        "ಹಳದಿಯಾಗುತ್ತಿದೆ",
        "ಹಳದಿ ಆಗಿವೆ",
    ],
    "hi": [
        "रोग",
        "कीट",
        "फफूंद",
        "कीड़ा",
        "कीड़े",
        "धब्बा",
        "धब्बे",
        "सड़न",
        "इलाज",
        "दवा",
        "छिड़काव",
        "पीलापन",
        "पीली पत्ती",
        "पीला पत्ता",
        "पत्तियां पीली",
    ],
}

PRICING_KEYWORDS = {
    "en": ["price", "market", "mandi", "rate", "cost", "rupees", "sell", "profit", "today's price", "worth", "bhav"],
    "kn": ["ಬೆಲೆ", "ಮಾರುಕಟ್ಟೆ", "ದರ", "ಮಂಡಿ", "ಮಾರಾಟ", "ಲಾಭ", "ರೂಪಾಯಿ", "ಖರ್ಚು"],
    "hi": ["भाव", "मंडी", "दाम", "कीमत", "मूल्य", "बिक्री", "मुनाफा", "रुपये", "बाजार"],
}

CAPABILITY_KEYWORDS = {
    "en": ["yield", "predict", "forecast", "simulate", "model", "quintal", "harvest estimate", "how much yield", "production"],
    "kn": ["ಇಳುವರಿ", "ಮುನ್ಸೂಚನೆ", "ಅಂದಾಜು", "ಕ್ವಿಂಟಾಲ್", "ಉತ್ಪಾದನೆ", "ಇಳುವರಿ ಮುನ್ಸೂಚನೆ"],
    "hi": ["उपज", "अनुमान", "पूर्वानुमान", "पैदावार", "क्विंटल", "उत्पादन"],
}

WATER_KEYWORDS = {
    "en": ["water", "irrigation", "moisture", "need", "requirement", "irrigate", "how much water"],
    "kn": ["ನೀರು", "ನೀರಾವರಿ", "ತೇವಾಂಶ", "ಅಗತ್ಯ", "ಅಗತ್ಯತೆ", "ನೀರಿನ ಅಗತ್ಯ"],
    "hi": ["पानी", "सिंचाई", "नमी", "जरूरत", "आवश्यकता", "जल"],
}


@dataclass(frozen=True)
class InteractionResult:
    intent: str
    language: LocaleType
    resolution_status: ResolutionStatus
    resolved_crop: CropRecord | None
    candidates: list[CandidateMatch]
    response_text: str
    speech_text: str
    limitations: list[str] = field(default_factory=list)
    escalation_required: bool = False
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "response_text", _localized_user_text(self.response_text, self.language)
        )
        object.__setattr__(
            self, "speech_text", _localized_user_text(self.speech_text, self.language)
        )
        object.__setattr__(
            self,
            "limitations",
            [_localized_limitation(item, self.language) for item in self.limitations],
        )


class BoundedInteractionService:
    """Provides deterministic, evidence-grounded responses to farmer queries in English, Kannada, and Hindi.

    Strictly refuses to invent prices, yield forecasts, or plant pathology diagnoses.
    """

    def __init__(self, resolver: CropLensResolver | None = None) -> None:
        self.resolver = resolver if resolver is not None else CropLensResolver(CROP_REGISTRY)

    def _matches_any_keyword(self, text: str, keywords: list[str]) -> bool:
        normalized = _normalize(text)
        tokens = normalized.split()
        for kw in keywords:
            kw_norm = _normalize(kw)
            if " " in kw_norm:
                if kw_norm in normalized:
                    return True
            else:
                if kw_norm in tokens or any(tok.startswith(kw_norm) for tok in tokens if len(kw_norm) >= 3):
                    return True
        return False

    def interact(self, query: str, language: LocaleType = "en") -> InteractionResult:
        clean_query = query.strip()
        if not clean_query:
            return self._build_empty_response(language)

        # 1. Guardrail Check: Plant Pathology (Pest / Disease / Rot)
        all_pathology_kws = (
            PATHOLOGY_KEYWORDS.get(language, [])
            + PATHOLOGY_KEYWORDS["en"]
            + PATHOLOGY_KEYWORDS["kn"]
            + PATHOLOGY_KEYWORDS["hi"]
        )
        if self._matches_any_keyword(clean_query, all_pathology_kws):
            return self._handle_plant_pathology(clean_query, language)

        # 2. Guardrail Check: Market Pricing / Mandi Rates
        all_pricing_kws = (
            PRICING_KEYWORDS.get(language, [])
            + PRICING_KEYWORDS["en"]
            + PRICING_KEYWORDS["kn"]
            + PRICING_KEYWORDS["hi"]
        )
        if self._matches_any_keyword(clean_query, all_pricing_kws):
            return self._handle_market_pricing(clean_query, language)

        # 3. Resolve crop identity from query
        resolution: ResolutionResult = self.resolver.resolve(clean_query)

        # 4. Check for Yield / Simulation Capability inquiries
        all_cap_kws = (
            CAPABILITY_KEYWORDS.get(language, [])
            + CAPABILITY_KEYWORDS["en"]
            + CAPABILITY_KEYWORDS["kn"]
            + CAPABILITY_KEYWORDS["hi"]
        )
        if self._matches_any_keyword(clean_query, all_cap_kws):
            return self._handle_crop_capability(clean_query, language, resolution)

        # 5. Check for Water / Irrigation requirement inquiries
        all_water_kws = (
            WATER_KEYWORDS.get(language, [])
            + WATER_KEYWORDS["en"]
            + WATER_KEYWORDS["kn"]
            + WATER_KEYWORDS["hi"]
        )
        if self._matches_any_keyword(clean_query, all_water_kws):
            return self._handle_water_guidance(clean_query, language, resolution)

        # 6. Direct Crop Resolution inquiry (e.g. "ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ", "I grow turmeric")
        if resolution.status == ResolutionStatus.EXACT_MATCH and resolution.crop is not None:
            return self._handle_crop_resolution(resolution, language)
        elif resolution.status == ResolutionStatus.AMBIGUOUS:
            return self._handle_ambiguous_crop(resolution, language)

        # 7. Fallback: Bounded system overview
        return self._handle_unknown(clean_query, language)

    # -------------------------------------------------------------------------
    # Intent Handlers
    # -------------------------------------------------------------------------
    def _build_empty_response(self, language: LocaleType) -> InteractionResult:
        if language == "kn":
            resp = "ದಯವಿಟ್ಟು ಪ್ರಶ್ನೆ ಅಥವಾ ಬೆಳೆಯ ಹೆಸರನ್ನು ನಮೂದಿಸಿ."
            speech = "ದಯವಿಟ್ಟು ಪ್ರಶ್ನೆಯನ್ನು ನಮೂದಿಸಿ."
        elif language == "hi":
            resp = "कृपया कोई प्रश्न या फसल का नाम दर्ज करें।"
            speech = "कृपया प्रश्न दर्ज करें।"
        else:
            resp = "Please enter a question or crop name."
            speech = "Please enter a question."

        return InteractionResult(
            intent="unknown_or_unsupported",
            language=language,
            resolution_status=ResolutionStatus.NOT_FOUND,
            resolved_crop=None,
            candidates=[],
            response_text=resp,
            speech_text=speech,
            limitations=["Empty query."],
        )

    def _handle_plant_pathology(self, query: str, language: LocaleType) -> InteractionResult:
        if language == "kn":
            resp = (
                "ಟೆರ್ರಾಪಲ್ಸ್ ಬೆಳೆ ರೋಗಗಳು, ಕೀಟ ಬಾಧೆಗಳು ಅಥವಾ ರಾಸಾಯನಿಕ ಚಿಕಿತ್ಸೆಗಳನ್ನು ರೋಗನಿರ್ಣಯ ಮಾಡುವುದಿಲ್ಲ. "
                "ನಿಖರ ತಪಾಸಣೆ ಮತ್ತು ಸುರಕ್ಷಿತ ಪರಿಹಾರಕ್ಕಾಗಿ ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸ್ಥಳೀಯ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ (KVK), "
                "ಕೃಷಿ ವಿಸ್ತರಣಾ ಅಧಿಕಾರಿ ಅಥವಾ ವಿಶ್ವವಿದ್ಯಾಲಯದ ತಜ್ಞರನ್ನು ಸಂಪರ್ಕಿಸಿ."
            )
            speech = "ಬೆಳೆ ರೋಗ ತಪಾಸಣೆಗೆ ನಿಮ್ಮ ಸ್ಥಳೀಯ ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ ತಜ್ಞರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        elif language == "hi":
            resp = (
                "टेरापल्स फसल की बीमारियों, कीटों या रासायनिक उपचारों का निदान नहीं करता है। "
                "सटीक निरीक्षण और सुरक्षित सलाह के लिए कृपया अपने नजदीकी कृषि विज्ञान केंद्र (KVK), "
                "कृषि विस्तार अधिकारी या विश्वविद्यालय के कृषि विशेषज्ञ से संपर्क करें।"
            )
            speech = "फसल रोग की जांच के लिए कृपया अपने नजदीकी कृषि विज्ञान केंद्र से संपर्क करें।"
        else:
            resp = (
                "TerraPulse does not diagnose crop diseases, pests, or recommend chemical treatments. "
                "Please consult your local Krishi Vigyan Kendra (KVK), agricultural extension officer, "
                "or university agronomist for in-person inspection and safe guidance."
            )
            speech = "Crop disease diagnosis requires physical inspection. Please consult your local Krishi Vigyan Kendra for expert advice."

        return InteractionResult(
            intent="escalation_plant_pathology",
            language=language,
            resolution_status=ResolutionStatus.NOT_FOUND,
            resolved_crop=None,
            candidates=[],
            response_text=resp,
            speech_text=speech,
            limitations=["Plant pathology and chemical/pest diagnosis are outside TerraPulse's biophysical scope."],
            escalation_required=True,
            sources=[
                "Indian Council of Agricultural Research (ICAR)",
                "Krishi Vigyan Kendra (KVK) Network",
                "State Agricultural Extension Department",
            ],
        )

    def _handle_market_pricing(self, query: str, language: LocaleType) -> InteractionResult:
        if language == "kn":
            resp = (
                "ಟೆರ್ರಾಪಲ್ಸ್ ಮಣ್ಣು ಮತ್ತು ನೀರಿನ ವೈಜ್ಞಾನಿಕ ನಿರ್ಧಾರ ಬೆಂಬಲ ಪ್ರಯೋಗಾಲಯವಾಗಿದೆ. "
                "ಇದು ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು ಅಥವಾ ಬೆಲೆ ಮುನ್ಸೂಚನೆಯನ್ನು ನೀಡುವುದಿಲ್ಲ. "
                "ಅಧಿಕೃತ ಬೆಲೆಗಳಿಗಾಗಿ ಅಗ್ಮಾರ್ಕ್‌ನೆಟ್ (Agmarknet) ಅಥವಾ ಸ್ಥಳೀಯ ಎಪಿಎಂಸಿ ಮಂಡಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."
            )
            speech = "ಟೆರ್ರಾಪಲ್ಸ್ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳನ್ನು ನೀಡುವುದಿಲ್ಲ. ದಯವಿಟ್ಟು ಸ್ಥಳೀಯ ಎಪಿಎಂಸಿ ಮಂಡಿಯನ್ನು ಪರಿಶೀಲಿಸಿ."
        elif language == "hi":
            resp = (
                "टेरापल्स एक वैज्ञानिक मृदा-जल निर्णय प्रयोगशाला है और जिंस बाजार के भाव या मूल्य पूर्वानुमान प्रदान नहीं करता है। "
                "सटीक और आधिकारिक दरों के लिए कृपया एगमार्कनेट (Agmarknet) या अपने स्थानीय एपीएमसी मंडी पोर्टल को देखें।"
            )
            speech = "टेरापल्स बाजार भाव प्रदान नहीं करता है। कृपया स्थानीय मंडी या एगमार्कनेट देखें।"
        else:
            resp = (
                "TerraPulse is a scientific soil-water decision laboratory and does not provide commodity market prices or price predictions. "
                "For authentic market rates, refer to official portals like Agmarknet or your local APMC mandi."
            )
            speech = "TerraPulse does not provide market prices. Please check Agmarknet or your local APMC mandi."

        return InteractionResult(
            intent="refusal_market_pricing",
            language=language,
            resolution_status=ResolutionStatus.NOT_FOUND,
            resolved_crop=None,
            candidates=[],
            response_text=resp,
            speech_text=speech,
            limitations=["Market pricing, commodity forecasting, and financial speculation are strictly excluded from TerraPulse."],
            escalation_required=False,
            sources=["e-NAM (National Agriculture Market)", "Agmarknet (Directorate of Marketing & Inspection)"],
        )

    def _handle_crop_capability(
        self, query: str, language: LocaleType, resolution: ResolutionResult
    ) -> InteractionResult:
        if resolution.status == ResolutionStatus.AMBIGUOUS:
            return self._handle_ambiguous_crop(resolution, language)

        crop = resolution.crop
        if crop is None:
            # General capability explanation
            if language == "kn":
                resp = (
                    "ಅರಿಶಿನಕ್ಕೆ FAO-56 ನೀರಿನ ಸಮತೋಲನಕ್ಕಾಗಿ ತಾತ್ಕಾಲಿಕ A, B ಅಥವಾ C ಹಂತ ನಕ್ಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ. "
                    + WHEAT_EXAMPLE_LABELS[language]
                )
            elif language == "hi":
                resp = (
                    "हल्दी के FAO-56 जल संतुलन के लिए अनंतिम चरण मानचित्र A, B या C चुनें। "
                    + WHEAT_EXAMPLE_LABELS[language]
                )
            else:
                resp = (
                    "Turmeric supports FAO-56 root-zone water balance with explicit provisional mapping A, B, or C. "
                    + WHEAT_EXAMPLE_LABELS[language]
                )

            return InteractionResult(
                intent="crop_capability",
                language=language,
                resolution_status=ResolutionStatus.NOT_FOUND,
                resolved_crop=None,
                candidates=[],
                response_text=resp,
                speech_text=resp,
                limitations=["Yield simulation depends on engine capability: AquaCrop supports yield; FAO-56 does not."],
                sources=["FAO-56 Irrigation and Drainage Paper", "FAO AquaCrop Reference Manual"],
            )

        # Specific crop capability
        engine = crop.selected_engine
        canonical = crop.canonical_name

        if canonical == "Wheat":
            return self._handle_wheat_example(resolution, language, "crop_capability")

        if engine == "AquaCrop":
            if language == "kn":
                resp = (
                    f"{canonical} ಬೆಳೆಗೆ ಕ್ಯಾಟಲಾಗ್‌ನಲ್ಲಿ AquaCrop ಉಲ್ಲೇಖವಿದೆ. "
                    "ಜಮೀನಿನ ಮಟ್ಟದ ಸಿಮ್ಯುಲೇಶನ್ ಲಭ್ಯವಿಲ್ಲ."
                )
                speech = resp
            elif language == "hi":
                resp = (
                    f"कैटलॉग में {canonical} के लिए AquaCrop का उल्लेख है। "
                    "खेत-स्तरीय सिमुलेशन उपलब्ध नहीं है।"
                )
                speech = resp
            else:
                resp = (
                    f"The catalogue lists AquaCrop for {canonical}. Farm-scale simulation is unavailable."
                )
                speech = resp

            return InteractionResult(
                intent="crop_capability",
                language=language,
                resolution_status=ResolutionStatus.EXACT_MATCH,
                resolved_crop=crop,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=["No verified farm-scale AquaCrop profile is enabled for this crop."],
                sources=["FAO AquaCrop Model Reference", "TerraPulse C7 Model Registry"],
            )

        elif engine == "FAO-56" and canonical == "Turmeric":
            if language == "kn":
                resp = (
                    f"{canonical} ಬೆಳೆಗಾಗಿ FAO-56 ({crop.engine_version}) ಮಾದರಿಯು ಬೇರಿನ ವಲಯದ ನೀರಿನ ಕೊರತೆ ಮತ್ತು ಆವಿಯಾಗುವಿಕೆಯನ್ನು (ET) ಲೆಕ್ಕಹಾಕುತ್ತದೆ. "
                    "ತಾತ್ಕಾಲಿಕ A, B ಅಥವಾ C ಹಂತ ನಕ್ಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ. ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಲಭ್ಯವಿಲ್ಲ."
                )
                speech = f"{canonical} ಬೆಳೆಗೆ FAO-56 ನೀರಿನ ಸಮತೋಲನ ಲಭ್ಯವಿದೆ, ಆದರೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಲಭ್ಯವಿಲ್ಲ."
            elif language == "hi":
                resp = (
                    f"{canonical} फसल के लिए FAO-56 ({crop.engine_version}) मॉडल जड़-क्षेत्र में जल की कमी और वाष्पोत्सर्जन (ET) का आकलन करता है। "
                    "अनंतिम चरण मानचित्र A, B या C चुनें। उपज का अनुमान उपलब्ध नहीं है।"
                )
                speech = f"{canonical} के लिए FAO-56 जल संतुलन उपलब्ध है, लेकिन उपज अनुमान समर्थित नहीं है।"
            else:
                resp = (
                    f"For {canonical}, TerraPulse uses a single crop coefficient under FAO-56. "
                    "Daily root-zone water balance requires explicit provisional stage mapping A, B, or C. "
                    f"However, calibrated dry-matter yield prediction is explicitly not supported for {canonical} under FAO-56."
                )
                speech = f"{canonical} supports water balance and water stress simulation under FAO-56, but not yield prediction."

            return InteractionResult(
                intent="crop_capability",
                language=language,
                resolution_status=ResolutionStatus.EXACT_MATCH,
                resolved_crop=crop,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=[f"No calibrated dry-matter yield output for {canonical} under FAO-56."],
                sources=["FAO-56 Irrigation and Drainage Paper 56", "TerraPulse C7 Model Registry"],
            )

        else:
            # identity/ecology-only
            if language == "kn":
                resp = (
                    f"{canonical} ಬೆಳೆಯು ಪ್ರಸ್ತುತ ಗುರುತು ಮತ್ತು ಪರಿಸರ-ಉಲ್ಲೇಖ ಮಟ್ಟದಲ್ಲಿ ಮಾತ್ರ ನೋಂದಾಯಿಸಲ್ಪಟ್ಟಿದೆ. "
                    "ಇದಕ್ಕೆ ಪರಿಮಾಣಾತ್ಮಕ ಸಿಮ್ಯುಲೇಶನ್ ಅಥವಾ ಇಳುವರಿ ಮಾದರಿ ಲಭ್ಯವಿಲ್ಲ."
                )
                speech = f"{canonical} ಬೆಳೆಗೆ ಸಿಮ್ಯುಲೇಶನ್ ಅಥವಾ ಇಳುವರಿ ಮಾದರಿ ಲಭ್ಯವಿಲ್ಲ."
            elif language == "hi":
                resp = (
                    f"{canonical} फसल वर्तमान में केवल वर्गीकरण और पारिस्थितिक संदर्भ स्तर पर पंजीकृत है। "
                    "इसके लिए कोई मात्रात्मक सिमुलेशन या उपज मॉडल कैलिब्रेट नहीं है।"
                )
                speech = f"{canonical} के लिए कोई मात्रात्मक सिमुलेशन या उपज मॉडल समर्थित नहीं है।"
            else:
                resp = (
                    f"{canonical} is registered for taxonomic identity and ecological reference only. "
                    "No calibrated AquaCrop or FAO-56 quantitative simulation model is enabled for this crop."
                )
                speech = f"{canonical} has identity-only reference and does not support yield simulation."

            return InteractionResult(
                intent="crop_capability",
                language=language,
                resolution_status=ResolutionStatus.EXACT_MATCH,
                resolved_crop=crop,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=["No quantitative simulation calibrated for this crop.", "Identity and taxonomy reference only."],
                sources=["FAO ECOCROP", "GBIF Backbone Taxonomy"],
            )

    def _handle_water_guidance(
        self, query: str, language: LocaleType, resolution: ResolutionResult
    ) -> InteractionResult:
        if resolution.status == ResolutionStatus.AMBIGUOUS:
            return self._handle_ambiguous_crop(resolution, language)

        crop = resolution.crop
        if crop is None:
            # General water guidance
            if language == "kn":
                resp = (
                    "ಬೆಳೆಯ ನೀರಿನ ಅಗತ್ಯವು ಸ್ಥಳೀಯ ಹವಾಮಾನ (ಆವಿಯಾಗುವಿಕೆ ET0), ಮಣ್ಣಿನ ವಿಧ ಮತ್ತು ಬೆಳೆಯ ಬೆಳವಣಿಗೆಯ ಹಂತವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ. "
                    "ನಿಮ್ಮ ಜಮೀನನ್ನು ಆಯ್ಕೆಮಾಡಿ ಪರಿಸರ ಡೇಟಾವನ್ನು ವೀಕ್ಷಿಸಿ."
                )
                speech = "ಬೆಳೆಯ ನೀರಿನ ಅಗತ್ಯವು ಹವಾಮಾನ ಮತ್ತು ಮಣ್ಣಿನ ತೇವಾಂಶವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ."
            elif language == "hi":
                resp = (
                    "फसल की पानी की आवश्यकता स्थानीय मौसम (वाष्पोत्सर्जन ET0), मिट्टी के प्रकार और फसल के विकास चरण पर निर्भर करती है। "
                    "विस्तृत जानकारी के लिए अपना खेत चुनें और पर्यावरणीय साक्ष्य देखें।"
                )
                speech = "फसल के लिए पानी की आवश्यकता मौसम और मिट्टी की नमी पर निर्भर करती है।"
            else:
                resp = (
                    "Crop water requirements depend on local reference evapotranspiration (ET0), soil moisture profile, and growth stage coefficients (Kc). "
                    "To view quantitative daily water balance, open your plot's environmental evidence."
                )
                speech = "Water requirements depend on local reference evapotranspiration and crop growth stages."

            return InteractionResult(
                intent="water_guidance",
                language=language,
                resolution_status=ResolutionStatus.NOT_FOUND,
                resolved_crop=None,
                candidates=[],
                response_text=resp,
                speech_text=speech,
                limitations=["Quantitative water calculation requires plot location, weather data, and soil profile."],
                sources=["FAO-56 Irrigation and Drainage Paper"],
            )

        # Sourced parameters from C7
        params = crop.model_parameters
        canonical = crop.canonical_name
        kc_info = []
        if "kcIni" in params and "kcMid" in params and "kcEnd" in params:
            kc_info = [
                f"Initial stage (Kc): {params['kcIni']}",
                f"Mid-season peak (Kc): {params['kcMid']}",
                f"Late season (Kc): {params['kcEnd']}",
            ]

        if crop.selected_engine == "FAO-56" and kc_info:
            kc_str = ", ".join(kc_info)
            if language == "kn":
                resp = (
                    f"{canonical} ಬೆಳೆಗಾಗಿ FAO-56 ಪ್ರಮಾಣಿತ ಬೆಳೆ ಗುಣಾಂಕಗಳು (Kc): {kc_str}. "
                    "ದೈನಂದಿನ ನೀರಿನ ಬಳಕೆ = ET0 × Kc. ನಿಜವಾದ ನೀರಿನ ಅಗತ್ಯವು ನಿಮ್ಮ ಜಮೀನಿನ ದೈನಂದಿನ ಮಳೆ ಮತ್ತು ಮಣ್ಣಿನ ತೇವಾಂಶವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ."
                )
                speech = f"{canonical} ಬೆಳೆಗೆ ಗರಿಷ್ಠ ಹಂತದಲ್ಲಿ Kc ಗುಣಾಂಕ {params.get('kcMid')} ಇರುತ್ತದೆ."
            elif language == "hi":
                resp = (
                    f"{canonical} फसल के लिए FAO-56 मानक फसल गुणांक (Kc): {kc_str}। "
                    "दैनिक जल आवश्यकता = ET0 × Kc। वास्तविक सिंचाई आवश्यकता आपके खेत की मिट्टी की नमी और दैनिक वर्षा पर निर्भर करती है।"
                )
                speech = f"{canonical} के लिए मुख्य वृद्धि चरण में फसल गुणांक {params.get('kcMid')} है।"
            else:
                resp = (
                    f"For {canonical}, standard FAO-56 crop coefficients are: {kc_str}. "
                    "Daily crop evapotranspiration (ETc) is calculated as ET0 × Kc. Actual irrigation needed depends on effective daily rainfall and soil moisture depletion in your field."
                )
                speech = f"For {canonical}, the mid-season peak crop coefficient is {params.get('kcMid')}."

            return InteractionResult(
                intent="water_guidance",
                language=language,
                resolution_status=ResolutionStatus.EXACT_MATCH,
                resolved_crop=crop,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=["Standard Kc values require adjustment for local climate humidity and wind conditions."],
                sources=["FAO-56 Irrigation and Drainage Paper 56", "TerraPulse C7 Model Registry"],
            )
        elif canonical == "Wheat":
            return self._handle_wheat_example(resolution, language, "water_guidance")
        elif crop.selected_engine == "AquaCrop":
            if language == "kn":
                resp = (
                    f"{canonical} ಬೆಳೆಗಾಗಿ AquaCrop ಎಂಜಿನ್ ಕ್ಯಾನೋಪಿ ಕವರ್ ಮತ್ತು ಬೇರಿನ ವಲಯದ ನೀರಿನ ಕೊರತೆಯನ್ನು ಸಿಮ್ಯುಲೇಟ್ ಮಾಡುತ್ತದೆ. "
                    "ಬೇಸ್ ತಾಪಮಾನ: 8.0°C, ಗರಿಷ್ಠ ತಾಪಮಾನ: 30.0°C."
                )
                speech = f"{canonical} ಬೆಳೆಗೆ AquaCrop ನೀರಿನ ಸಮತೋಲನವನ್ನು ಲೆಕ್ಕಹಾಕುತ್ತದೆ."
            elif language == "hi":
                resp = (
                    f"{canonical} फसल के लिए AquaCrop मॉडल कैनोपी आवरण और जड़-क्षेत्र के जल संतुलन का अनुकरण करता है। "
                    "आधार तापमान: 8.0°C, अधिकतम सीमा: 30.0°C।"
                )
                speech = f"{canonical} के लिए AquaCrop जल संतुलन मॉडल सक्रिय है।"
            else:
                resp = (
                    f"For {canonical}, AquaCrop dynamically simulates canopy expansion, transpiration, and root-zone water depletion. "
                    "Base temperature: 8.0°C, Cutoff temperature: 30.0°C."
                )
                speech = f"{canonical} uses AquaCrop to simulate dynamic transpiration and water stress."

            return InteractionResult(
                intent="water_guidance",
                language=language,
                resolution_status=ResolutionStatus.EXACT_MATCH,
                resolved_crop=crop,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=["Dynamic water balance requires verified planting date and weather realization."],
                sources=["FAO AquaCrop Manual", "TerraPulse C7 Model Registry"],
            )
        else:
            # uncalibrated
            if language == "kn":
                resp = f"{canonical} ಬೆಳೆಗೆ ಪ್ರಮಾಣೀಕೃತ ನೀರಿನ ಗುಣಾಂಕಗಳು ಲಭ್ಯವಿಲ್ಲ. ಕೃಷಿ ವಿಸ್ತರಣಾ ತಜ್ಞರನ್ನು ಸಂಪರ್ಕಿಸಿ."
                speech = f"{canonical} ಬೆಳೆಗೆ ನೀರಿನ ಗುಣಾಂಕ ಲಭ್ಯವಿಲ್ಲ."
            elif language == "hi":
                resp = f"{canonical} फसल के लिए कैलिब्रेटेड जल गुणांक उपलब्ध नहीं हैं। कृषि विशेषज्ञ से सलाह लें।"
                speech = f"{canonical} के लिए जल गुणांक उपलब्ध नहीं हैं।"
            else:
                resp = f"Calibrated quantitative water balance parameters are not available for {canonical}."
                speech = f"Water balance parameters are not available for {canonical}."

            return InteractionResult(
                intent="water_guidance",
                language=language,
                resolution_status=ResolutionStatus.EXACT_MATCH,
                resolved_crop=crop,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=["No quantitative water model calibrated for this crop."],
                sources=["TerraPulse C7 Model Registry"],
            )

    def _handle_wheat_example(
        self, resolution: ResolutionResult, language: LocaleType,
        intent: Literal["crop_capability", "crop_resolution", "water_guidance"],
    ) -> InteractionResult:
        text = WHEAT_EXAMPLE_LABELS[language]
        return InteractionResult(
            intent=intent,
            language=language,
            resolution_status=ResolutionStatus.EXACT_MATCH,
            resolved_crop=resolution.crop,
            candidates=resolution.candidates,
            response_text=text,
            speech_text=text,
            limitations=[text],
            sources=["TerraPulse C7 Model Registry"],
        )

    def _handle_crop_resolution(
        self, resolution: ResolutionResult, language: LocaleType
    ) -> InteractionResult:
        crop = resolution.crop
        if crop is None:
            return self._handle_unknown(resolution.query, language)
        if crop.canonical_name == "Wheat":
            return self._handle_wheat_example(resolution, language, "crop_resolution")

        canonical = crop.canonical_name
        sci = crop.scientific_name
        engine = crop.selected_engine
        outputs = (
            ", ".join(
                SUPPORTED_OUTPUT_LABELS.get(output, {}).get(language, output)
                for output in crop.supported_outputs
            )
            if crop.supported_outputs
            else IDENTITY_ONLY_LABELS[language]
        )

        if language == "kn":
            resp = (
                f"ನಿಮ್ಮ ಬೆಳೆ '{canonical}' ({sci}) ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ. "
                f"ಆಯ್ಕೆಮಾಡಿದ ಸಿಮ್ಯುಲೇಶನ್ ಎಂಜಿನ್: {engine} (v{crop.engine_version}). "
                f"ಬೆಂಬಲಿತ ಔಟ್‌ಪುಟ್‌ಗಳು: {outputs}."
            )
            speech = f"ನಿಮ್ಮ ಬೆಳೆ {canonical} ಎಂದು ಯಶಸ್ವಿಯಾಗಿ ಗುರುತಿಸಲಾಗಿದೆ. ಮಾದರಿ ಎಂಜಿನ್ {engine}."
        elif language == "hi":
            resp = (
                f"आपकी फसल की पहचान '{canonical}' ({sci}) के रूप में हुई है। "
                f"चयनित सिमुलेशन इंजन: {engine} (v{crop.engine_version})। "
                f"समर्थित आउटपुट: {outputs}।"
            )
            speech = f"आपकी फसल {canonical} के रूप में पहचानी गई है। सिमुलेशन इंजन {engine} है।"
        else:
            resp = (
                f"Identified crop as '{canonical}' ({sci}). "
                f"Simulation engine: {engine} (v{crop.engine_version}). "
                f"Supported outputs: {outputs}."
            )
            speech = f"Identified crop as {canonical} using {engine}."

        return InteractionResult(
            intent="crop_resolution",
            language=language,
            resolution_status=ResolutionStatus.EXACT_MATCH,
            resolved_crop=crop,
            candidates=resolution.candidates,
            response_text=resp,
            speech_text=speech,
            limitations=list(crop.known_limitations),
            sources=[ref.source_name for ref in crop.external_references] + ["TerraPulse C7 Registry"],
        )

    def _handle_ambiguous_crop(
        self, resolution: ResolutionResult, language: LocaleType
    ) -> InteractionResult:
        query_norm = _normalize(resolution.query)
        if "ಹಳದಿ" in query_norm.split():
            if language == "kn":
                resp = (
                    "ಕನ್ನಡದಲ್ಲಿ 'ಹಳದಿ' ಎಂದರೆ ಬಣ್ಣ. ನೀವು ಅರಿಶಿನ ಬೆಳೆಯನ್ನು (Turmeric) ಉದ್ದೇಶಿಸಿದ್ದರೆ 'ಅರಿಶಿನ' ಎಂದು ದೃಢೀಕರಿಸಿ, "
                    "ಅಥವಾ ಎಲೆಗಳು ಹಳದಿಯಾಗುವ ರೋಗ ಲಕ್ಷಣದ ಕುರಿತಾಗಿದ್ದರೆ ದಯವಿಟ್ಟು ವಿಸ್ತರಿಸಿ."
                )
                speech = "ಕನ್ನಡದಲ್ಲಿ ಹಳದಿ ಎಂದರೆ ಬಣ್ಣ. ಅರಿಶಿನ ಬೆಳೆಯಾದರೆ ಅರಿಶಿನ ಎಂದು ದೃಢೀಕರಿಸಿ."
            elif language == "hi":
                resp = (
                    "कन्नड़ में 'ಹಳದಿ' का अर्थ पीला रंग होता है। यदि आपका आशय हल्दी (Turmeric) फसल से है तो 'हल्दी' का चयन करें, "
                    "अथवा यदि यह पत्तियों के पीलेपन का लक्षण है तो स्पष्ट करें।"
                )
                speech = "यदि आपका आशय हल्दी फसल से है तो कृपया पुष्टि करें।"
            else:
                resp = (
                    "In Kannada, 'ಹಳದಿ' denotes the color yellow. If you intended the crop Turmeric, please confirm "
                    "'Turmeric' / 'ಅರಿಶಿನ', or specify if referring to yellow leaf symptoms."
                )
                speech = "ಹಳದಿ means yellow in Kannada. Please confirm if you intended Turmeric."

            return InteractionResult(
                intent="crop_resolution",
                language=language,
                resolution_status=ResolutionStatus.AMBIGUOUS,
                resolved_crop=None,
                candidates=resolution.candidates,
                response_text=resp,
                speech_text=speech,
                limitations=["'ಹಳದಿ' is ambiguous between the color yellow and colloquial turmeric reference."],
                sources=["TerraPulse Indic Crop Disambiguation"],
            )

        candidate_names = [f"{c.canonical_name} ({c.scientific_name})" for c in resolution.candidates]
        candidates_str = ", ".join(candidate_names) if candidate_names else "multiple candidates"

        if language == "kn":
            resp = (
                f"ನಿಮ್ಮ ಪ್ರಶ್ನೆ '{resolution.query}' ಹಲವಾರು ಬೆಳೆಗಳಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ: {candidates_str}. "
                "ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟವಾದ ಬೆಳೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ ಅಥವಾ ನಿರ್ದಿಷ್ಟ ಹೆಸರನ್ನು ನಮೂದಿಸಿ."
            )
            speech = f"ಪ್ರಶ್ನೆ ಅಸ್ಪಷ್ಟವಾಗಿದೆ ಮತ್ತು {len(resolution.candidates)} ಬೆಳೆಗಳಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ. ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟಪಡಿಸಿ."
        elif language == "hi":
            resp = (
                f"आपका प्रश्न '{resolution.query}' कई संभावित फसलों से मेल खाता है: {candidates_str}। "
                "कृपया पुष्टि के लिए किसी विशिष्ट फसल का नाम बताएं या चुनें।"
            )
            speech = "यह नाम कई फसलों से मेल खाता है। कृपया स्पष्ट फसल का चयन करें।"
        else:
            resp = (
                f"Your query '{resolution.query}' is ambiguous and matches multiple crops: {candidates_str}. "
                "Please specify or select the intended crop to proceed."
            )
            speech = f"Your query matches {len(resolution.candidates)} crops. Please specify the crop."

        return InteractionResult(
            intent="crop_resolution",
            language=language,
            resolution_status=ResolutionStatus.AMBIGUOUS,
            resolved_crop=None,
            candidates=resolution.candidates,
            response_text=resp,
            speech_text=speech,
            limitations=["Ambiguous crop identification requires explicit user confirmation."],
            sources=["TerraPulse C7 Model Registry"],
        )

    def _handle_unknown(self, query: str, language: LocaleType) -> InteractionResult:
        if language == "kn":
            resp = (
                "ಟೆರ್ರಾಪಲ್ಸ್ ಮಣ್ಣಿನ ತೇವಾಂಶ, ಬೆಳೆ-ನೀರಿನ ಸಮತೋಲನ ಮತ್ತು ಹವಾಮಾನ ಒತ್ತಡದ ವಿಶ್ಲೇಷಣೆಯನ್ನು ಬೆಂಬಲಿಸುತ್ತದೆ. "
                "ನಿಮ್ಮ ಬೆಳೆಯ ಹೆಸರು (ಉದಾ: ಅರಿಶಿನ, ರಾಗಿ, ಮೆಕ್ಕೆಜೋಳ) ಅಥವಾ ನೀರಿನ ಅಗತ್ಯತೆಯ ಕುರಿತು ಪ್ರಶ್ನಿಸಿ."
            )
            speech = "ಟೆರ್ರಾಪಲ್ಸ್ ಬೆಳೆ-ನೀರಿನ ಸಮತೋಲನವನ್ನು ಬೆಂಬಲಿಸುತ್ತದೆ. ನಿಮ್ಮ ಬೆಳೆಯ ಹೆಸರನ್ನು ನಮೂದಿಸಿ."
        elif language == "hi":
            resp = (
                "टेरापल्स मिट्टी की नमी, फसल-जल संतुलन और मौसमी तनाव विश्लेषण का समर्थन करता है। "
                "अपनी फसल का नाम (जैसे हल्दी, रागी, मक्का) या सिंचाई संबंधी प्रश्न पूछें।"
            )
            speech = "टेरापल्स फसल-जल संतुलन का समर्थन करता है। अपनी फसल का नाम बताएं।"
        else:
            resp = (
                "TerraPulse provides evidence-grounded crop water balance, root-zone moisture, and weather stress analysis. "
                "You can specify your crop (e.g. Turmeric, Ragi, Maize) or ask about crop water requirements."
            )
            speech = "TerraPulse provides crop water balance analysis. You can ask about your crop or water requirements."

        return InteractionResult(
            intent="unknown_or_unsupported",
            language=language,
            resolution_status=ResolutionStatus.NOT_FOUND,
            resolved_crop=None,
            candidates=[],
            response_text=resp,
            speech_text=speech,
            limitations=["General query outside recognized crop water or capability categories."],
            sources=["TerraPulse Agricultural Intelligence"],
        )
