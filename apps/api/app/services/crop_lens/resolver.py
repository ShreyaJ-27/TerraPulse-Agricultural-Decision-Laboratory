from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.contracts import C7ModelCapability
from app.services.crop_lens.registry import CROP_REGISTRY, CropRecord


class ResolutionStatus(StrEnum):
    EXACT_MATCH = "exact_match"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    UNSUPPORTED_OFF_CATALOGUE = "unsupported_off_catalogue"


@dataclass(frozen=True)
class CandidateMatch:
    crop_id: UUID
    canonical_name: str
    scientific_name: str
    matched_alias: str
    match_type: str  # "canonical", "scientific", "alias", "partial"


@dataclass(frozen=True)
class ResolutionResult:
    status: ResolutionStatus
    query: str
    crop: CropRecord | None
    capability: C7ModelCapability | None
    candidates: list[CandidateMatch]
    message: str


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", " ", cleaned)


def _matches_partial(query_norm: str, text_norm: str) -> bool:
    """Check for bounded word match or prefix match to prevent false positives."""
    if len(query_norm) < 3:
        return bool(re.search(r"\b" + re.escape(query_norm) + r"\b", text_norm))
    if re.search(r"\b" + re.escape(query_norm), text_norm):
        return True
    words = query_norm.split()
    return len(words) > 1 and all(bool(re.search(r"\b" + re.escape(w), text_norm)) for w in words)


