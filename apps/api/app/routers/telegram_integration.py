"""Webhook-mode Telegram opt-in and Vercel Hobby-compatible daily alerts.

Telegram's webhook replaces getUpdates. Only one environment should own this bot
at a time. The daily endpoint uses already-persisted C1/C3 inputs and sourced
regional calendar profiles; it never manufactures crop stages or weather data.
"""
from __future__ import annotations

import hmac
import json
import os
import re
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionFactory, get_session
from app.services.farmer_alerts.commands import handle_command
from app.services.farmer_alerts.persistence import advance_cursor, get_cursor
from app.services.farmer_alerts.profile_loader import load_profiles_file
from app.services.farmer_alerts.telegram import TelegramClient, command_from_update
from app.services.farmer_alerts.worker import deliver_queued, evaluate_registered_farms

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram-alerts"])
MAX_UPDATE_BYTES = 64 * 1024
HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$", re.I)
SECRET_RE = re.compile(r"^[a-zA-Z0-9_-]{16,256}$")


def _enabled() -> bool:
    return os.environ.get("TERRAPULSE_TELEGRAM_ENABLED") == "1"


def _verify(request: Request, env_key: str, header_name: str, *, prefix: str = "") -> None:
    expected = os.environ.get(env_key, "")
    actual = request.headers.get(header_name, "")
    if not expected or not hmac.compare_digest(actual, prefix + expected):
        # Reject unconfigured endpoints, even if caller supplies an empty value.
        raise HTTPException(status_code=403, detail="Forbidden")


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

    setWebhook uses max_connections=1. update_id is monotonically acknowledged in
    the existing DB cursor. Acknowledgment precedes sending the greeting to avoid
    duplicate subscription changes if a downstream Telegram reply fails. The
    linked subscription persists even if the courtesy reply cannot be delivered.
    """
    if not _enabled():
        raise HTTPException(status_code=503, detail="Telegram integration not activated")
    _verify(request, "TELEGRAM_WEBHOOK_SECRET", "x-telegram-bot-api-secret-token")
    if len(await request.body()) > MAX_UPDATE_BYTES:
        raise HTTPException(status_code=413, detail="Telegram update too large")
    try:
        update = json.loads(await request.body())
    except (UnicodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update") from exc
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Invalid Telegram update")
    update_id = update.get("update_id")
    if type(update_id) is not int or update_id < 0:
        raise HTTPException(status_code=400, detail="Invalid Telegram update ID")
    if update_id < await get_cursor(session):
        return {"ok": True, "duplicate": True}

    parsed = command_from_update(update)
    if parsed:
        chat_id, user_id, language, text = parsed
        # Existing persistence commands commit the one-time link atomically.
        reply = await handle_command(
            session, chat_id=chat_id, user_id=user_id, language=language, text=text
        )
    await advance_cursor(session, update_id)
    if parsed:
        try:
            result = await TelegramClient().send(chat_id, reply)
            if not result.success:
                # Do not leak Telegram chat IDs, tokens, or raw provider responses.
                import logging
                logging.getLogger("terrapulse.telegram").warning(
                    "Telegram acknowledgment delivery failed: %s", result.error_code
                )
        except (RuntimeError, ValueError, OSError):
            import logging
            logging.getLogger("terrapulse.telegram").warning(
                "Telegram acknowledgment delivery temporarily unavailable"
            )
    return {"ok": True, "duplicate": False}


@router.get("/cron", status_code=200)
async def telegram_daily_cron(request: Request) -> dict:
    """Authorized daily Vercel cron (Hobby): evaluate and deliver bounded alerts."""
    _admin(request)
    if not _enabled():
        raise HTTPException(status_code=503, detail="Telegram integration not activated")
    # Fail closed if a webhook was never configured for command opt-ins.
    if not os.environ.get("TELEGRAM_WEBHOOK_SECRET"):
        raise HTTPException(status_code=503, detail="Webhook configuration missing")
    client = TelegramClient()
    profiles = load_profiles_file(os.environ.get("TERRAPULSE_CALENDAR_PROFILES_FILE"))
    async with SessionFactory() as session:
        new_alerts, new_deliveries = await evaluate_registered_farms(
            session, now=datetime.now(timezone.utc), regional_profiles=profiles
        )
    delivery = await deliver_queued(SessionFactory, client, dry_run=False, limit=5)
    return {"ok": True, "newAlerts": new_alerts, "newDeliveries": new_deliveries,
            "delivery": delivery}


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
    if probe.status_code != 403:
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
