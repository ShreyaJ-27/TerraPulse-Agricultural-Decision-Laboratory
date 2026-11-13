from uuid import UUID

import pytest
from app.contracts import C7ModelCapability
from app.services.crop_lens.registry import CROP_REGISTRY, get_crop_by_id, list_crops
from app.services.crop_lens.resolver import (
    CropLensResolver,
    ResolutionStatus,
)


@pytest.fixture
def resolver() -> CropLensResolver:
    return CropLensResolver(CROP_REGISTRY)


def test_registry_contains_curated_crops_with_taxonomic_references():
    crops = list_crops()
    assert len(crops) >= 5

    turmeric = get_crop_by_id(UUID("00000000-0000-0000-0000-000000000003"))
    assert turmeric is not None
    assert turmeric.canonical_name == "Turmeric"
    assert turmeric.scientific_name == "Curcuma longa"

    # Check external taxonomy
    sources = {ref.source_name: ref for ref in turmeric.external_references}
    assert "AGROVOC" in sources
    assert sources["AGROVOC"].identifier == "c_2034"
    assert "GBIF" in sources
    assert sources["GBIF"].identifier == "2757624"
    assert "ECOCROP" in sources
    assert sources["ECOCROP"].identifier == "828"


def test_turmeric_capability_matches_c7_contract(resolver: CropLensResolver):
    result = resolver.resolve("turmeric")
    assert result.status == ResolutionStatus.EXACT_MATCH
    assert result.crop is not None
    assert result.capability is not None

    cap = result.capability
    assert isinstance(cap, C7ModelCapability)
    assert cap.contract_version == "1.0"
    assert cap.crop_id == UUID("00000000-0000-0000-0000-000000000003")
    assert "haldi" in cap.accepted_crop_names
    assert cap.scientific_name == "Curcuma longa"
    assert cap.selected_engine == "FAO-56"
    assert cap.engine_version == "1.0"
    assert "actualEvapotranspiration" in cap.supported_outputs
    assert "irrigation" in cap.supported_outputs
    assert cap.known_limitations == ["No yield output"]


@pytest.mark.parametrize(
    "query,expected_canonical",
    [
        ("haldi", "Turmeric"),
        ("pasupu", "Turmeric"),
        ("manjal", "Turmeric"),
        ("Curcuma longa", "Turmeric"),
        ("curcuma", "Turmeric"),
        ("maize", "Maize"),
        ("corn", "Maize"),
        ("makka", "Maize"),
        ("Zea mays", "Maize"),
        ("wheat", "Wheat"),
        ("gehun", "Wheat"),
        ("Triticum aestivum", "Wheat"),
    ],
)
def test_exact_resolution_by_alias_and_scientific_name(
    resolver: CropLensResolver, query: str, expected_canonical: str
):
    result = resolver.resolve(query)
    assert result.status == ResolutionStatus.EXACT_MATCH
    assert result.crop is not None
    assert result.crop.canonical_name == expected_canonical
    assert result.capability is not None
    assert result.capability.contract_version == "1.0"


def test_ambiguous_crop_requires_user_confirmation(resolver: CropLensResolver):
    # "millet" matches Pearl Millet, Finger Millet, and Foxtail Millet
    result = resolver.resolve("millet")
    assert result.status == ResolutionStatus.AMBIGUOUS
    assert result.crop is None
    assert result.capability is None
    assert len(result.candidates) >= 2

    candidate_names = [c.canonical_name for c in result.candidates]
    assert "Pearl Millet" in candidate_names
    assert "Finger Millet" in candidate_names


def test_ambiguous_gram_requires_confirmation(resolver: CropLensResolver):
    # "gram" matches Bengal Gram (Chickpea) and Black Gram (Urad)
    result = resolver.resolve("gram")
    assert result.status == ResolutionStatus.AMBIGUOUS
    assert result.crop is None
    assert result.capability is None
    assert len(result.candidates) >= 2


def test_unknown_crop_returns_not_found(resolver: CropLensResolver):
    result = resolver.resolve("unobtainium_crop")
    assert result.status == ResolutionStatus.NOT_FOUND
    assert result.crop is None
    assert result.capability is None
    assert len(result.candidates) == 0


def test_explicit_unsupported_crop_produces_valid_c7_contract(resolver: CropLensResolver):
    cap = resolver.create_unsupported_capability("Dragon Fruit", scientific_name="Selenicereus undatus")
    assert isinstance(cap, C7ModelCapability)
    assert cap.contract_version == "1.0"
    assert cap.selected_engine == "identity/ecology-only"
    assert cap.supported_outputs == []
    assert len(cap.known_limitations) > 0
    assert "unsupported" in cap.known_limitations[1].lower()


def test_cotton_unsupported_engine_declaration(resolver: CropLensResolver):
    result = resolver.resolve("cotton")
    assert result.status == ResolutionStatus.EXACT_MATCH
    assert result.capability is not None
    assert result.capability.selected_engine == "identity/ecology-only"
    assert result.capability.supported_outputs == []
    assert len(result.capability.known_limitations) > 0
