import json
from datetime import datetime
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import require_farm_access, workspace_digest
from app.core.db import get_session
from app.models import EnvironmentalProvenance, EnvironmentalSnapshot, Farm, Plot
from app.schemas import ApiResponse
from app.services.environmental.models import EnvironmentalInputRequest
from app.services.environmental.service import EnvironmentalInputService
from app.services.farmer_alerts.calendar import PlantingDate
from app.services.simulations.orchestration import farm_execution_blocker

router = APIRouter(prefix="/api/v1/environment", tags=["environment"])


def _snapshot_content(value):
    """Keep scientific inputs and source metadata while ignoring retrieval timestamps."""
    if isinstance(value, dict):
        return {
            key: _snapshot_content(item)
            for key, item in value.items()
            if key not in {
                "retrievedAt", "freshness", "inputHash",
                "forecast_generationtime_ms", "ensemble_generationtime_ms",
            }
        }
    if isinstance(value, list):
        return [_snapshot_content(item) for item in value]
    return value


async def _store_snapshot(session, farm_id, plot_id, data):
    c1 = data.get("c1Input") or {}
    data = {**data, "retrievedAt": c1.get("retrievedAt"), "provenance": c1.get("provenance", [])}
    content = _snapshot_content(data)
    period = c1.get("simulationPeriod")
    if period:
        legacy_hash = f"{farm_id}:{plot_id}:{period['startDate']}:{period['endDate']}"
        legacy = (await session.execute(
            select(EnvironmentalSnapshot.id, EnvironmentalSnapshot.payload).where(
                EnvironmentalSnapshot.input_hash == legacy_hash
            )
        )).one_or_none()
        if legacy and _snapshot_content(legacy.payload) == {
            key: value for key, value in content.items()
            if key not in {"planting", "simulationBlocker"}
        } and data["planting"]["date"] is None:
            return {**legacy.payload, "planting": data["planting"],
                    "simulationBlocker": data["simulationBlocker"],
                    "environmentalSnapshotId": str(legacy.id)}
    normalized = json.dumps(content, sort_keys=True, separators=(",", ":"))
    input_hash = sha256(f"{farm_id}:{plot_id}:{normalized}".encode()).hexdigest()
    statement = (
        insert(EnvironmentalSnapshot)
        .values(farm_id=farm_id, plot_id=plot_id, payload=data,
                availability=data["status"], input_hash=input_hash)
        .on_conflict_do_nothing(index_elements=[EnvironmentalSnapshot.input_hash])
        .returning(EnvironmentalSnapshot.id)
    )
    snapshot_id = await session.scalar(statement)
    if snapshot_id is None:
        # At READ COMMITTED a new statement sees the winning insert and its provenance.
        existing = (await session.execute(
            select(EnvironmentalSnapshot.id, EnvironmentalSnapshot.payload).where(
                EnvironmentalSnapshot.input_hash == input_hash
            )
        )).one()
        snapshot_id, data = existing
    else:
        for source in data["provenance"]:
            session.add(EnvironmentalProvenance(
                snapshot_id=snapshot_id,
                source_id=source["sourceId"],
                source_version=source.get("sourceVersion"),
                retrieved_at=datetime.fromisoformat(source["retrievedAt"]),
                payload=source,
            ))
    await session.commit()
    return {**data, "environmentalSnapshotId": str(snapshot_id)}


@router.post("/prepare", response_model=ApiResponse)
async def prepare_environment(
    payload: EnvironmentalInputRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    await require_farm_access(session, payload.farm_id, workspace_digest(request))
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
    planting = PlantingDate.from_plot(plot.planting_date, plot.management or {})
    data["planting"] = {
        "date": planting.date.isoformat() if planting.date else None,
        "certainty": planting.certainty,
    }
    blocker = farm_execution_blocker(plot.crop_id) if plot.crop_id else None
    data["simulationBlocker"] = {"code": blocker[0], "message": blocker[1]} if blocker else None
    data = await _store_snapshot(session, farm.id, plot.id, data)
    return ApiResponse(data=data, correlationId=request.state.correlation_id)
