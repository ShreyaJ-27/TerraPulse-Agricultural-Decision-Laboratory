from __future__ import annotations

import pytest
from app.services.crop_lens.interaction import BoundedInteractionService
from app.services.crop_lens.registry import CROP_REGISTRY
from app.services.crop_lens.resolver import (
    CropLensResolver,
    ResolutionStatus,
    _normalize,
)


@pytest.fixture
def resolver() -> CropLensResolver:
    return CropLensResolver(CROP_REGISTRY)


@pytest.fixture
def interaction_service(resolver: CropLensResolver) -> BoundedInteractionService:
    return BoundedInteractionService(resolver)


# -----------------------------------------------------------------------------
# 1. Indic Script Unicode Normalization & Matra Preservation Tests
# -----------------------------------------------------------------------------
def test_unicode_nfc_and_matra_preservation():
    # Combining vowel marks and viramas must NOT be stripped by normalizer
    assert _normalize("ಅರಿಶಿನ") == "ಅರಿಶಿನ"
    assert _normalize("हल्दी") == "हल्दी"
    assert _normalize("गेहूं") == "गेहूं"
    assert _normalize("ರಾಗಿ") == "ರಾಗಿ"
    assert _normalize("ಮೆಕ್ಕೆಜೋಳ") == "ಮೆಕ್ಕೆಜೋಳ"
    assert _normalize("ಕಡಲೆ") == "ಕಡಲೆ"
    assert _normalize("सज्जे") == "सज्जे"
    assert _normalize("Turmeric (Haldi)!") == "turmeric haldi"


# -----------------------------------------------------------------------------
# 2. Kannada Script Resolution Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query,expected_canonical",
    [
        ("ಅರಿಶಿನ", "Turmeric"),
        ("ಅರಶಿಣ", "Turmeric"),
        ("ರಾಗಿ", "Finger Millet"),
        ("ಸಜ್ಜೆ", "Pearl Millet"),
        ("ನವಣೆ", "Foxtail Millet"),
        ("ಮೆಕ್ಕೆಜೋಳ", "Maize"),
        ("ಮುಸುಕಿನ ಜೋಳ", "Maize"),
        ("ಗೋಧಿ", "Wheat"),
        ("ಕಡಲೆ", "Chickpea (Bengal Gram)"),
        ("ಕಡಲೆ ಕಾಳು", "Chickpea (Bengal Gram)"),
        ("ಉದ್ದು", "Black Gram (Urad)"),
        ("ಉದ್ದಿನ ಬೇಳೆ", "Black Gram (Urad)"),
        ("ಹತ್ತಿ", "Upland Cotton"),
    ],
)
def test_kannada_crop_resolution(resolver: CropLensResolver, query: str, expected_canonical: str):
    res = resolver.resolve(query)
    assert res.status == ResolutionStatus.EXACT_MATCH
    assert res.crop is not None
    assert res.crop.canonical_name == expected_canonical
    assert res.capability is not None
    assert res.capability.crop_id == res.crop.crop_id


# -----------------------------------------------------------------------------
# 3. Hindi Script Resolution Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query,expected_canonical",
    [
        ("हल्दी", "Turmeric"),
        ("हरदी", "Turmeric"),
        ("गेहूं", "Wheat"),
        ("गेंहू", "Wheat"),
        ("मक्का", "Maize"),
        ("मकई", "Maize"),
        ("भुट्टा", "Maize"),
        ("बाजरा", "Pearl Millet"),
        ("मंडुआ", "Finger Millet"),
        ("कंगनी", "Foxtail Millet"),
        ("चना", "Chickpea (Bengal Gram)"),
        ("काला चना", "Chickpea (Bengal Gram)"),
        ("छोला", "Chickpea (Bengal Gram)"),
        ("उड़द", "Black Gram (Urad)"),
        ("उरद", "Black Gram (Urad)"),
        ("कपास", "Upland Cotton"),
        ("रुई", "Upland Cotton"),
    ],
)
def test_hindi_crop_resolution(resolver: CropLensResolver, query: str, expected_canonical: str):
    res = resolver.resolve(query)
    assert res.status == ResolutionStatus.EXACT_MATCH
    assert res.crop is not None
    assert res.crop.canonical_name == expected_canonical


