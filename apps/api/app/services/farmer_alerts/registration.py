"""One-click Telegram linking from TerraPulse's existing farm-registration response.

A fresh farm registration is the trusted context. Existing farms must not gain
an unauthenticated endpoint to issue arbitrary new links.
"""
from __future__ import annotations
import logging
import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from .persistence import issue_link
from .telegram import create_deep_link

log = logging.getLogger("terrapulse.farmer_alerts")


async def link_for_newly_registered_farm(session: AsyncSession, farm_id: UUID) -> str | None:
    """Generate an optional, short-lived deep link without blocking registration.

    This function must be called server-side immediately after a successful
    CREATE of that farm, not from a GET endpoint or from a caller-supplied ID.
    """
    username = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()
    if not username:
        return None
    try:
        token = await issue_link(session, farm_id=farm_id, ownership_verified=True)
        return create_deep_link(username, token)
    except Exception as exc:
        # Telegram is optional. A DB-migration or bot configuration problem
        # must not prevent the farmer from registering a farm.
        await session.rollback()
        log.warning("Telegram connection currently unavailable: %s", type(exc).__name__)
        return None
