"""Redeem an existing farmer's one-tap Telegram link on a new browser."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import workspace_digest
from app.core.db import get_session
from app.schemas import ApiResponse
from app.services.farmer_alerts.workspace_links import redeem_one_tap_link

router = APIRouter(prefix="/api/v1/workspace-link", tags=["farm-workspace"])


class OpenLinkRequest(BaseModel):
    token: str = Field(min_length=40, max_length=64)


@router.post("/redeem", response_model=ApiResponse)
async def redeem(
    request: Request,
    payload: OpenLinkRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    digest = workspace_digest(request)
    if digest is None:
        raise HTTPException(status_code=401, detail="A browser workspace key is required")
    async with session.begin():
        farm_ids = await redeem_one_tap_link(session, token=payload.token, browser_digest=digest)
    return ApiResponse(
        data={"farmIds": farm_ids, "total": len(farm_ids)},
        correlationId=request.state.correlation_id,
    )