# -----------------------------------------------------------------------------
# 4. Phrase and Natural Sentence Matching Tests
# -----------------------------------------------------------------------------
def test_natural_sentence_crop_resolution(resolver: CropLensResolver):
    # Kannada sentence
    res_kn = resolver.resolve("ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ")
    assert res_kn.status == ResolutionStatus.EXACT_MATCH
    assert res_kn.crop is not None
    assert res_kn.crop.canonical_name == "Turmeric"

    # Hindi sentence
    res_hi = resolver.resolve("मेरी फसल हल्दी है")
    assert res_hi.status == ResolutionStatus.EXACT_MATCH
    assert res_hi.crop is not None
    assert res_hi.crop.canonical_name == "Turmeric"

    # English sentence
    res_en = resolver.resolve("I grow wheat on my farm")
    assert res_en.status == ResolutionStatus.EXACT_MATCH
    assert res_en.crop is not None
    assert res_en.crop.canonical_name == "Wheat"


# -----------------------------------------------------------------------------
# 5. Ambiguity Handling Across Languages
# -----------------------------------------------------------------------------
def test_ambiguity_never_guesses(resolver: CropLensResolver):
    # English ambiguous categories
    res_millet = resolver.resolve("millet")
    assert res_millet.status == ResolutionStatus.AMBIGUOUS
    assert len(res_millet.candidates) >= 3
    assert res_millet.crop is None

    res_gram = resolver.resolve("gram")
    assert res_gram.status == ResolutionStatus.AMBIGUOUS
    assert len(res_gram.candidates) >= 2
    assert res_gram.crop is None

    # Kannada ambiguous category: ಸಿರಿಧಾನ್ಯ (Millets)
    res_kn_millet = resolver.resolve("ಸಿರಿಧಾನ್ಯ")
    assert res_kn_millet.status == ResolutionStatus.AMBIGUOUS
    assert len(res_kn_millet.candidates) >= 3
    assert any("Finger Millet" in c.canonical_name for c in res_kn_millet.candidates)

    # Hindi ambiguous category: दाल (Pulses/Gram)
    res_hi_pulse = resolver.resolve("दाल")
    assert res_hi_pulse.status == ResolutionStatus.AMBIGUOUS
    assert len(res_hi_pulse.candidates) >= 2


# -----------------------------------------------------------------------------
# 6. Bounded Interaction Service Intent & Guardrail Tests
# -----------------------------------------------------------------------------
def test_interaction_crop_capability_fao56_turmeric(interaction_service: BoundedInteractionService):
    # English inquiry about turmeric yield
    res_en = interaction_service.interact("I grow turmeric. Can you predict yield?", "en")
    assert res_en.intent == "crop_capability"
    assert res_en.language == "en"
    assert res_en.resolved_crop is not None
    assert res_en.resolved_crop.canonical_name == "Turmeric"
    assert "FAO-56" in res_en.response_text
    assert "yield prediction is explicitly not supported" in res_en.response_text or "does not produce calibrated yield" in res_en.response_text
    assert not res_en.escalation_required

    # Kannada inquiry
    res_kn = interaction_service.interact("ಅರಿಶಿನ ಬೆಳೆಗೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಇದೆಯೇ?", "kn")
    assert res_kn.intent == "crop_capability"
    assert res_kn.language == "kn"
    assert res_kn.resolved_crop is not None
    assert "FAO-56" in res_kn.response_text
    assert "ಇಳುವರಿ" in res_kn.response_text
    assert "ಅರಿಶಿನ" in res_kn.response_text
    assert "Turmeric" not in res_kn.response_text

    # Hindi inquiry
    res_hi = interaction_service.interact("क्या हल्दी की उपज का अनुमान मिलेगा?", "hi")
    assert res_hi.intent == "crop_capability"
    assert res_hi.language == "hi"
    assert res_hi.resolved_crop is not None
    assert "FAO-56" in res_hi.response_text
    assert "उपज" in res_hi.response_text
    assert "हल्दी" in res_hi.response_text
    assert "Turmeric" not in res_hi.response_text


