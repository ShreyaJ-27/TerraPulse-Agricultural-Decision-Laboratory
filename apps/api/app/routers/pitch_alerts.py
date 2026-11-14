"""Limited, auditable pitch scenario delivery to a real opted-in Telegram chat.

Never writes fabricated weather or scientific evidence. The separate
telegram_pitch_sends receipt table records only illustrative messages. Both
farm workspace ownership and an explicit server-side farm allowlist apply.
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import require_farm_access, workspace_digest
from app.core.db import SessionFactory, get_session
from app.models import Farm, Plot, CropIdentity
from app.services.farmer_alerts.models import TelegramSubscription, PitchAlertSend
from app.services.farmer_alerts.pitch_message import rainfall_watch_message
from app.services.farmer_alerts.telegram import TelegramClient

router = APIRouter(prefix="/api/v1", tags=["pitch-alerts"])
COOLDOWN_SECONDS = 90
MAX_SENDS_PER_DAY = 4


class PitchSendRequest(BaseModel):
    # The operator uses this for safely retrying if the browser loses the response.
    requestId: UUID


class AdminPitchSendRequest(BaseModel):
    farmId: UUID
    requestId: UUID


def _authorized_pitch_farm(farm_id: UUID) -> bool:
    if os.environ.get("TERRAPULSE_TELEGRAM_ENABLED") != "1":
        return False
    if os.environ.get("TERRAPULSE_PITCH_ALERTS_ENABLED") != "1":
        return False
    if str(farm_id) != os.environ.get("TERRAPULSE_PITCH_FARM_ID", ""):
        return False
    expires = os.environ.get("TERRAPULSE_PITCH_EXPIRES_AT", "")
    if not expires:
        return False
    try:
        expiration = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        return False
    return expiration.tzinfo is not None and expiration > datetime.now(timezone.utc)


def _require_admin(request: Request) -> None:
    expected = os.environ.get("CRON_SECRET", "")
    provided = request.headers.getlist("authorization")
    if (not expected or len(provided) != 1 or not hmac.compare_digest(
        provided[0], "Bearer " + expected
    )):
        raise HTTPException(403, "Forbidden")


async def _available_sub(session: AsyncSession, farm_id: UUID):
    return await session.scalar(
        select(TelegramSubscription).where(
            TelegramSubscription.farm_id == farm_id,
            TelegramSubscription.active.is_(True),
        ).order_by(TelegramSubscription.created_at, TelegramSubscription.id).limit(1)
    )


@router.get("/farms/{farm_id}/pitch-alert")
async def pitch_alert_status(
    farm_id: UUID, request: Request, session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Owner-only; invisible for farms not explicitly approved for a pitch."""
    await require_farm_access(session, farm_id, workspace_digest(request))
    if not _authorized_pitch_farm(farm_id):
        return {"available": False}
    sub = await _available_sub(session, farm_id)
    latest = await session.scalar(select(PitchAlertSend).where(
        PitchAlertSend.farm_id == farm_id,
    ).order_by(PitchAlertSend.created_at.desc()).limit(1))
    cooldown = max(0, int((latest.created_at + timedelta(seconds=COOLDOWN_SECONDS)
                           - datetime.now(timezone.utc)).total_seconds()) + 1) if latest else 0
    return {"available": True, "connected": sub is not None,
            "cooldownSeconds": cooldown, "scenario": "rainfall-watch"}


async def _send_pitch(farm_id: UUID, request_id: UUID, *, browser_digest: str | None = None) -> dict:
    if not _authorized_pitch_farm(farm_id):
        raise HTTPException(404, "Pitch alert not enabled for this farm")
    now = datetime.now(timezone.utc)
    receipt_id = uuid4()
    async with SessionFactory() as session:
        async with session.begin():
            await require_farm_access(session, farm_id, browser_digest)
            # Serializes simultaneous sends for this farm before rate-checking.
            farm = await session.scalar(select(Farm).where(
                Farm.id == farm_id
            ).with_for_update())
            if farm is None:
                raise HTTPException(404, "Farm not found")
            existing = await session.scalar(select(PitchAlertSend).where(
                PitchAlertSend.farm_id == farm_id,
                PitchAlertSend.request_id == request_id,
            ))
            if existing is not None:
                return {"sent": existing.status == "sent", "status": existing.status,
                        "receiptId": str(existing.id), "replayed": True}
            sub = await _available_sub(session, farm_id)
            if sub is None:
                raise HTTPException(409, "Connect Telegram for this farm first")
            latest = await session.scalar(select(PitchAlertSend.created_at).where(
                PitchAlertSend.farm_id == farm_id,
            ).order_by(PitchAlertSend.created_at.desc()).limit(1))
            if latest is not None and now - latest < timedelta(seconds=COOLDOWN_SECONDS):
                raise HTTPException(429, "Please allow a short interval between pitch alerts")
            count = await session.scalar(select(func.count(PitchAlertSend.id)).where(
                PitchAlertSend.farm_id == farm_id,
                PitchAlertSend.created_at >= now - timedelta(hours=24),
            ))
            if count is not None and count >= MAX_SENDS_PER_DAY:
                raise HTTPException(429, "Daily pitch-alert limit reached")
            # Use an actual, verified crop identity, not a made-up farm name.
            row = await session.execute(select(Plot, CropIdentity).join(
                CropIdentity, Plot.crop_id == CropIdentity.id, isouter=True
            ).where(Plot.farm_id == farm_id).order_by(Plot.id).limit(1))
            plot_pair = row.first()
            crop_name = (plot_pair[1].canonical_name if plot_pair and plot_pair[1]
                         else "your crop")
            chat_id = sub.chat_id
            receipt = PitchAlertSend(
                id=receipt_id, farm_id=farm_id, subscription_id=sub.id,
                request_id=request_id, scenario="rainfall-watch",
                status="sending", created_at=now,
            )
            session.add(receipt)

    # Do not hold database locks while waiting on Telegram's network.
    try:
        result = await TelegramClient().send(chat_id, rainfall_watch_message(crop_name))
        success = bool(result.success and result.message_id is not None)
        message_id = result.message_id if success else None
        error_code = None if success else (result.error_code or "SEND_NOT_CONFIRMED")[:80]
    except (OSError, ValueError, RuntimeError):
        success, message_id, error_code = False, None, "SEND_UNAVAILABLE"
    async with SessionFactory() as session:
        async with session.begin():
            stored = await session.get(PitchAlertSend, receipt_id)
            if stored is not None:
                stored.status = "sent" if success else "failed"
                stored.telegram_message_id = message_id
                stored.error_code = error_code
    if not success:
        raise HTTPException(502, "Telegram could not confirm scenario delivery")
    return {"sent": True, "status": "sent", "receiptId": str(receipt_id),
            "scenario": "rainfall-watch", "telegramMessageId": message_id}


@router.post("/farms/{farm_id}/pitch-alert")
async def pitch_alert_send(
    farm_id: UUID, payload: PitchSendRequest, request: Request,
) -> dict:
    return await _send_pitch(farm_id, payload.requestId, browser_digest=workspace_digest(request))


@router.post("/telegram/pitch-send")
async def operator_pitch_alert_send(request: Request, payload: AdminPitchSendRequest) -> dict:
    """Operator-only fallback for a farm linked from a separate test browser."""
    _require_admin(request)
    return await _send_pitch(payload.farmId, payload.requestId)
