from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas import ApiResponse
from app.services.analysis import (
    AnalysisRequest,
    AnalysisResponseData,
    EvidenceGroundedAnalysisService,
)
from app.services.crop_lens import CropLensResolver
from app.services.crop_lens.registry import CROP_REGISTRY
from app.services.environmental import EnvironmentalInputService
from app.services.onboarding import OnboardingService

router = APIRouter(prefix="/api/v1/analysis", tags=["evidence-analysis"])


async def get_analysis_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceGroundedAnalysisService:
    onboarding = OnboardingService(session=session)
    crop_resolver = CropLensResolver(CROP_REGISTRY)
    environmental = EnvironmentalInputService(crop_resolver=crop_resolver)
    return EvidenceGroundedAnalysisService(
        onboarding_service=onboarding,
        crop_resolver=crop_resolver,
        environmental_service=environmental,
    )


ServiceDep = Annotated[EvidenceGroundedAnalysisService, Depends(get_analysis_service)]


@router.post("", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def run_analysis(
    request: Request,
    payload: AnalysisRequest,
    service: ServiceDep,
) -> ApiResponse:
    """Execute evidence-grounded AI analysis for a specified farm and plot."""
    try:
        result: AnalysisResponseData = await service.analyze(payload)
        return ApiResponse(
            data=result.model_dump(by_alias=True),
            correlationId=request.state.correlation_id,
        )
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err).strip("'\""),
        )