def test_crop_resolution_localizes_supported_outputs_and_limitations(
    interaction_service: BoundedInteractionService,
):
    res_kn = interaction_service.interact("ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ", "kn")
    assert res_kn.intent == "crop_resolution"
    assert "ವಾಸ್ತವಿಕ ವಾಷ್ಪೋತ್ಸರ್ಜನೆ" in res_kn.response_text
    assert "ನೀರಿನ ಒತ್ತಡ" in res_kn.response_text
    assert "ನೀರಾವರಿ" in res_kn.response_text
    assert "actualEvapotranspiration" not in res_kn.response_text
    assert "No yield output" not in res_kn.limitations
    assert "ಇಳುವರಿ" in res_kn.limitations[0]

    res_hi = interaction_service.interact("मेरी फसल हल्दी", "hi")
    assert res_hi.intent == "crop_resolution"
    assert "वास्तविक वाष्पोत्सर्जन" in res_hi.response_text
    assert "जल तनाव" in res_hi.response_text
    assert "सिंचाई" in res_hi.response_text
    assert "No yield output" not in res_hi.limitations
    assert "उपज" in res_hi.limitations[0]


def test_interaction_crop_capability_aquacrop_maize(interaction_service: BoundedInteractionService):
    res = interaction_service.interact("Can you simulate maize yield?", "en")
    assert res.intent == "crop_capability"
    assert res.resolved_crop is not None
    assert res.resolved_crop.canonical_name == "Maize"
    assert "AquaCrop" in res.response_text
    assert "Farm-scale simulation is unavailable" in res.response_text


def test_interaction_water_guidance_finger_millet(interaction_service: BoundedInteractionService):
    # English: How much water does ragi need?
    res_en = interaction_service.interact("How much water does ragi need?", "en")
    assert res_en.intent == "water_guidance"
    assert res_en.resolved_crop is not None
    assert res_en.resolved_crop.canonical_name == "Finger Millet"
    assert "0.35" in res_en.response_text  # kcIni
    assert "1.1" in res_en.response_text   # kcMid
    assert "0.3" in res_en.response_text   # kcEnd
    assert "FAO-56" in res_en.sources[0]

    # Kannada: ರಾಗಿ ಬೆಳೆಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?
    res_kn = interaction_service.interact("ರಾಗಿ ಬೆಳೆಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?", "kn")
    assert res_kn.intent == "water_guidance"
    assert res_kn.language == "kn"
    assert res_kn.resolved_crop is not None
    assert "1.1" in res_kn.response_text


def test_interaction_plant_pathology_escalation(interaction_service: BoundedInteractionService):
    # English
    res_en = interaction_service.interact("My crop has brown spots and fungal rot", "en")
    assert res_en.intent == "escalation_plant_pathology"
    assert res_en.escalation_required is True
    assert "Krishi Vigyan Kendra" in res_en.response_text

    # Kannada
    res_kn = interaction_service.interact("ಬೆಳೆಯಲ್ಲಿ ಕೀಟ ಮತ್ತು ರೋಗ ಬಾಧೆ ಹೆಚ್ಚಾಗಿದೆ", "kn")
    assert res_kn.intent == "escalation_plant_pathology"
    assert res_kn.escalation_required is True
    assert "ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ" in res_kn.response_text

    # Hindi
    res_hi = interaction_service.interact("फसल में कीड़े लग गए हैं क्या करें", "hi")
    assert res_hi.intent == "escalation_plant_pathology"
    assert res_hi.escalation_required is True
    assert "कृषि विज्ञान केंद्र" in res_hi.response_text


def test_interaction_market_pricing_refusal(interaction_service: BoundedInteractionService):
    # English
    res_en = interaction_service.interact("What is today's turmeric market price?", "en")
    assert res_en.intent == "refusal_market_pricing"
    assert res_en.escalation_required is False
    assert "does not provide commodity market prices" in res_en.response_text
    assert "Agmarknet" in res_en.response_text

    # Kannada
    res_kn = interaction_service.interact("ಅರಿಶಿನ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಎಷ್ಟು?", "kn")
    assert res_kn.intent == "refusal_market_pricing"
    assert "ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು" in res_kn.response_text

    # Hindi
    res_hi = interaction_service.interact("मंडी में हल्दी का क्या भाव है?", "hi")
    assert res_hi.intent == "refusal_market_pricing"
    assert "भाव या मूल्य पूर्वानुमान प्रदान नहीं करता" in res_hi.response_text


