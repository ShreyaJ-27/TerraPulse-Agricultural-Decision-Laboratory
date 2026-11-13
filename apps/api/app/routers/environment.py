from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import EnvironmentalProvenance, EnvironmentalSnapshot, Farm, Plot
from app.schemas import ApiResponse
from app.services.environmental.models import EnvironmentalInputRequest
from app.services.environmental.service import EnvironmentalInputService

router = APIRouter(prefix="/api/v1/environment", tags=["environment"])


@router.post("/prepare", response_model=ApiResponse)
async def prepare_environment(
    payload: EnvironmentalInputRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    farm = await session.get(Farm, payload.farm_id)
    plot = await session.get(Plot, payload.plot_id) if payload.plot_id else None
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm was not found.")
    if plot is None or plot.farm_id != farm.id:
        raise HTTPException(status_code=404, detail="Plot was not found under this farm.")
    location = farm.location
    from app.services.onboarding import _parse_point_coordinates

    coordinates = _parse_point_coordinates(location)
    result = await EnvironmentalInputService().prepare(
        farm_id=farm.id,
        plot_id=plot.id,
        latitude=coordinates.latitude,
        longitude=coordinates.longitude,
        start_date=payload.simulation_period.start_date,
        end_date=payload.simulation_period.end_date,
        timezone=farm.timezone,
        crop_id=plot.crop_id,
        requested_outputs=payload.requested_outputs,
        weather_member_id=payload.weather_member_id,
        include_ensemble=payload.include_ensemble,
        soil_target_depth_cm=payload.soil_target_depth_cm,
        require_quantitative_simulation=payload.require_quantitative_simulation,
        force_refresh=payload.force_refresh,
    )
    data = result.model_dump(by_alias=True, mode="json")
    c1 = data.get("c1Input") or {}
    data["retrievedAt"] = c1.get("retrievedAt")
    data["provenance"] = c1.get("provenance", [])
    snapshot = EnvironmentalSnapshot(
        farm_id=farm.id,
        plot_id=plot.id,
        payload=data,
        availability=result.status.value,
        input_hash=result.input_hash
        or f"{farm.id}:{plot.id}:{payload.simulation_period.start_date}:{payload.simulation_period.end_date}",
    )
    session.add(snapshot)
    for source in data["provenance"]:
        session.add(
            EnvironmentalProvenance(
                snapshot_id=snapshot.id,
                source_id=source["sourceId"],
                source_version=source.get("sourceVersion"),
                retrieved_at=datetime.fromisoformat(source["retrievedAt"]),
                payload=source,
            )
        )
    await session.commit()
    data["environmentalSnapshotId"] = str(snapshot.id)
    return ApiResponse(data=data, correlationId=request.state.correlation_id)
