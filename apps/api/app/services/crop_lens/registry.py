from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from app.contracts import C7ModelCapability, Provenance


@dataclass(frozen=True)
class ExternalReference:
    source_name: str  # "AGROVOC", "GBIF", "ECOCROP"
    identifier: str
    uri: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class CropRecord:
    crop_id: UUID
    canonical_name: str
    scientific_name: str
    family: str
    aliases: list[str]  # Common, vernacular, spelling variants
    external_references: list[ExternalReference]
    selected_engine: Literal["AquaCrop", "FAO-56", "identity/ecology-only"]
    engine_version: str
    supported_outputs: list[str]
    model_parameters: dict[str, float | str]
    parameter_sources: list[Provenance]
    parameter_versions: list[str]
    known_limitations: list[str]
    provenance_references: list[Provenance] = field(default_factory=list)

    def to_c7_capability(self) -> C7ModelCapability:
        """Export to the authoritative C7ModelCapability contract."""
        return C7ModelCapability(
            contractVersion="1.0",
            cropId=self.crop_id,
            acceptedCropNames=list(self.aliases),
            scientificName=self.scientific_name,
            selectedEngine=self.selected_engine,
            engineVersion=self.engine_version,
            supportedOutputs=list(self.supported_outputs),
            modelParameters=dict(self.model_parameters),
            parameterSources=list(self.parameter_sources),
            parameterVersions=list(self.parameter_versions),
            knownLimitations=list(self.known_limitations),
            provenanceReferences=list(self.provenance_references),
        )


NOW = datetime(2026, 11, 13, 0, 0, 0, tzinfo=UTC)