def test_interaction_ambiguous_crop_prompts_clarification(interaction_service: BoundedInteractionService):
    res = interaction_service.interact("How should I grow millet?", "en")
    assert res.intent == "crop_resolution" or res.intent == "water_guidance"
    assert res.resolution_status == ResolutionStatus.AMBIGUOUS
    assert len(res.candidates) >= 3
    assert "ambiguous" in res.response_text.lower()


def test_resolver_prevents_false_substring_matches(resolver: CropLensResolver):
    """Ensure partial matching does not produce false crop identities like 'heat' -> 'Wheat' or 'ton' -> 'Cotton'."""
    res_heat = resolver.resolve("heat")
    assert res_heat.status == ResolutionStatus.NOT_FOUND
    assert res_heat.crop is None

    res_ton = resolver.resolve("ton")
    assert res_ton.status == ResolutionStatus.NOT_FOUND
    assert res_ton.crop is None

    res_wheat = resolver.resolve("wheat")
    assert res_wheat.status == ResolutionStatus.EXACT_MATCH
    assert res_wheat.crop is not None
    assert res_wheat.crop.canonical_name == "Wheat"

    res_cotton = resolver.resolve("cotton")
    assert res_cotton.status == ResolutionStatus.EXACT_MATCH
    assert res_cotton.crop is not None
    assert res_cotton.crop.canonical_name == "Upland Cotton"


def test_kannada_haladi_ambiguity_and_pathology(
    resolver: CropLensResolver, interaction_service: BoundedInteractionService
):
    """Review Kannada 'ಹಳದಿ': ensure it requires disambiguation when queried as crop, and routes yellow leaves to pathology."""
    # 1. Bare 'ಹಳದಿ' as crop name must be ambiguous
    res_crop = resolver.resolve("ಹಳದಿ")
    assert res_crop.status == ResolutionStatus.AMBIGUOUS
    assert any(c.canonical_name == "Turmeric" for c in res_crop.candidates)

    # 2. Bare 'ಹಳದಿ' in interaction prompts explicit clarification
    res_interact = interaction_service.interact("ಹಳದಿ", "kn")
    assert res_interact.intent == "crop_resolution"
    assert res_interact.resolution_status == ResolutionStatus.AMBIGUOUS
    assert "ಅರಿಶಿನ" in res_interact.response_text

    # 3. 'ಹಳದಿ ಎಲೆ' (yellow leaf symptom) must escalate to pathology
    res_path = interaction_service.interact("ನನ್ನ ಬೆಳೆಯಲ್ಲಿ ಹಳದಿ ಎಲೆ ಕಾಣಿಸಿದೆ", "kn")
    assert res_path.intent == "escalation_plant_pathology"
    assert res_path.escalation_required is True


def test_pathology_keyword_prefix_no_false_escalation(interaction_service: BoundedInteractionService):
    """Ensure substring 'rot' inside innocent words like 'carrot' does not falsely escalate to plant pathology."""
    res_carrot = interaction_service.interact("can I grow carrot", "en")
    assert res_carrot.intent != "escalation_plant_pathology"

    res_rot = interaction_service.interact("the roots are rotting with fungus", "en")
    assert res_rot.intent == "escalation_plant_pathology"
    assert res_rot.escalation_required is True


def test_cotton_kannada_aliases(resolver: CropLensResolver):
    """Verify clean Kannada aliases for Upland Cotton without script mixing."""
    res_kapas = resolver.resolve("ಕಪಾಸ್")
    assert res_kapas.status == ResolutionStatus.EXACT_MATCH
    assert res_kapas.crop is not None
    assert res_kapas.crop.canonical_name == "Upland Cotton"

    res_kapasu = resolver.resolve("ಕಪಾಸು")
    assert res_kapasu.status == ResolutionStatus.EXACT_MATCH
    assert res_kapasu.crop is not None
    assert res_kapasu.crop.canonical_name == "Upland Cotton"
