from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import DecisionBranch, Plot, ScientificState, SimulationRun
from app.schemas import ApiResponse

router = APIRouter(prefix="/api/v1", tags=["observatory"])


@router.get("/farms/{farm_id}/plots/{plot_id}/scientific-states", response_model=ApiResponse)
async def get_scientific_state(
    farm_id: UUID,
    plot_id: UUID,
    request: Request,
    branch_id: UUID,
    state_date: date,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    plot = await session.get(Plot, plot_id)
    branch = await session.get(DecisionBranch, branch_id)
    if plot is None or plot.farm_id != farm_id or branch is None:
        raise HTTPException(status_code=404, detail={"code": "STATE_SCOPE_NOT_FOUND"})
    if branch.farm_id != farm_id or branch.plot_id != plot_id:
        raise HTTPException(status_code=404, detail={"code": "STATE_SCOPE_NOT_FOUND"})
    result = await session.execute(
        select(ScientificState, SimulationRun)
        .join(SimulationRun, SimulationRun.id == ScientificState.simulation_run_id)
        .where(
            ScientificState.plot_id == plot_id,
            ScientificState.branch_id == branch_id,
            ScientificState.state_date == state_date,
            SimulationRun.farm_id == farm_id,
            SimulationRun.status == "completed",
        )
        .order_by(SimulationRun.completed_at.desc())
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "SCIENTIFIC_STATE_UNAVAILABLE"})
    state, run = row
    return ApiResponse(
        data={
            "farmId": farm_id,
            "plotId": plot_id,
            "branchId": branch_id,
            "simulationRunId": run.id,
            "date": state.state_date,
            "availability": state.availability,
            "state": state.payload,
            "provenance": {
                "engine": run.engine_name,
                "engineVersion": run.engine_version,
                "parameterVersion": run.parameter_version,
                "environmentalSnapshotId": run.environmental_snapshot_id,
                "inputHash": run.input_hash,
                "weatherRealizationId": run.weather_realization_id,
                "weatherMemberId": run.weather_member_id,
                "warnings": run.warnings or [],
                "visualInterpolation": {
                    "allowed": True,
                    "scientificValuesMutated": False,
                    "label": "illustrative visual animation only",
                },
            },
        },
        correlationId=request.state.correlation_id,
    )
