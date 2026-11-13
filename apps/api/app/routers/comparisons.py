from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import authorize_path_farm
from app.core.db import get_session
from app.schemas import ApiResponse
from app.services.comparison_schemas import ComparisonCreateRequest, ComparisonResponse
from app.services.comparisons import ComparisonService

router = APIRouter(prefix="/api/v1", tags=["comparisons"])


def _dump(comparison):
    data = ComparisonResponse(
        comparisonId=comparison.id,
        farmId=comparison.farm_id,
        plotId=comparison.plot_id,
        baselineBranchId=comparison.branch_a_id,
        alternativeBranchId=comparison.branch_b_id,
        baselineRunId=comparison.run_a_id,
        alternativeRunId=comparison.run_b_id,
        comparisonDate=comparison.comparison_date,
        status=comparison.status,
        matchedInputs=comparison.matched_inputs,
        reasons=comparison.non_comparable_reasons or [],
        payload=comparison.payload,
        createdAt=(comparison.payload or {}).get("createdAt"),
    )
    return data.model_dump(by_alias=True, mode="json")


@router.post("/farms/{farm_id}/plots/{plot_id}/comparisons", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse, status_code=201)
async def create_comparison(
    farm_id: UUID,
    plot_id: UUID,
    payload: ComparisonCreateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        comparison = await ComparisonService(session).compare(
            farm_id,
            plot_id,
            payload.baseline_branch_id,
            payload.alternative_branch_id,
            payload.baseline_run_id,
            payload.alternative_run_id,
            payload.fork_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": str(exc)}) from exc
    return ApiResponse(data=_dump(comparison), correlationId=request.state.correlation_id)


@router.get("/farms/{farm_id}/plots/{plot_id}/comparisons", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def list_comparisons(
    farm_id: UUID,
    plot_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    comparisons = await ComparisonService(session).list(farm_id, plot_id)
    return ApiResponse(
        data={"comparisons": [_dump(item) for item in comparisons]},
        correlationId=request.state.correlation_id,
    )


@router.get("/farms/{farm_id}/plots/{plot_id}/comparisons/{comparison_id}", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def get_comparison(
    farm_id: UUID,
    plot_id: UUID,
    comparison_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        comparison = await ComparisonService(session).get(farm_id, plot_id, comparison_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": str(exc)}) from exc
    return ApiResponse(data=_dump(comparison), correlationId=request.state.correlation_id)
