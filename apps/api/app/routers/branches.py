from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import authorize_path_farm
from app.core.db import get_session
from app.schemas import ApiResponse
from app.services.branches import BranchService
from app.services.branches_schemas import BranchCreateRequest, BranchResponse, TimelineResponse

router = APIRouter(prefix="/api/v1", tags=["branches"])


def _failure(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": str(exc)})


@router.post("/farms/{farm_id}/plots/{plot_id}/branches", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse, status_code=201)
async def create_branch(
    farm_id: UUID,
    plot_id: UUID,
    payload: BranchCreateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    if payload.plot_id != plot_id:
        raise _failure(ValueError("PLOT_SCOPE_MISMATCH"))
    try:
        branch = await BranchService(session).create(
            farm_id,
            plot_id,
            snapshot_id=payload.environmental_snapshot_id,
            effective_date=payload.effective_date,
            decision_type=payload.decision_type,
            decision_diff=payload.decision_diff,
            parent_branch_id=payload.parent_branch_id,
        )
    except ValueError as exc:
        raise _failure(exc) from exc
    return ApiResponse(
        data=BranchResponse.model_validate(branch).model_dump(by_alias=True, mode="json"),
        correlationId=request.state.correlation_id,
    )


@router.get("/farms/{farm_id}/plots/{plot_id}/branches", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def list_branches(
    farm_id: UUID,
    plot_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        branches = await BranchService(session).list(farm_id, plot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": str(exc)}) from exc
    return ApiResponse(
        data={"branches": [BranchResponse.model_validate(b).model_dump(by_alias=True, mode="json") for b in branches]},
        correlationId=request.state.correlation_id,
    )


@router.get("/farms/{farm_id}/plots/{plot_id}/branches/{branch_id}", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def get_branch(
    farm_id: UUID,
    plot_id: UUID,
    branch_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        branch = await BranchService(session).get(farm_id, plot_id, branch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": str(exc)}) from exc
    return ApiResponse(
        data=BranchResponse.model_validate(branch).model_dump(by_alias=True, mode="json"),
        correlationId=request.state.correlation_id,
    )


@router.get("/farms/{farm_id}/plots/{plot_id}/timeline", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def get_timeline(
    farm_id: UUID,
    plot_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        events = await BranchService(session).timeline(farm_id, plot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": str(exc)}) from exc
    return ApiResponse(
        data={"events": [TimelineResponse.model_validate(e).model_dump(by_alias=True, mode="json") for e in events]},
        correlationId=request.state.correlation_id,
    )