class CropLensResolver:
    """Resolves farmer or scientific crop queries with strict ambiguity protection."""

    def __init__(self, registry: list[CropRecord] | None = None) -> None:
        self.registry = registry if registry is not None else CROP_REGISTRY

    def resolve(self, query: str) -> ResolutionResult:
        normalized = _normalize(query)
        if not normalized:
            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                query=query,
                crop=None,
                capability=None,
                candidates=[],
                message="Crop name query cannot be empty.",
            )

        # 1. Exact canonical matches
        exact_canonical: list[tuple[CropRecord, str]] = []
        for crop in self.registry:
            if _normalize(crop.canonical_name) == normalized:
                exact_canonical.append((crop, crop.canonical_name))

        if len(exact_canonical) == 1:
            crop = exact_canonical[0][0]
            return ResolutionResult(
                status=ResolutionStatus.EXACT_MATCH,
                query=query,
                crop=crop,
                capability=crop.to_c7_capability(),
                candidates=[
                    CandidateMatch(
                        crop_id=crop.crop_id,
                        canonical_name=crop.canonical_name,
                        scientific_name=crop.scientific_name,
                        matched_alias=exact_canonical[0][1],
                        match_type="canonical",
                    )
                ],
                message=f"Resolved directly to {crop.canonical_name} ({crop.scientific_name}).",
            )

        # 2. Exact scientific matches
        exact_scientific: list[tuple[CropRecord, str]] = []
        for crop in self.registry:
            if _normalize(crop.scientific_name) == normalized:
                exact_scientific.append((crop, crop.scientific_name))

        if len(exact_scientific) == 1:
            crop = exact_scientific[0][0]
            return ResolutionResult(
                status=ResolutionStatus.EXACT_MATCH,
                query=query,
                crop=crop,
                capability=crop.to_c7_capability(),
                candidates=[
                    CandidateMatch(
                        crop_id=crop.crop_id,
                        canonical_name=crop.canonical_name,
                        scientific_name=crop.scientific_name,
                        matched_alias=exact_scientific[0][1],
                        match_type="scientific",
                    )
                ],
                message=f"Resolved by scientific name to {crop.canonical_name} ({crop.scientific_name}).",
            )

        # 3. Exact alias matches
        exact_aliases: list[tuple[CropRecord, str]] = []
        for crop in self.registry:
            for alias in crop.aliases:
                if _normalize(alias) == normalized:
                    exact_aliases.append((crop, alias))
                    break

        if len(exact_aliases) == 1:
            crop = exact_aliases[0][0]
            return ResolutionResult(
                status=ResolutionStatus.EXACT_MATCH,
                query=query,
                crop=crop,
                capability=crop.to_c7_capability(),
                candidates=[
                    CandidateMatch(
                        crop_id=crop.crop_id,
                        canonical_name=crop.canonical_name,
                        scientific_name=crop.scientific_name,
                        matched_alias=exact_aliases[0][1],
                        match_type="alias",
                    )
                ],
                message=f"Resolved alias '{exact_aliases[0][1]}' to {crop.canonical_name} ({crop.scientific_name}).",
            )
        elif len(exact_aliases) > 1:
            # An alias mapped to more than one crop -> must require confirmation!
            candidates = [
                CandidateMatch(
                    crop_id=c.crop_id,
                    canonical_name=c.canonical_name,
                    scientific_name=c.scientific_name,
                    matched_alias=alias,
                    match_type="alias",
                )
                for c, alias in exact_aliases
            ]
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                query=query,
                crop=None,
                capability=None,
                candidates=candidates,
                message=f"Query '{query}' is ambiguous and matches {len(candidates)} distinct crops. Confirmation required.",
            )

        # 4. Word-bounded token or prefix partial matches across names and aliases
        partial_matches: dict[UUID, CandidateMatch] = {}
        for crop in self.registry:
            canonical_norm = _normalize(crop.canonical_name)
            scientific_norm = _normalize(crop.scientific_name)

            if _matches_partial(normalized, canonical_norm):
                partial_matches[crop.crop_id] = CandidateMatch(
                    crop_id=crop.crop_id,
                    canonical_name=crop.canonical_name,
                    scientific_name=crop.scientific_name,
                    matched_alias=crop.canonical_name,
                    match_type="partial",
                )
                continue
            if _matches_partial(normalized, scientific_norm):
                partial_matches[crop.crop_id] = CandidateMatch(
                    crop_id=crop.crop_id,
                    canonical_name=crop.canonical_name,
                    scientific_name=crop.scientific_name,
                    matched_alias=crop.scientific_name,
                    match_type="partial",
                )
                continue
            for alias in crop.aliases:
                alias_norm = _normalize(alias)
                if _matches_partial(normalized, alias_norm):
                    partial_matches[crop.crop_id] = CandidateMatch(
                        crop_id=crop.crop_id,
                        canonical_name=crop.canonical_name,
                        scientific_name=crop.scientific_name,
                        matched_alias=alias,
                        match_type="partial",
                    )
                    break

        candidate_list = list(partial_matches.values())
        if len(candidate_list) == 1:
            # A single partial match
            match = candidate_list[0]
            matched_crop = next(c for c in self.registry if c.crop_id == match.crop_id)
            return ResolutionResult(
                status=ResolutionStatus.EXACT_MATCH,
                query=query,
                crop=matched_crop,
                capability=matched_crop.to_c7_capability(),
                candidates=candidate_list,
                message=f"Matched to {matched_crop.canonical_name} via '{match.matched_alias}'.",
            )
        elif len(candidate_list) > 1:
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                query=query,
                crop=None,
                capability=None,
                candidates=candidate_list,
                message=f"Query '{query}' matches {len(candidate_list)} candidate crops. Please select one to confirm.",
            )

        return ResolutionResult(
            status=ResolutionStatus.NOT_FOUND,
            query=query,
            crop=None,
            capability=None,
            candidates=[],
            message=f"No matching crop found in catalogue for '{query}'.",
        )

    def create_unsupported_capability(
        self, query: str, scientific_name: str | None = None
    ) -> C7ModelCapability:
        """Explicitly build an uncalibrated identity/ecology-only C7 contract for an off-catalogue crop."""
        stable_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"terrapulse.crop.{_normalize(query)}")
        clean_name = query.strip()
        accepted_names = [clean_name] if clean_name else []
        return C7ModelCapability(
            contractVersion="1.0",
            cropId=stable_id,
            acceptedCropNames=accepted_names,
            scientificName=scientific_name.strip() if scientific_name else None,
            selectedEngine="identity/ecology-only",
            engineVersion="1.0",
            supportedOutputs=[],
            modelParameters={},
            parameterSources=[],
            parameterVersions=[],
            knownLimitations=[
                "Crop is not calibrated in TerraPulse simulation engines (AquaCrop or FAO-56).",
                "Quantitative yield, root-zone water balance, and stress simulations are strictly unsupported.",
                "Taxonomic identity and ecological reference information only.",
            ],
            provenanceReferences=[],
        )

