"""Bind trusted server-side Crop Lens results to Developer A profiles."""
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from .capability import AQUA_PROFILE, CapabilityRegistry, turmeric_profile
from .contracts import CropKc, fail, nonempty
from .fao56 import run_fao
from .repository_contracts import RepositoryFaoInput, fao_input_from_c1_v1

TURMERIC_ID = UUID("00000000-0000-0000-0000-000000000003")
WHEAT_ID = UUID("00000000-0000-0000-0000-000000000020")
BINDING_VERSION = "dev-a-crop-binding-1"


@dataclass(frozen=True)
class CropBinding:
    crop_id: UUID
    catalogue_scientific_name: str
    catalogue_engine: str
    profile: CropKc
    version: str = BINDING_VERSION


class CropBindingService:
    """Wire with C's resolver.resolve and get_crop_by_id at server startup.

    The resolver and lookup are trusted dependencies, never request fields.
    Requests supply a query and, when needed, a confirmed candidate UUID.
    A C7 capability payload is not accepted from the client.
    """

    def __init__(self, *, resolve: Callable, get_crop_by_id: Callable):
        self._resolve = resolve
        self._get_crop_by_id = get_crop_by_id

    def bind_fao(self, query: str, *, confirmed_crop_id: str | None = None,
                 turmeric_mapping: str | None = None) -> CropBinding:
        result = self._resolve(nonempty(query, "crop query"))
        confirmed = None
        if confirmed_crop_id is not None:
            try:
                confirmed = UUID(str(confirmed_crop_id))
            except ValueError:
                fail("INVALID_CROP_CONFIRMATION", "confirmation must be a canonical crop UUID")

        if result.status == "ambiguous":
            candidates = {candidate.crop_id for candidate in result.candidates}
            if confirmed is None:
                fail("CROP_CONFIRMATION_REQUIRED", "select a candidate from Crop Lens")
            if confirmed not in candidates:
                fail("INVALID_CROP_CONFIRMATION", "confirmed crop was not a candidate for this query")
            crop_id = confirmed
        elif result.status == "exact_match" and result.crop is not None:
            crop_id = result.crop.crop_id
            if confirmed is not None and confirmed != crop_id:
                fail("INVALID_CROP_CONFIRMATION", "confirmation conflicts with the resolved crop")
        else:
            fail("CROP_IDENTITY_UNRESOLVED", "Crop Lens did not resolve a curated crop")

        record = self._get_crop_by_id(crop_id)
        if record is None or record.crop_id != crop_id:
            fail("CROP_CATALOGUE_MISMATCH", "resolved UUID is absent from the authoritative catalogue")
        capability = record.to_c7_capability()
        if (capability.crop_id != crop_id
            or capability.scientific_name != record.scientific_name
            or capability.selected_engine != record.selected_engine):
            fail("CROP_CATALOGUE_MISMATCH", "C7 does not match the canonical catalogue record")

        name, engine = capability.scientific_name, capability.selected_engine
        if engine == "identity/ecology-only":
            fail("CROP_IDENTITY_ONLY", "catalogue identity is available without numerical simulation")
        if crop_id == WHEAT_ID:
            if name != "Triticum aestivum":
                fail("CROP_CATALOGUE_MISMATCH", "wheat UUID no longer identifies Triticum aestivum")
            if engine != "AquaCrop":
                fail("CROP_ENGINE_MISMATCH",
                     f"catalogue wheat declares {engine}; Developer A only verifies {AQUA_PROFILE['parameterVersion']}")
            fail("CROP_EXAMPLE_ONLY", "the pinned Tunis wheat example cannot drive a C1 farm run")
        if crop_id != TURMERIC_ID:
            fail("UNSUPPORTED_CROP_CAPABILITY", "no verified Developer A farm profile for this crop UUID")
        if name != "Curcuma longa":
            fail("CROP_CATALOGUE_MISMATCH", "turmeric UUID no longer identifies Curcuma longa")
        if engine != "FAO-56":
            fail("CROP_ENGINE_MISMATCH", "the registered turmeric profile requires FAO-56")

        if turmeric_mapping is None:
            fail("CROP_MAPPING_REQUIRED", "explicitly select a provisional turmeric stage mapping A/B/C")
        if not isinstance(turmeric_mapping, str):
            fail("UNSUPPORTED_MAPPING", "turmeric mappings: A/B/C provisional only")
        profile = turmeric_profile(turmeric_mapping)
        CapabilityRegistry().require_fao(profile)
        return CropBinding(crop_id, name, engine, profile)

    def prepare_fao(self, c1, *, query, confirmed_crop_id=None, turmeric_mapping=None,
                    **context) -> tuple[CropBinding, RepositoryFaoInput]:
        """Gate the repository C1 adapter before preparing a scientific run."""
        binding = self.bind_fao(query, confirmed_crop_id=confirmed_crop_id,
                                turmeric_mapping=turmeric_mapping)
        if "crop" in context or "capability" in context or "capabilities" in context:
            fail("CLIENT_SCIENCE_PROFILE", "the crop binding supplies the scientific profile")
        return binding, fao_input_from_c1_v1(c1, crop=binding.profile, **context)

    def run_fao(self, c1, *, requested_outputs=(), **context) -> dict:
        """Run with the current trusted resolver and retain the canonical ID."""
        binding, inputs = self.prepare_fao(c1, **context)
        result = run_fao(inputs.request, requested_outputs=requested_outputs)
        result["cropBinding"] = {
            "version":binding.version,
            "cropId":str(binding.crop_id),
            "catalogueScientificName":binding.catalogue_scientific_name,
            "catalogueEngine":binding.catalogue_engine,
            "parameterVersion":binding.profile.parameter_version,
            "parameterHash":result["capability"]["parameterHash"],
        }
        return result
