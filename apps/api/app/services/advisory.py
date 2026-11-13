from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from app.services.crop_lens.registry import get_crop_by_id
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

DEMO_REGION_ID = "IN-PB"


class AdvisoryModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class CropIdentity(AdvisoryModel):
    crop_id: UUID
    canonical_name: str
    scientific_name: str
    family: str
    aliases: tuple[str, ...]


class ExtensionSource(AdvisoryModel):
    publisher: str = "Punjab Agricultural University"
    title: str
    edition: str
    published_month: str
    reviewed_on: date = date(2026, 11, 13)
    url: str


class PlantingWindow(AdvisoryModel):
    kind: Literal["typical_regional_window"] = "typical_regional_window"
    operation: Literal["direct_sowing"] = "direct_sowing"
    label: str
    applicability: str
    source_section: str


class CultivationMilestone(AdvisoryModel):
    id: str
    label: str
    definition: str
    source_section: str
    definition_url: str | None = None


class RegionalContext(AdvisoryModel):
    season: Literal["kharif", "rabi"]
    summary: str
    source: ExtensionSource
    planting_window: PlantingWindow
    milestones: tuple[CultivationMilestone, ...]


class AdvisoryCapabilities(AdvisoryModel):
    regional_planting_window: bool
    cultivation_milestones: bool
    numerical_irrigation_advice: Literal[False] = False
    harvest_date_prediction: Literal[False] = False
    yield_prediction: Literal[False] = False
    simulation: Literal[False] = False


class AdvisoryProfile(AdvisoryModel):
    schema_version: Literal["1.0"] = "1.0"
    region_id: str
    status: Literal["regional_context_available", "region_unsupported", "crop_context_unavailable"]
    crop: CropIdentity
    regional_context: RegionalContext | None
    capabilities: AdvisoryCapabilities


MAIZE_PRACTICES = "Maize, Agronomic Practices (printed pp. 30–31)"
MAIZE_DEFINITIONS = "https://agry.purdue.edu/ext/corn/news/timeless/GrainFill.html"
WHEAT_SOWING = "Wheat, Time of Sowing and Sowing Method and Spacing (printed pp. 4–6)"

PUNJAB_CONTEXT = {
    UUID("00000000-0000-0000-0000-000000000010"): RegionalContext(
        season="kharif",
        summary=(
            "Monsoon-season maize. PAU describes earlier establishment for fields prone "
            "to standing water before monsoon rains."
        ),
        source=ExtensionSource(
            title="Package of Practices for Crops of Punjab",
            edition="Kharif 2026",
            published_month="2026-03",
            url="https://pau.edu/content/ccil/pf/pp_kharif.pdf",
        ),
        planting_window=PlantingWindow(
            label="Late May through the end of June",
            applicability=(
                "PAU's main-season maize window. For fields prone to standing water, "
                "the guide describes sowing in late May to early June."
            ),
            source_section=MAIZE_PRACTICES,
        ),
        milestones=(
            CultivationMilestone(
                id="silking",
                label="Silking",
                definition="Silks emerge from the maize ear.",
                source_section=MAIZE_PRACTICES,
                definition_url=MAIZE_DEFINITIONS,
            ),
            CultivationMilestone(
                id="grain_filling",
                label="Grain filling",
                definition="Kernels develop and accumulate dry matter.",
                source_section=MAIZE_PRACTICES,
                definition_url=MAIZE_DEFINITIONS,
            ),
        ),
    ),
    UUID("00000000-0000-0000-0000-000000000020"): RegionalContext(
        season="rabi",
        summary="Winter-season wheat. Sowing guidance varies by variety and field conditions.",
        source=ExtensionSource(
            title="Package of Practices for Crops of Punjab",
            edition="Rabi 2025–26",
            published_month="2025-08",
            url="https://pau.edu/content/ccil/pf/pp_rabi.pdf",
        ),
        planting_window=PlantingWindow(
            label="First half of November",
            applicability=(
                "PAU's general optimum window in this edition. Some long-duration "
                "varieties can be sown from late October. Check variety-specific guidance."
            ),
            source_section=WHEAT_SOWING,
        ),
        milestones=(
            CultivationMilestone(
                id="field_sowing",
                label="Field sowing",
                definition="Wheat seed is placed in the field.",
                source_section=WHEAT_SOWING,
            ),
            CultivationMilestone(
                id="seedling_emergence",
                label="Seedling emergence",
                definition="Wheat shoots become visible above the soil surface.",
                source_section=WHEAT_SOWING,
            ),
        ),
    ),
}


def get_advisory_profile(crop_id: UUID, region_id: str) -> AdvisoryProfile | None:
    crop = get_crop_by_id(crop_id)
    if crop is None:
        return None

    context = PUNJAB_CONTEXT.get(crop_id) if region_id == DEMO_REGION_ID else None
    status = "crop_context_unavailable"
    if region_id != DEMO_REGION_ID:
        status = "region_unsupported"
    elif context is not None:
        status = "regional_context_available"

    return AdvisoryProfile(
        region_id=region_id,
        status=status,
        crop=CropIdentity(
            crop_id=crop.crop_id,
            canonical_name=crop.canonical_name,
            scientific_name=crop.scientific_name,
            family=crop.family,
            aliases=tuple(crop.aliases),
        ),
        regional_context=context,
        capabilities=AdvisoryCapabilities(
            regional_planting_window=context is not None,
            cultivation_milestones=bool(context and context.milestones),
        ),
    )
