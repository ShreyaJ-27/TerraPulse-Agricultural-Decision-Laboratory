from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import authorize_path_farm, require_farm_access, workspace_digest
from app.core.db import SessionFactory, get_session
from app.models import ScientificState
from app.schemas import ApiResponse
from app.services.simulations.orchestration import SimulationService
from app.services.simulations.schemas import SimulationRunResponse, SimulationSubmitRequest

router = APIRouter(prefix="/api/v1", tags=["simulations"])


def _response(run, states=()):
    return SimulationRunResponse(
        simulationRunId=run.id,
        farmId=run.farm_id,
        plotId=run.plot_id,
        branchId=run.branch_id,
        status=run.status,
        engine=run.engine_name,
        engineVersion=run.engine_version,
        parameterVersion=run.parameter_version,
        environmentalSnapshotId=run.environmental_snapshot_id,
        weatherRealizationId=run.weather_realization_id,
        weatherMemberId=run.weather_member_id,
        requestedAt=run.requested_at,
        startedAt=run.started_at,
        completedAt=run.completed_at,
        warnings=run.warnings or [],
        errorCode=run.error_code,
        errorMessage=run.error_message,
        states=list(states),
        scienceEnvelope=run.science_envelope,
        inputProvenance=run.input_provenance,
    ).model_dump(by_alias=True, mode="json")


@router.post("/simulations", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_simulation(
    payload: SimulationSubmitRequest,
    request: Request,
    background: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await require_farm_access(session, payload.farm_id, workspace_digest(request))
    try:
        run = await SimulationService(session).submit(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": str(exc), "message": str(exc)})
    background.add_task(SimulationService(session).execute_background, run.id, SessionFactory)
    return ApiResponse(
        data={"simulationRunId": run.id, "status": run.status},
        correlationId=request.state.correlation_id,
    )


@router.get("/simulations/{run_id}", response_model=ApiResponse)
async def get_simulation(
    run_id: UUID, request: Request, session: Annotated[AsyncSession, Depends(get_session)]
):
    digest = workspace_digest(request)
    run = await SimulationService(session).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation run was not found.")
    await require_farm_access(session, run.farm_id, digest)
    from sqlalchemy import select

    result = await session.execute(
        select(ScientificState)
        .where(ScientificState.simulation_run_id == run.id)
        .order_by(ScientificState.state_date)
    )
    states = [state.payload for state in result.scalars()]
    return ApiResponse(data=_response(run, states), correlationId=request.state.correlation_id)


@router.get("/farms/{farm_id}/plots/{plot_id}/simulations", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def list_simulations(
    farm_id: UUID,
    plot_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    runs = await SimulationService(session).list_runs(farm_id, plot_id)
    return ApiResponse(
        data={"simulations": [_response(run) for run in runs], "total": len(runs)},
        correlationId=request.state.correlation_id,
    )
