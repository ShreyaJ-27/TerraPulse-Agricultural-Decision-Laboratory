from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.contracts import C7ModelCapability
from app.schemas import ApiResponse
from app.services.crop_lens.registry import CROP_REGISTRY, get_crop_by_id, list_crops
from app.services.crop_lens.resolver import (
    CropLensResolver,
    ResolutionResult,
    ResolutionStatus,
)

router = APIRouter(prefix="/api/v1/crops", tags=["crop-lens"])
resolver = CropLensResolver(CROP_REGISTRY)


class ExternalReferenceOut(BaseModel):
    source_name: str = Field(alias="sourceName")
    identifier: str
    uri: str | None = None
    description: str | None = None
    model_config = ConfigDict(populate_by_name=True)


class CropCatalogItem(BaseModel):
    crop_id: UUID = Field(alias="cropId")
    canonical_name: str = Field(alias="canonicalName")
    scientific_name: str = Field(alias="scientificName")
    family: str
    aliases: list[str]
    external_references: list[ExternalReferenceOut] = Field(alias="externalReferences")
    selected_engine: str = Field(alias="selectedEngine")
    engine_version: str = Field(alias="engineVersion")
    supported_outputs: list[str] = Field(alias="supportedOutputs")
    model_config = ConfigDict(populate_by_name=True)


class CandidateMatchOut(BaseModel):
    crop_id: UUID = Field(alias="cropId")
    canonical_name: str = Field(alias="canonicalName")
    scientific_name: str = Field(alias="scientificName")
    matched_alias: str = Field(alias="matchedAlias")
    match_type: str = Field(alias="matchType")
    model_config = ConfigDict(populate_by_name=True)


class CropResolutionResponse(BaseModel):
    status: str
    query: str
    message: str
    crop: CropCatalogItem | None = None
    capability: C7ModelCapability | None = None
    candidates: list[CandidateMatchOut] = Field(default_factory=list)
    model_config = ConfigDict(populate_by_name=True)


def _to_catalog_item(record: Any) -> CropCatalogItem:
    return CropCatalogItem(
        cropId=record.crop_id,
        canonicalName=record.canonical_name,
        scientificName=record.scientific_name,
        family=record.family,
        aliases=record.aliases,
        externalReferences=[
            ExternalReferenceOut(
                sourceName=ref.source_name,
                identifier=ref.identifier,
                uri=ref.uri,
                description=ref.description,
            )
            for ref in record.external_references
        ],
        selectedEngine=record.selected_engine,
        engineVersion=record.engine_version,
        supportedOutputs=record.supported_outputs,
    )


@router.get("", response_model=ApiResponse)
async def get_crop_catalog(request: Request) -> ApiResponse:
    """List all crops in the curated catalog with their capabilities and external taxonomy."""
    items = [_to_catalog_item(crop) for crop in list_crops()]
    return ApiResponse(
        data={"crops": [item.model_dump(by_alias=True) for item in items], "total": len(items)},
        correlationId=request.state.correlation_id,
    )


@router.get("/resolve", response_model=ApiResponse)
async def resolve_crop(
    request: Request,
    q: str = Query(..., min_length=1, description="Crop name, alias, or scientific name to resolve"),
    allow_unsupported: bool = Query(
        False, description="Whether to create an uncalibrated identity/ecology-only capability if off-catalogue"
    ),
    scientific_name: str | None = Query(
        None, description="Optional botanical scientific name for off-catalogue registration"
    ),
) -> ApiResponse:
    """Resolve a crop name/alias with strict ambiguity handling."""
    result: ResolutionResult = resolver.resolve(q)

    if result.status == ResolutionStatus.EXACT_MATCH and result.crop is not None:
        payload = CropResolutionResponse(
            status=result.status.value,
            query=q,
            message=result.message,
            crop=_to_catalog_item(result.crop),
            capability=result.capability,
            candidates=[
                CandidateMatchOut(
                    cropId=c.crop_id,
                    canonicalName=c.canonical_name,
                    scientificName=c.scientific_name,
                    matchedAlias=c.matched_alias,
                    matchType=c.match_type,
                )
                for c in result.candidates
            ],
        )
        return ApiResponse(data=payload.model_dump(by_alias=True), correlationId=request.state.correlation_id)

    if result.status == ResolutionStatus.AMBIGUOUS:
        payload = CropResolutionResponse(
            status=result.status.value,
            query=q,
            message=result.message,
            crop=None,
            capability=None,
            candidates=[
                CandidateMatchOut(
                    cropId=c.crop_id,
                    canonicalName=c.canonical_name,
                    scientificName=c.scientific_name,
                    matchedAlias=c.matched_alias,
                    matchType=c.match_type,
                )
                for c in result.candidates
            ],
        )
        return ApiResponse(data=payload.model_dump(by_alias=True), correlationId=request.state.correlation_id)

    if allow_unsupported:
        unsupported_cap = resolver.create_unsupported_capability(q, scientific_name=scientific_name)
        payload = CropResolutionResponse(
            status=ResolutionStatus.UNSUPPORTED_OFF_CATALOGUE.value,
            query=q,
            message=f"Crop '{q}' is not in catalogue. Generated uncalibrated identity/ecology-only contract.",
            crop=None,
            capability=unsupported_cap,
            candidates=[],
        )
        return ApiResponse(data=payload.model_dump(by_alias=True), correlationId=request.state.correlation_id)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No matching crop found for '{q}'. Pass allow_unsupported=true to register an uncalibrated identity.",
    )


@router.get("/{crop_id}/capability", response_model=ApiResponse)
async def get_crop_capability(request: Request, crop_id: UUID) -> ApiResponse:
    """Retrieve authoritative C7 Model Capability for a specific crop ID."""
    crop = get_crop_by_id(crop_id)
    if crop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop ID '{crop_id}' not found in registry.",
        )
    capability = crop.to_c7_capability()
    return ApiResponse(
        data=capability.model_dump(by_alias=True),
        correlationId=request.state.correlation_id,
    )