# Curated crop registry with reliable AGROVOC, GBIF, and ECOCROP references
# Turmeric uses UUID 00000000-0000-0000-0000-000000000003 to align with shared C7 fixture.
CROP_REGISTRY: list[CropRecord] = [
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000003"),
        canonical_name="Turmeric",
        scientific_name="Curcuma longa",
        family="Zingiberaceae",
        aliases=[
            "turmeric",
            "haldi",
            "pasupu",
            "manjal",
            "halad",
            "curcuma longa",
            "curcuma",
            "ಅರಿಶಿನ",
            "ಅರಶಿಣ",
            "हल्दी",
            "हरदी",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_2034",
                uri="http://aims.fao.org/aos/agrovoc/c_2034",
                description="Curcuma longa in FAO AGROVOC Concept Scheme",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2757624",
                uri="https://www.gbif.org/species/2757624",
                description="Curcuma longa L. in GBIF Backbone Taxonomy",
            ),
            ExternalReference(
                source_name="ECOCROP",
                identifier="828",
                uri="https://ecocrop.fao.org/ecocrop/srv/en/cropView?id=828",
                description="Curcuma longa FAO ECOCROP code",
            ),
        ],
        selected_engine="FAO-56",
        engine_version="1.0",
        supported_outputs=["actualEvapotranspiration", "waterStress", "irrigation"],
        model_parameters={"cropCoefficient": "documented externally"},
        parameter_sources=[],
        parameter_versions=["demo-1"],
        known_limitations=["No yield output"],
        provenance_references=[],
    ),
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000010"),
        canonical_name="Maize",
        scientific_name="Zea mays",
        family="Poaceae",
        aliases=[
            "maize",
            "corn",
            "makka",
            "makki",
            "cholam",
            "zea mays",
            "ಮೆಕ್ಕೆಜೋಳ",
            "ಮುಸುಕಿನ ಜೋಳ",
            "मक्का",
            "मकई",
            "भुट्टा",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_8504",
                uri="http://aims.fao.org/aos/agrovoc/c_8504",
                description="Zea mays in FAO AGROVOC Concept Scheme",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="5290052",
                uri="https://www.gbif.org/species/5290052",
                description="Zea mays L. in GBIF Backbone Taxonomy",
            ),
            ExternalReference(
                source_name="ECOCROP",
                identifier="2175",
                uri="https://ecocrop.fao.org/ecocrop/srv/en/cropView?id=2175",
                description="Zea mays FAO ECOCROP code",
            ),
        ],
        selected_engine="AquaCrop",
        engine_version="3.1.0",
        supported_outputs=[
            "canopyCover",
            "biomass",
            "yield",
            "actualEvapotranspiration",
            "waterStress",
        ],
        model_parameters={"baseTemperatureC": 8.0, "cutoffTemperatureC": 30.0},
        parameter_sources=[
            Provenance(
                sourceId="fao-aquacrop-ospy-maize-default",
                sourceVersion="3.1.0",
                retrievedAt=NOW,
            )
        ],
        parameter_versions=["aquacrop-maize-v1"],
        known_limitations=[
            "Requires verified planting date and irrigation schedule.",
            "Valid only under pest-free baseline assumption.",
        ],
        provenance_references=[
            Provenance(sourceId="agrovoc-c_8512", sourceVersion="2026", retrievedAt=NOW),
            Provenance(sourceId="gbif-5290052", sourceVersion="2026", retrievedAt=NOW),
        ],
    ),
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000020"),
        canonical_name="Wheat",
        scientific_name="Triticum aestivum",
        family="Poaceae",
        aliases=[
            "wheat",
            "gehun",
            "godhumai",
            "kanak",
            "triticum aestivum",
            "ಗೋಧಿ",
            "गेहूं",
            "गेंहू",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_7951",
                uri="http://aims.fao.org/aos/agrovoc/c_7951",
                description="Triticum aestivum in FAO AGROVOC Concept Scheme",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2706391",
                uri="https://www.gbif.org/species/2706391",
                description="Triticum aestivum L. in GBIF Backbone Taxonomy",
            ),
            ExternalReference(
                source_name="ECOCROP",
                identifier="2114",
                uri="https://ecocrop.fao.org/ecocrop/srv/en/cropView?id=2114",
                description="Triticum aestivum FAO ECOCROP code",
            ),
        ],
        selected_engine="FAO-56",
        engine_version="1.0",
        supported_outputs=["actualEvapotranspiration", "waterStress", "irrigation"],
        model_parameters={"kcIni": 0.3, "kcMid": 1.15, "kcEnd": 0.25},
        parameter_sources=[
            Provenance(
                sourceId="fao-56-irrigation-drainage-paper",
                sourceVersion="1998",
                retrievedAt=NOW,
            )
        ],
        parameter_versions=["fao56-wheat-standard"],
        known_limitations=[
            "No calibrated dry-matter yield or protein estimation.",
            "Water balance only.",
        ],
        provenance_references=[
            Provenance(sourceId="agrovoc-c_7951", sourceVersion="2026", retrievedAt=NOW),
            Provenance(sourceId="gbif-2705886", sourceVersion="2026", retrievedAt=NOW),
        ],
    ),
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000060"),
        canonical_name="Okra",
        scientific_name="Abelmoschus esculentus",
        family="Malvaceae",
        aliases=["okra", "bhindi", "bhendi", "lady's finger", "abelmoschus esculentus"],
        external_references=[],
        selected_engine="identity/ecology-only",
        engine_version="1.0",
        supported_outputs=[],
        model_parameters={},
        parameter_sources=[],
        parameter_versions=[],
        known_limitations=[
            "Crop identity is supported, but no quantitative AquaCrop or FAO-56 calibration is available.",
            "Scientific simulation must not be inferred from this identity-only record.",
        ],
        provenance_references=[],
    ),
    # Crops for ambiguity demonstration (Millets)
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000031"),
        canonical_name="Pearl Millet",
        scientific_name="Pennisetum glaucum",
        family="Poaceae",
        aliases=[
            "pearl millet",
            "bajra",
            "sajje",
            "kambu",
            "pennisetum glaucum",
            "ಸಜ್ಜೆ",
            "बाजरा",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_5682",
                uri="http://aims.fao.org/aos/agrovoc/c_5682",
                description="Pennisetum glaucum",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2706141",
                uri="https://www.gbif.org/species/2706141",
                description="Pennisetum glaucum (L.) R.Br.",
            ),
        ],
        selected_engine="FAO-56",
        engine_version="1.0",
        supported_outputs=["actualEvapotranspiration", "waterStress"],
        model_parameters={"kcIni": 0.35, "kcMid": 1.0, "kcEnd": 0.3},
        parameter_sources=[
            Provenance(sourceId="fao-56-millet", sourceVersion="1998", retrievedAt=NOW)
        ],
        parameter_versions=["fao56-pearl-millet-v1"],
        known_limitations=["Root-zone water depletion only; yield estimation not supported."],
        provenance_references=[],
    ),
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000032"),
        canonical_name="Finger Millet",
        scientific_name="Eleusine coracana",
        family="Poaceae",
        aliases=[
            "finger millet",
            "ragi",
            "mandua",
            "nachani",
            "eleusine coracana",
            "ರಾಗಿ",
            "मंडुआ",
            "रागी",
            "नाचनी",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_2522",
                uri="http://aims.fao.org/aos/agrovoc/c_2522",
                description="Eleusine coracana",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2705957",
                uri="https://www.gbif.org/species/2705957",
                description="Eleusine coracana (L.) Gaertn.",
            ),
        ],
        selected_engine="FAO-56",
        engine_version="1.0",
        supported_outputs=["actualEvapotranspiration", "waterStress"],
        model_parameters={"kcIni": 0.35, "kcMid": 1.1, "kcEnd": 0.3},
        parameter_sources=[
            Provenance(sourceId="fao-56-ragi", sourceVersion="1998", retrievedAt=NOW)
        ],
        parameter_versions=["fao56-finger-millet-v1"],
        known_limitations=["Yield output is not supported."],
        provenance_references=[],
    ),
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000033"),
        canonical_name="Foxtail Millet",
        scientific_name="Setaria italica",
        family="Poaceae",
        aliases=[
            "foxtail millet",
            "kangni",
            "tenai",
            "korra",
            "setaria italica",
            "ನವಣೆ",
            "ಕಂಗನಿ",
            "कंगनी",
            "काकुन",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_7030",
                uri="http://aims.fao.org/aos/agrovoc/c_7030",
                description="Setaria italica",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2705299",
                uri="https://www.gbif.org/species/2705299",
                description="Setaria italica (L.) P.Beauv.",
            ),
        ],
        selected_engine="identity/ecology-only",
        engine_version="1.0",
        supported_outputs=[],
        model_parameters={},
        parameter_sources=[],
        parameter_versions=[],
        known_limitations=["No quantitative AquaCrop or FAO-56 simulation calibrated."],
        provenance_references=[],
    ),
    # Crops for ambiguity demonstration (Gram / Pulses)
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000041"),
        canonical_name="Chickpea (Bengal Gram)",
        scientific_name="Cicer arietinum",
        family="Fabaceae",
        aliases=[
            "chickpea",
            "bengal gram",
            "chana",
            "kala chana",
            "cicer arietinum",
            "ಕಡಲೆ",
            "ಕಡಲೆ ಕಾಳು",
            "चना",
            "काला चना",
            "छोला",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_1583",
                uri="http://aims.fao.org/aos/agrovoc/c_1583",
                description="Cicer arietinum",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2972418",
                uri="https://www.gbif.org/species/2972418",
                description="Cicer arietinum L.",
            ),
        ],
        selected_engine="FAO-56",
        engine_version="1.0",
        supported_outputs=["actualEvapotranspiration", "waterStress"],
        model_parameters={"kcIni": 0.4, "kcMid": 1.0, "kcEnd": 0.35},
        parameter_sources=[
            Provenance(sourceId="fao-56-chickpea", sourceVersion="1998", retrievedAt=NOW)
        ],
        parameter_versions=["fao56-chickpea-v1"],
        known_limitations=["No yield or pod development prediction."],
        provenance_references=[],
    ),
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000042"),
        canonical_name="Black Gram (Urad)",
        scientific_name="Vigna mungo",
        family="Fabaceae",
        aliases=[
            "black gram",
            "urad",
            "mash kalai",
            "vigna mungo",
            "ಉದ್ದು",
            "ಉದ್ದಿನ ಬೇಳೆ",
            "उड़द",
            "उरद",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_8277",
                uri="http://aims.fao.org/aos/agrovoc/c_8277",
                description="Vigna mungo",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="2982594",
                uri="https://www.gbif.org/species/2982594",
                description="Vigna mungo (L.) Hepper",
            ),
        ],
        selected_engine="identity/ecology-only",
        engine_version="1.0",
        supported_outputs=[],
        model_parameters={},
        parameter_sources=[],
        parameter_versions=[],
        known_limitations=["Simulation model not currently calibrated."],
        provenance_references=[],
    ),
    # Cotton: explicitly identity/ecology-only to demonstrate unsupported crop pathway
    CropRecord(
        crop_id=UUID("00000000-0000-0000-0000-000000000050"),
        canonical_name="Upland Cotton",
        scientific_name="Gossypium hirsutum",
        family="Malvaceae",
        aliases=[
            "cotton",
            "kapas",
            "cotton plant",
            "gossypium hirsutum",
            "gossypium",
            "ಹತ್ತಿ",
            "ಕಪಾಸ್",
            "ಕಪಾಸು",
            "कपास",
            "रुई",
        ],
        external_references=[
            ExternalReference(
                source_name="AGROVOC",
                identifier="c_3338",
                uri="http://aims.fao.org/aos/agrovoc/c_3338",
                description="Gossypium hirsutum",
            ),
            ExternalReference(
                source_name="GBIF",
                identifier="3152678",
                uri="https://www.gbif.org/species/3152678",
                description="Gossypium hirsutum L.",
            ),
            ExternalReference(
                source_name="ECOCROP",
                identifier="1161",
                uri="https://ecocrop.fao.org/ecocrop/srv/en/cropView?id=1161",
                description="Gossypium hirsutum FAO ECOCROP profile",
            ),
        ],
        selected_engine="identity/ecology-only",
        engine_version="1.0",
        supported_outputs=[],
        model_parameters={},
        parameter_sources=[],
        parameter_versions=[],
        known_limitations=[
            "Crop not calibrated for quantitative AquaCrop or FAO-56 simulation.",
            "Identity and taxonomic references only. Fabricated yield/growth output is strictly prohibited.",
        ],
        provenance_references=[
            Provenance(sourceId="agrovoc-c_3338", sourceVersion="2026", retrievedAt=NOW),
            Provenance(sourceId="gbif-3152678", sourceVersion="2026", retrievedAt=NOW),
        ],
    ),
]


def get_crop_by_id(crop_id: UUID) -> CropRecord | None:
    for crop in CROP_REGISTRY:
        if crop.crop_id == crop_id:
            return crop
    return None


def list_crops() -> list[CropRecord]:
    return list(CROP_REGISTRY)
