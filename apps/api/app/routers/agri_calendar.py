"""Read-only crop calendar endpoint; no bot commands required from farmers."""
from __future__ import annotations
import os
from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import authorize_path_farm
from app.core.db import get_session
from app.models import CropIdentity, Farm, Plot
from app.schemas import ApiResponse
from app.services.farmer_alerts.calendar import PlantingDate
from app.services.farmer_alerts.calendar_view import build_calendar_view
from app.services.farmer_alerts.profile_loader import load_profiles_file

router = APIRouter(prefix="/api/v1/agri-calendar", tags=["agricultural-calendar"])


@router.get("/farms/{farm_id}", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def calendar_for_farm(farm_id: UUID, request: Request,
                            session: Annotated[AsyncSession, Depends(get_session)]) -> ApiResponse:
    farm = await session.get(Farm, farm_id)
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    try:
        today = datetime.now(ZoneInfo(farm.timezone)).date()
    except (ValueError, KeyError):
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    # Regional profiles are optional; a farmer's own plan still appears without them.
    try:
        profiles = load_profiles_file(os.environ.get("TERRAPULSE_CALENDAR_PROFILES_FILE"))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Regional calendar data currently unavailable") from exc
    plots = list((await session.scalars(select(Plot).where(Plot.farm_id == farm_id).order_by(Plot.created_at, Plot.id))).all())
    result = []
    for index, plot in enumerate(plots, start=1):
        metadata = plot.management or {}
        region = metadata.get("regionId")
        crop = await session.get(CropIdentity, plot.crop_id) if plot.crop_id else None
        result.append(build_calendar_view(farm_id=farm_id, plot_id=plot.id,
            crop_id=plot.crop_id, crop_name=crop.canonical_name if crop else "Your crop",
            plot_name=metadata.get("plotName") or f"Plot {index}",
            region_id=region, planting=PlantingDate.from_plot(plot.planting_date, metadata),
            on_date=today, profile=profiles.get((region, plot.crop_id)) if isinstance(region, str) else None))
    return ApiResponse(data={"farmId":str(farm_id), "asOfDate":today.isoformat(),
        "plots": result, "total":len(result)}, correlationId=request.state.correlation_id)
