"""Agricultural Calendar 2.0 Router: season-wise crop intelligence, regional variations,
sowing recommendations, growth stages, irrigation scheduling and explanations.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
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

SEASONS_INFO = [
    {
        "id": "kharif",
        "name": "Kharif Season (Monsoon)",
        "period": "June to October",
        "sowingMonths": "June – July",
        "harvestMonths": "September – October",
        "characteristics": "High rainfall, warm temperatures, monsoon-dependent soil moisture. Sowing is coordinated with pre-monsoon showers or early monsoon onset.",
        "dominantCrops": ["Rice", "Maize", "Turmeric", "Cotton", "Groundnut", "Pearl Millet", "Finger Millet"],
        "waterManagement": "Ensure field drainage to prevent standing water logging. Utilize furrow irrigation during unexpected dry spells.",
        "criticalStages": "Tasseling/Silking for Maize, Tillering/Panicle for Rice, Vegetative Bulking for Turmeric.",
        "commonRisks": "Early dry spells delaying sowing, excess flooding, leaf blight, stem borer infestation."
    },
    {
        "id": "rabi",
        "name": "Rabi Season (Winter)",
        "period": "October to March",
        "sowingMonths": "October – November",
        "harvestMonths": "March – April",
        "characteristics": "Cool dry weather, declining day length, residual subsoil moisture or assured irrigation requirement. Frost vigilance in northern belts.",
        "dominantCrops": ["Wheat", "Chickpea (Bengal Gram)", "Mustard", "Barley", "Green Peas"],
        "waterManagement": "Critical stage irrigation is essential: Crown Root Initiation (CRI) 21 days post-sowing, flowering, and grain milking.",
        "criticalStages": "Crown Root Initiation (21-25 DAS), Flowering/Anthesis, Dough stage.",
        "commonRisks": "Delayed sowing reducing yield, terminal heat stress during March grain filling, yellow rust."
    },
    {
        "id": "zaid",
        "name": "Zaid Season (Summer)",
        "period": "March to June",
        "sowingMonths": "February – March",
        "harvestMonths": "May – June",
        "characteristics": "Warm dry summer, long sunny days, high reference evapotranspiration (ET0). Requires dependable irrigation supply.",
        "dominantCrops": ["Okra (Bhindi)", "Watermelon", "Muskmelon", "Cucumber", "Summer Pulses (Moong, Urad)"],
        "waterManagement": "Frequent light irrigations (4-6 day intervals). Drip irrigation with plastic or organic mulching drastically improves water efficiency.",
        "criticalStages": "Emergence, Flowering initiation, Pod development.",
        "commonRisks": "Severe evapotranspirative demand, desiccating winds, whitefly vectors transmitting YVMV."
    }
]


def _get_profiles():
    return load_profiles_file(os.environ.get("TERRAPULSE_CALENDAR_PROFILES_FILE"))


@router.get("/seasons", response_model=ApiResponse)
async def get_seasons_overview(request: Request) -> ApiResponse:
    """Return scientific season-wise crop calendar intelligence for India."""
    return ApiResponse(
        data={"seasons": SEASONS_INFO, "total": len(SEASONS_INFO)},
        correlationId=request.state.correlation_id,
    )


@router.get("/regional/{region_id}", response_model=ApiResponse)
async def get_regional_calendar(region_id: str, request: Request) -> ApiResponse:
    """Return regional agricultural calendar profiles (e.g. IN-PB, IN-KA)."""
    profiles = _get_profiles()
    matches = []
    for (r, crop_id), profile in profiles.items():
        if r == region_id:
            windows = [
                {
                    "code": w.code,
                    "label": w.label,
                    "start": w.start.isoformat(),
                    "end": w.end.isoformat(),
                    "sourceId": w.source_id,
                }
                for w in profile.planting_windows
            ]
            milestones = [
                {
                    "code": m.code,
                    "label": m.label,
                    "daysAfterPlanting": m.days_after_planting,
                    "guidance": m.guidance,
                    "sourceId": m.source_id,
                }
                for m in profile.milestones
            ]
            matches.append(
                {
                    "regionId": profile.region_id,
                    "cropId": str(crop_id),
                    "sourceId": profile.source_id,
                    "sourceVersion": profile.source_version,
                    "plantingWindowNote": profile.planting_window_note,
                    "plantingWindows": windows,
                    "milestones": milestones,
                }
            )

    return ApiResponse(
        data={"regionId": region_id, "profiles": matches, "total": len(matches)},
        correlationId=request.state.correlation_id,
    )


class GenerateCalendarRequest(BaseModel):
    cropId: UUID
    plantingDate: date
    regionId: str = "IN-PB"
    certainty: str = "confirmed"


@router.post("/generate", response_model=ApiResponse)
async def generate_custom_calendar(
    payload: GenerateCalendarRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    """Generate dynamic season and stage calendar for any crop and planting date."""
    crop = await session.get(CropIdentity, payload.cropId)
    crop_name = crop.canonical_name if crop else "Crop"
    profiles = _get_profiles()
    profile = profiles.get((payload.regionId, payload.cropId))

    view = build_calendar_view(
        farm_id=UUID("00000000-0000-0000-0000-000000000001"),
        plot_id=UUID("00000000-0000-0000-0000-000000000101"),
        crop_id=payload.cropId,
        crop_name=crop_name,
        plot_name=f"{crop_name} Plot",
        region_id=payload.regionId,
        planting=PlantingDate(payload.plantingDate, payload.certainty if payload.certainty in ("confirmed", "estimated", "recorded") else "recorded"),
        on_date=payload.plantingDate,
        profile=profile,
    )

    # Determine season from planting month
    month = payload.plantingDate.month
    if 6 <= month <= 10:
        season = SEASONS_INFO[0]
    elif month >= 11 or month <= 2:
        season = SEASONS_INFO[1]
    else:
        season = SEASONS_INFO[2]

    view["season"] = season
    return ApiResponse(data=view, correlationId=request.state.correlation_id)


@router.get("/farms/{farm_id}", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def calendar_for_farm(
    farm_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    """Season-wise agricultural calendar for all plots in a farm."""
    farm = await session.get(Farm, farm_id)
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found")

    try:
        today = datetime.now(ZoneInfo(farm.timezone)).date()
    except (ValueError, KeyError):
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    profiles = _get_profiles()
    plots = list((await session.scalars(select(Plot).where(Plot.farm_id == farm_id).order_by(Plot.created_at, Plot.id))).all())
    result = []

    for index, plot in enumerate(plots, start=1):
        metadata = plot.management or {}
        region = metadata.get("regionId")
        crop = await session.get(CropIdentity, plot.crop_id) if plot.crop_id else None

        cal = build_calendar_view(
            farm_id=farm_id,
            plot_id=plot.id,
            crop_id=plot.crop_id,
            crop_name=crop.canonical_name if crop else "Your crop",
            plot_name=metadata.get("plotName") or f"Plot {index}",
            region_id=region,
            planting=PlantingDate.from_plot(plot.planting_date, metadata),
            on_date=today,
            profile=profiles.get((region, plot.crop_id)) if isinstance(region, str) else None,
        )

        # A modeled stage requires observations or scientific state for this plot.
        if plot.planting_date:
            days_grown = (today - plot.planting_date).days
            cal["daysSincePlanting"] = days_grown if days_grown >= 0 else None
        else:
            cal["daysSincePlanting"] = None
        cal["currentGrowthStage"] = None

        cal["activeSeason"] = "Kharif" if 6 <= today.month <= 10 else "Rabi" if today.month >= 11 or today.month <= 2 else "Zaid"
        result.append(cal)

    return ApiResponse(
        data={
            "farmId": str(farm_id),
            "asOfDate": today.isoformat(),
            "plots": result,
            "total": len(result),
            "seasons": SEASONS_INFO,
        },
        correlationId=request.state.correlation_id,
    )
