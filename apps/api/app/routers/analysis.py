from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import require_farm_access, workspace_digest
from app.core.db import get_session
from app.schemas import ApiError, ApiErrorDetail, ApiResponse
from app.services.analysis import (
    AnalysisRequest,
    AnalysisResponseData,
    EvidenceGroundedAnalysisService,
)
from app.services.analysis.evidence_builder import AnalysisEvidenceError
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
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    """Execute evidence-grounded AI analysis for a specified farm and plot."""
    await require_farm_access(session, payload.farm_id, workspace_digest(request))
    try:
        result: AnalysisResponseData = await service.analyze(payload)
        return ApiResponse(
            data=result.model_dump(by_alias=True),
            correlationId=request.state.correlation_id,
        )
    except KeyError as err:
        body = ApiError(
            error=ApiErrorDetail(
                code="EVIDENCE_NOT_FOUND",
                message=str(err).strip("'\""),
            ),
            correlationId=request.state.correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=body.model_dump(by_alias=True),
        )
    except AnalysisEvidenceError as err:
        body = ApiError(
            error=ApiErrorDetail(code=err.code, message=err.message),
            correlationId=request.state.correlation_id,
        )
        return JSONResponse(
            status_code=err.status_code,
            content=body.model_dump(by_alias=True),
        )
