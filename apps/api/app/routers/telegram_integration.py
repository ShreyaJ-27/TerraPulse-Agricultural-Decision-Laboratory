"""Webhook-mode Telegram opt-in and Vercel Hobby-compatible daily alerts.

Telegram's webhook replaces getUpdates. Only one environment should own this bot
at a time. The daily endpoint uses already-persisted C1/C3 inputs and sourced
regional calendar profiles; it never manufactures crop stages or weather data.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionFactory, get_session
from app.services.farmer_alerts.commands import handle_command
from app.services.farmer_alerts.persistence import claim_webhook_update
from app.services.farmer_alerts.profile_loader import load_profiles_file
from app.services.farmer_alerts.telegram import TelegramClient, command_from_update
from app.services.farmer_alerts.worker import deliver_queued, evaluate_registered_farms
from app.services.farmer_alerts.evidence_refresh import refresh_subscribed_evidence

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram-alerts"])
logger = logging.getLogger("terrapulse.telegram")
MAX_UPDATE_BYTES = 64 * 1024
MAX_UPDATE_ID = 2**63 - 1
HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$", re.I)
SECRET_RE = re.compile(r"^[a-zA-Z0-9_-]{16,256}$")


def _enabled() -> bool:
    return os.environ.get("TERRAPULSE_TELEGRAM_ENABLED") == "1"


def _verify(request: Request, env_key: str, header_name: str, *, prefix: str = "") -> None:
    expected = os.environ.get(env_key, "")
    actual = request.headers.getlist(header_name)
    if not expected or len(actual) != 1 or not hmac.compare_digest(
        actual[0].encode("latin-1"), (prefix + expected).encode("utf-8")
    ):
        # Reject unconfigured endpoints, even if caller supplies an empty value.
        detail = "Telegram webhook authentication failed" if not prefix else "Forbidden"
        raise HTTPException(status_code=403, detail=detail)


def _admin(request: Request) -> None:
    _verify(request, "CRON_SECRET", "authorization", prefix="Bearer ")


def _public_webhook_url() -> str:
    """Resolve a trusted Vercel-owned HTTPS hostname, never an HTTP Host header."""
    environment = os.environ.get("VERCEL_ENV", "")
    if environment not in {"preview", "production"}:
        raise HTTPException(status_code=503, detail="Vercel environment unavailable")
    if environment == "production":
        host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL") or os.environ.get("VERCEL_URL")
    else:
        host = os.environ.get("VERCEL_URL")
    if not host or not HOST_RE.fullmatch(host) or not host.endswith(".vercel.app"):
        # A verified custom domain can be added by an explicit allowlist change.
        raise HTTPException(status_code=503, detail="Verified Vercel host unavailable")
    return f"https://{host}/api/v1/telegram/webhook"


@router.post("/webhook", status_code=200)
async def telegram_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, bool]:
    """Accept Telegram private-chat commands only after verifying its secret header.

    Store each command's update ID with its subscription changes, then send the
    courtesy reply. Retries acknowledge the stored update without a second reply.
    """
    if not _enabled():
        raise HTTPException(status_code=503, detail="Telegram integration not activated")
    _verify(request, "TELEGRAM_WEBHOOK_SECRET", "x-telegram-bot-api-secret-token")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_UPDATE_BYTES:
            raise HTTPException(status_code=413, detail="Telegram update too large")
        body.extend(chunk)
    try:
        update = json.loads(body)
    except (ValueError, RecursionError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update") from exc
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Invalid Telegram update")
    update_id = update.get("update_id")
    if type(update_id) is not int or not 0 <= update_id <= MAX_UPDATE_ID:
        raise HTTPException(status_code=400, detail="Invalid Telegram update ID")
    parsed = command_from_update(update)
    if parsed is None:
        return {"ok": True, "duplicate": False}
    async with session.begin():
        if not await claim_webhook_update(session, update_id):
            return {"ok": True, "duplicate": True}
        chat_id, user_id, language, text = parsed
        reply = await handle_command(
            session, chat_id=chat_id, user_id=user_id, language=language, text=text
        )
    try:
        result = await TelegramClient().send(chat_id, reply)
        if not result.success:
            logger.warning("Telegram acknowledgment delivery failed: %s", result.error_code)
    except (RuntimeError, ValueError, OSError):
        logger.warning("Telegram acknowledgment delivery temporarily unavailable")
    return {"ok": True, "duplicate": False}


@router.get("/cron", status_code=200)
async def telegram_daily_cron(request: Request) -> dict:
    """Authorized daily Vercel cron (Hobby): evaluate and deliver bounded alerts."""
    _admin(request)
    if not _enabled():
        raise HTTPException(status_code=503, detail="Telegram integration not activated")
    if not SECRET_RE.fullmatch(os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")):
        raise HTTPException(status_code=503, detail="Invalid webhook secret configuration")
    client = TelegramClient()
    current = datetime.now(timezone.utc)
    # Fetch genuinely sourced weather only for subscribed farms, at bounded cost.
    refresh = {"refreshed": 0, "skipped": 0, "failed": 0}
    if os.environ.get("TERRAPULSE_ALERT_REFRESH_ENABLED") == "1":
        refresh = await refresh_subscribed_evidence(SessionFactory, now=current, max_plots=2)
    profiles = load_profiles_file(os.environ.get("TERRAPULSE_CALENDAR_PROFILES_FILE"))
    async with SessionFactory() as session:
        new_alerts, new_deliveries = await evaluate_registered_farms(
            session, now=current, regional_profiles=profiles
        )
    delivery = await deliver_queued(SessionFactory, client, dry_run=False, limit=5)
    return {"ok": True, "newAlerts": new_alerts, "newDeliveries": new_deliveries,
            "weatherRefresh": refresh, "delivery": delivery}


@router.post("/activate-webhook", status_code=200)
async def telegram_activate_webhook(request: Request) -> dict[str, bool]:
    """Explicitly register only the current Vercel environment's public webhook.

    Requires CRON_SECRET and a public reachability probe. A protected Preview
    fails the probe rather than registering an endpoint Telegram cannot reach.
    Never run this on Production until its DB and consent tests are ready.
    """
    _admin(request)
    if not _enabled():
        raise HTTPException(status_code=503, detail="Telegram integration not activated")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not SECRET_RE.fullmatch(secret):
        raise HTTPException(status_code=503, detail="Invalid webhook secret configuration")
    url = _public_webhook_url()
    try:
        # A bad Telegram header must reach *our* webhook and produce 403.
        # A Vercel deployment-protection 401/redirect is not accessible to Telegram.
        async with httpx.AsyncClient(timeout=7, follow_redirects=False) as http:
            probe = await http.post(
                url, json={"update_id": 0},
                headers={"X-Telegram-Bot-Api-Secret-Token": "invalid-probe-token"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=409, detail="Webhook endpoint not publicly reachable") from exc
    try:
        webhook_response = probe.status_code == 403 and probe.json() == {
            "detail": "Telegram webhook authentication failed"
        }
    except ValueError:
        webhook_response = False
    if not webhook_response:
        raise HTTPException(status_code=409, detail="Webhook endpoint not publicly reachable")
    status, result = await TelegramClient()._call("setWebhook", {
        "url": url,
        "secret_token": secret,
        "allowed_updates": ["message"],
        "max_connections": 1,
        "drop_pending_updates": False,
    })
    if status != 200 or result.get("ok") is not True or result.get("result") is not True:
        raise HTTPException(status_code=502, detail="Telegram rejected webhook registration")
    return {"ok": True}
