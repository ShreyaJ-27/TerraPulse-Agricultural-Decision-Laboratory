"""Browser workspace credentials scope deployed farm records to their owner."""
import re
from hashlib import sha256
from hmac import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.models import Farm
from app.services.farmer_alerts.models import FarmWorkspaceGrant


def workspace_digest(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if not authorization and not get_settings().require_workspace_key:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not re.fullmatch(r"[a-f0-9]{64}", token):
        raise HTTPException(status_code=401, detail="A farm workspace key is required.")
    return sha256(token.encode("ascii")).hexdigest()


async def require_farm_access(
    session: AsyncSession, farm_id: UUID, digest: str | None
) -> None:
    if digest is None:
        return  # Local development mode only.
    farm = await session.get(Farm, farm_id)
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found in this workspace.")
    if farm.workspace_key_hash and compare_digest(farm.workspace_key_hash, digest):
        return
    # A Telegram-issued one-tap link grants access to this farm only.
    grant = await session.scalar(select(FarmWorkspaceGrant.id).where(
        FarmWorkspaceGrant.farm_id == farm_id,
        FarmWorkspaceGrant.token_hash == digest,
    ))
    if grant is None:
        raise HTTPException(status_code=404, detail="Farm not found in this workspace.")


async def authorize_path_farm(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> None:
    digest = workspace_digest(request)
    try:
        farm_id = UUID(request.path_params["farm_id"])
    except ValueError:
        return  # FastAPI validates the path parameter.
    await require_farm_access(session, farm_id, digest)
