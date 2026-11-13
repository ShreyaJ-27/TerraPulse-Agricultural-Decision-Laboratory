from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import authorize_path_farm, workspace_digest
from app.core.db import get_session
from app.schemas import (
    ApiError,
    ApiErrorDetail,
    ApiResponse,
    FarmCreateRequest,
    FarmResponse,
    PlotCreateRequest,
    PlotResponse,
)
from app.services.farmer_alerts.registration import issue_farm_link
from app.services.onboarding import AmbiguousCropError, OnboardingService

router = APIRouter(prefix="/api/v1/farms", tags=["farm-onboarding"])


async def get_onboarding_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OnboardingService:
    return OnboardingService(session=session)


ServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    request: Request,
    payload: FarmCreateRequest,
    service: ServiceDep,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    """Register a new farm with confirmed location coordinates."""
    farm: FarmResponse = await service.create_farm(payload, workspace_key_hash=workspace_digest(request))
    # Registration succeeds even if Telegram is temporarily unavailable.
    # The returned link enables one-tap opt-in after registration.
    registration = farm.model_dump(by_alias=True)
    connect_url = await issue_farm_link(session, farm.farm_id)
    if connect_url:
        registration["telegramConnectUrl"] = connect_url
    return ApiResponse(data=registration, correlationId=request.state.correlation_id)


@router.post("/{farm_id}/telegram-link", response_model=ApiResponse,
             dependencies=[Depends(authorize_path_farm)])
async def reconnect_telegram(
    farm_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    if workspace_digest(request) is None:
        raise HTTPException(status_code=401, detail="A farm workspace key is required.")
    url = await issue_farm_link(session, farm_id)
    if not url:
        raise HTTPException(status_code=503, detail="Telegram linking is currently unavailable.")
    return ApiResponse(data={"telegramConnectUrl": url}, correlationId=request.state.correlation_id)


@router.get("", response_model=ApiResponse)
async def list_farms(
    request: Request,
    service: ServiceDep,
) -> ApiResponse:
    """List all registered farms."""
    farms = await service.list_farms(workspace_key_hash=workspace_digest(request))
    return ApiResponse(
        data={"farms": [f.model_dump(by_alias=True) for f in farms], "total": len(farms)},
        correlationId=request.state.correlation_id,
    )


@router.get("/{farm_id}", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def get_farm(
    farm_id: UUID,
    request: Request,
    service: ServiceDep,
) -> ApiResponse:
    """Retrieve a farm by its unique ID."""
    farm = await service.get_farm(farm_id)
    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm ID '{farm_id}' was not found.",
        )
    return ApiResponse(
        data=farm.model_dump(by_alias=True),
        correlationId=request.state.correlation_id,
    )


@router.post("/{farm_id}/plots", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_plot(
    farm_id: UUID,
    payload: PlotCreateRequest,
    request: Request,
    service: ServiceDep,
) -> ApiResponse:
    """Register a plot under a confirmed farm, associating it with a resolved crop identity."""
    try:
        plot: PlotResponse = await service.create_plot(farm_id, payload)
        return ApiResponse(
            data=plot.model_dump(by_alias=True),
            correlationId=request.state.correlation_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm ID '{farm_id}' was not found.",
        )
    except AmbiguousCropError as err:
        body = ApiError(
            error=ApiErrorDetail(
                code="AMBIGUOUS_CROP_IDENTITY",
                message=err.message,
                fields={
                    "cropQuery": [
                        f"{c.canonical_name} ({c.scientific_name})" for c in err.candidates
                    ]
                },
            ),
            correlationId=request.state.correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(by_alias=True),
        )
    except ValueError as err:
        body = ApiError(
            error=ApiErrorDetail(
                code="VALIDATION_ERROR",
                message=str(err),
                fields={"crop": [str(err)]},
            ),
            correlationId=request.state.correlation_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(by_alias=True),
        )


@router.get("/{farm_id}/plots", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def list_plots(
    farm_id: UUID,
    request: Request,
    service: ServiceDep,
) -> ApiResponse:
    """List all plots registered under a farm."""
    try:
        plots = await service.list_plots(farm_id)
        return ApiResponse(
            data={"plots": [p.model_dump(by_alias=True) for p in plots], "total": len(plots)},
            correlationId=request.state.correlation_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm ID '{farm_id}' was not found.",
        )


@router.get("/{farm_id}/plots/{plot_id}", dependencies=[Depends(authorize_path_farm)], response_model=ApiResponse)
async def get_plot(
    farm_id: UUID,
    plot_id: UUID,
    request: Request,
    service: ServiceDep,
) -> ApiResponse:
    """Retrieve a specific plot by farm ID and plot ID."""
    farm = await service.get_farm(farm_id)
    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm ID '{farm_id}' was not found.",
        )
    plot = await service.get_plot(farm_id, plot_id)
    if plot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plot ID '{plot_id}' was not found under farm '{farm_id}'.",
        )
    return ApiResponse(
        data=plot.model_dump(by_alias=True),
        correlationId=request.state.correlation_id,
    )
