from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.contracts import C7ModelCapability
from app.services.crop_lens.registry import CROP_REGISTRY, CropRecord

AMBIGUOUS_CATEGORIES: dict[str, list[str]] = {
    # Millets
    "millet": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "millets": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "ಸಿರಿಧಾನ್ಯ": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "ಸಿರಿಧಾನ್ಯಗಳು": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "ತೃಣಧಾನ್ಯ": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "मिलेट": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "मिल्लेट": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    "मोटा अनाज": ["Pearl Millet", "Finger Millet", "Foxtail Millet"],
    # Gram / Pulses
    "gram": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "grams": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "pulse": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "pulses": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "ಕಾಳು": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "ದಾಲ್": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "ಬೇಳೆ": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "दाल": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    "दलहन": ["Chickpea (Bengal Gram)", "Black Gram (Urad)"],
    # Vernacular ambiguous terms (Kannada "ಹಳದಿ" means yellow, but can colloquially refer to turmeric)
    "ಹಳದಿ": ["Turmeric"],
}


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
    match_type: str  # "canonical", "scientific", "alias", "partial", "phrase_token", "category_ambiguity"


@dataclass(frozen=True)
class ResolutionResult:
    status: ResolutionStatus
    query: str
    crop: CropRecord | None
    capability: C7ModelCapability | None
    candidates: list[CandidateMatch]
    message: str


def _normalize(text: str) -> str:
    """Normalize text into Unicode NFC, preserving letters, combining marks (matras/viramas), numbers, and hyphens."""
    nfc = unicodedata.normalize("NFC", text.strip().lower())
    chars: list[str] = []
    for ch in nfc:
        cat = unicodedata.category(ch)
        if cat.startswith(("L", "M", "N")) or ch in (" ", "\t", "-"):
            chars.append(ch)
    cleaned = "".join(chars)
    return re.sub(r"\s+", " ", cleaned).strip()


def _matches_partial(query_norm: str, text_norm: str) -> bool:
    """Safe Indic-aware prefix and token match without false substring hits (e.g. 'heat' in 'wheat')."""
    q_words = query_norm.split()
    t_words = text_norm.split()
    if not q_words or not t_words:
        return False
    if len(q_words) == 1:
        qw = q_words[0]
        if len(qw) < 3:
            return qw in t_words
        return any(tw.startswith(qw) for tw in t_words)
    return all(any(tw.startswith(qw) for tw in t_words) for qw in q_words)


class CropLensResolver:
    """Resolves farmer or scientific crop queries with strict ambiguity protection and Indic script support."""

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

        # 1. Check known ambiguous category keywords (e.g. "millet", "ಸಿರಿಧಾನ್ಯ", "दाल")
        if normalized in AMBIGUOUS_CATEGORIES:
            target_names = AMBIGUOUS_CATEGORIES[normalized]
            candidates = [
                CandidateMatch(
                    crop_id=c.crop_id,
                    canonical_name=c.canonical_name,
                    scientific_name=c.scientific_name,
                    matched_alias=normalized,
                    match_type="category_ambiguity",
                )
                for c in self.registry
                if c.canonical_name in target_names
            ]
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                query=query,
                crop=None,
                capability=None,
                candidates=candidates,
                message=f"Query '{query}' refers to a crop group and matches {len(candidates)} distinct crops. Confirmation required.",
            )

        # 2. Exact canonical matches
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

        # 3. Exact scientific matches
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

        # 4. Exact alias matches
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

        # 5. Phrase and sentence token extraction (e.g. "ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ", "मेरी फसल हल्दी है", "I grow wheat")
        q_tokens = normalized.split()
        if len(q_tokens) > 1:
            phrase_matches: dict[UUID, CandidateMatch] = {}
            for crop in self.registry:
                # Check canonical name
                c_norm = _normalize(crop.canonical_name)
                c_tokens = c_norm.split()
                if c_norm in normalized and len(c_tokens) <= len(q_tokens):
                    for i in range(len(q_tokens) - len(c_tokens) + 1):
                        if q_tokens[i : i + len(c_tokens)] == c_tokens:
                            phrase_matches[crop.crop_id] = CandidateMatch(
                                crop_id=crop.crop_id,
                                canonical_name=crop.canonical_name,
                                scientific_name=crop.scientific_name,
                                matched_alias=crop.canonical_name,
                                match_type="phrase_token",
                            )
                            break
                if crop.crop_id in phrase_matches:
                    continue
                # Check aliases
                for alias in crop.aliases:
                    a_norm = _normalize(alias)
                    a_tokens = a_norm.split()
                    if a_norm in normalized and len(a_tokens) <= len(q_tokens):
                        matched_slice = False
                        for i in range(len(q_tokens) - len(a_tokens) + 1):
                            if q_tokens[i : i + len(a_tokens)] == a_tokens:
                                matched_slice = True
                                break
                        if matched_slice:
                            phrase_matches[crop.crop_id] = CandidateMatch(
                                crop_id=crop.crop_id,
                                canonical_name=crop.canonical_name,
                                scientific_name=crop.scientific_name,
                                matched_alias=alias,
                                match_type="phrase_token",
                            )
                            break

            if len(phrase_matches) == 1:
                match = next(iter(phrase_matches.values()))
                matched_crop = next(c for c in self.registry if c.crop_id == match.crop_id)
                return ResolutionResult(
                    status=ResolutionStatus.EXACT_MATCH,
                    query=query,
                    crop=matched_crop,
                    capability=matched_crop.to_c7_capability(),
                    candidates=[match],
                    message=f"Resolved from phrase to {matched_crop.canonical_name} via '{match.matched_alias}'.",
                )
            elif len(phrase_matches) > 1:
                candidate_list = list(phrase_matches.values())
                return ResolutionResult(
                    status=ResolutionStatus.AMBIGUOUS,
                    query=query,
                    crop=None,
                    capability=None,
                    candidates=candidate_list,
                    message=f"Query phrase matches {len(candidate_list)} distinct crops. Confirmation required.",
                )

        # 6. Check if query contains an ambiguous category token (e.g. "I want to grow millet")
        for cat_token, target_names in AMBIGUOUS_CATEGORIES.items():
            cat_norm = _normalize(cat_token)
            if cat_norm in q_tokens:
                candidates = [
                    CandidateMatch(
                        crop_id=c.crop_id,
                        canonical_name=c.canonical_name,
                        scientific_name=c.scientific_name,
                        matched_alias=cat_token,
                        match_type="category_ambiguity",
                    )
                    for c in self.registry
                    if c.canonical_name in target_names
                ]
                return ResolutionResult(
                    status=ResolutionStatus.AMBIGUOUS,
                    query=query,
                    crop=None,
                    capability=None,
                    candidates=candidates,
                    message=f"Query '{query}' contains crop category '{cat_token}' and matches {len(candidates)} distinct crops. Confirmation required.",
                )

        # 7. Word-bounded token or prefix partial matches across names and aliases
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

