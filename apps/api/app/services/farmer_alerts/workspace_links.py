"""One-tap, short-lived links from an existing private Telegram subscription.

A farmer types /open in the same chat already receiving TerraPulse alerts, taps
one link, and gets their already-registered farms on that browser. The original
farm key and Telegram subscriptions are neither read nor replaced.

Uses the *already installed* revision 0010 table. No second approval, password,
or Telegram bot permission change. A one-use link is a bearer credential; don't
log it or put it in an HTTP query parameter. A browser redeems it from a fragment.
"""
from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import FarmWorkspaceGrant, TelegramBrowserReconnect, TelegramSubscription
from .persistence import token_digest

LINK_TTL_MINUTES = 10
LINKS_PER_HOUR = 12
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,64}$")
_HOST_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$", re.I)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def workspace_origin() -> str:
    """Never trust the HTTP Host header to build a Telegram access link."""
    configured = os.environ.get("TERRAPULSE_FARM_ORIGIN", "").strip().rstrip("/")
    if configured:
        parsed = urlsplit(configured)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/") or parsed.port not in (None, 443)):
            raise ValueError("Invalid TERRAPULSE_FARM_ORIGIN; set a trusted HTTPS site origin")
        return f"https://{parsed.hostname}" + (":443" if parsed.port == 443 else "")
    for name in ("VERCEL_BRANCH_URL", "VERCEL_URL"):
        host = os.environ.get(name, "").strip().lower()
        if (_HOST_PATTERN.fullmatch(host) and host.endswith(".vercel.app")
                and ".." not in host):
            return "https://" + host
    raise ValueError("Set TERRAPULSE_FARM_ORIGIN to the stable TerraPulse HTTPS address")


def _chat_hash(chat_id: int) -> str:
    # Not a credential; groups requests for a small per-chat issuance limit.
    return sha256(f"terrapulse:open:{chat_id}".encode("ascii")).hexdigest()


async def issue_one_tap_link(session: AsyncSession, *, chat_id: int, user_id: int) -> str | None:
    """Called only by the secret-verified Telegram private-chat webhook."""
    if not 0 < chat_id == user_id < 2**63:
        return None
    eligible = await session.scalar(select(TelegramSubscription.id).where(
        TelegramSubscription.chat_id == chat_id,
        TelegramSubscription.user_id == user_id,
        TelegramSubscription.active.is_(True),
    ).order_by(TelegramSubscription.id).limit(1).with_for_update())
    if eligible is None:
        return None
    # Fail before inserting a token if the deployment cannot build a valid URL.
    origin = workspace_origin()
    now = utcnow()
    count = await session.scalar(select(func.count(TelegramBrowserReconnect.id)).where(
        TelegramBrowserReconnect.client_hash == _chat_hash(chat_id),
        TelegramBrowserReconnect.created_at >= now - timedelta(hours=1),
    ))
    if (count or 0) >= LINKS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many open-link requests")

    token = secrets.token_urlsafe(32)
    # 0010 originally reserved two other hashes for browser-poll flow; the
    # one-tap variant needs neither, so store independent unpredictable values.
    session.add(TelegramBrowserReconnect(
        id=uuid4(), token_hash=token_digest(token),
        poll_hash=token_digest(secrets.token_urlsafe(32)),
        client_hash=_chat_hash(chat_id),
        farm_id=None, approved_chat_id=chat_id, approved_user_id=user_id,
        approved_at=now, expires_at=now + timedelta(minutes=LINK_TTL_MINUTES),
        redeemed_at=None, created_at=now,
    ))
    # Transaction is committed alongside webhook replay prevention by caller.
    return f"{origin}/recover#open={token}"


async def redeem_one_tap_link(
    session: AsyncSession, *, token: str, browser_digest: str
) -> list[str]:
    """Atomically redeem once, granting this browser *only* active linked farms.

    The caller owns a transaction. Row lock prevents competing consumers of
    the same link; raising an error rolls back grants and consumption together.
    """
    if not _TOKEN_PATTERN.fullmatch(token) or not re.fullmatch(r"[a-f0-9]{64}", browser_digest):
        raise HTTPException(status_code=404, detail="Open link unavailable. Request a new /open link in Telegram.")
    lookup = select(TelegramBrowserReconnect).where(
        TelegramBrowserReconnect.token_hash == token_digest(token),
    )
    row = await session.scalar(lookup)
    unavailable = HTTPException(
        status_code=404, detail="Open link unavailable. Request a new /open link in Telegram."
    )
    if (row is None or row.redeemed_at is not None or row.approved_at is None
            or row.expires_at <= utcnow() or row.approved_chat_id is None
            or row.approved_chat_id != row.approved_user_id or row.farm_id is not None
            or row.client_hash != _chat_hash(row.approved_chat_id)):
        raise unavailable

    # Do not rely only on the subscription's state when the token was issued:
    # a farmer who sent /stop before redemption must not get a new grant.
    farm_ids = list(set((await session.scalars(select(TelegramSubscription.farm_id).where(
        TelegramSubscription.chat_id == row.approved_chat_id,
        TelegramSubscription.user_id == row.approved_user_id,
        TelegramSubscription.active.is_(True),
    ).order_by(TelegramSubscription.id).with_for_update())).all()))
    if not farm_ids:
        raise HTTPException(status_code=404, detail="No active linked farm. Reconnect Telegram from the existing farm workspace.")

    # Match the unsubscribe lock order and refresh the row after waiting.
    row = await session.scalar(lookup.with_for_update().execution_options(populate_existing=True))
    now = utcnow()
    if row is None or row.redeemed_at is not None or row.expires_at <= now:
        raise unavailable

    stmt = pg_insert(FarmWorkspaceGrant).values([
        {"id": uuid4(), "farm_id": farm_id,
         "token_hash": browser_digest, "created_at": now}
        for farm_id in farm_ids
    ])
    await session.execute(stmt.on_conflict_do_nothing(
        index_elements=[FarmWorkspaceGrant.farm_id, FarmWorkspaceGrant.token_hash],
    ))
    row.redeemed_at = now
    return [str(farm_id) for farm_id in sorted(farm_ids)]
