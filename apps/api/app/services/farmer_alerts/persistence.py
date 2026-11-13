"""Atomic PostgreSQL operations for one-tap, opt-in farmer notifications.

Link codes must be issued by an authorized server-side registration operation,
never by a public API accepting arbitrary farm IDs. No complex farmer login is
required to click a one-time Telegram connection during registration.
"""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, update, or_, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .decision import AdvisoryEvent
from .models import (FarmerAlert, TelegramDelivery, TelegramLink, TelegramSubscription,
                     TelegramUpdateCursor, TelegramWebhookUpdate)

DEFAULT_CATEGORIES = {"calendar": True, "weather": True, "science": True}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


async def issue_link(session: AsyncSession, *, farm_id: UUID, ownership_verified: bool,
                     ttl_minutes: int = 15) -> str:
    """Only a trusted caller can mint a one-time secret. Never exposed as an open API."""
    if not ownership_verified:
        raise PermissionError("Farm ownership verification is required before issuing a link")
    if not 1 <= ttl_minutes <= 30:
        raise ValueError("link expiry must be 1-30 minutes")
    from app.models import Farm
    if await session.get(Farm, farm_id) is None:
        raise ValueError("unknown farm")
    token = secrets.token_urlsafe(24)  # base64url, 32 chars, within Telegram's 64-char limit
    session.add(TelegramLink(id=uuid4(), farm_id=farm_id, token_hash=token_digest(token),
                             expires_at=now_utc()+timedelta(minutes=ttl_minutes), created_at=now_utc()))
    await session.commit()
    return token


async def consume_link(session: AsyncSession, *, token: str, chat_id: int, user_id: int,
                       locale: str = "en", timezone_name: str | None = None) -> UUID | None:
    """One-use token consumption with row lock; command must come from private chat."""
    if not isinstance(chat_id, int) or not isinstance(user_id, int) or chat_id <= 0 or user_id <= 0:
        return None
    if not (16 <= len(token) <= 64) or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in token):
        return None
    if locale not in {"en", "hi", "kn"}:
        locale = "en"
    intent = await session.scalar(select(TelegramLink).where(
        TelegramLink.token_hash == token_digest(token), TelegramLink.used_at.is_(None),
        TelegramLink.expires_at > now_utc()).with_for_update())
    if intent is None:
        return None
    from app.models import Farm
    farm = await session.get(Farm, intent.farm_id)
    if farm is None:
        return None
    timezone_name = timezone_name or farm.timezone
    try:
        ZoneInfo(timezone_name)
    except (ValueError, KeyError):
        timezone_name = "Asia/Kolkata"
    existing = await session.scalar(select(TelegramSubscription).where(
        TelegramSubscription.farm_id == intent.farm_id, TelegramSubscription.chat_id == chat_id
    ).with_for_update())
    if existing is None:
        session.add(TelegramSubscription(id=uuid4(), farm_id=intent.farm_id,
                    chat_id=chat_id, user_id=user_id, active=True,
                    categories=dict(DEFAULT_CATEGORIES), locale=locale, timezone=timezone_name,
                    created_at=now_utc(), updated_at=now_utc()))
    else:
        # Preserve changed preferences when a farmer reconnects.
        existing.user_id = user_id
        existing.active = True
        existing.updated_at = now_utc()
    intent.used_at = now_utc()
    intent.used_chat_id = chat_id
    return intent.farm_id


async def subscriptions_for_chat(session: AsyncSession, chat_id: int) -> list[TelegramSubscription]:
    return list((await session.scalars(select(TelegramSubscription)
                 .where(TelegramSubscription.chat_id == chat_id)
                 .order_by(TelegramSubscription.created_at))).all())


async def resume_subscriptions(session: AsyncSession, chat_id: int) -> int:
    """A returning farmer can turn alerts back on with /start, no relinking."""
    result = await session.execute(update(TelegramSubscription)
        .where(TelegramSubscription.chat_id == chat_id, TelegramSubscription.active.is_(False))
        .values(active=True, updated_at=now_utc()))
    return result.rowcount


async def unsubscribe(session: AsyncSession, chat_id: int) -> int:
    """Stop future sends and cancel queued messages, not only flip a flag."""
    ids = select(TelegramSubscription.id).where(TelegramSubscription.chat_id == chat_id)
    result = await session.execute(update(TelegramSubscription)
                   .where(TelegramSubscription.chat_id == chat_id, TelegramSubscription.active.is_(True))
                   .values(active=False, updated_at=now_utc()))
    await session.execute(update(TelegramDelivery).where(
        TelegramDelivery.subscription_id.in_(ids),
        TelegramDelivery.status.in_(("pending", "sending"))).values(
        status="cancelled", lease_until=None, updated_at=now_utc()))
    return result.rowcount


async def change_preference(session: AsyncSession, chat_id: int, *,
                            category: str | None = None, enabled: bool | None = None,
                            locale: str | None = None) -> int:
    if category is not None and (category not in DEFAULT_CATEGORIES or enabled is None):
        raise ValueError("unsupported alert preference")
    if locale is not None and locale not in {"en", "hi", "kn"}:
        raise ValueError("unsupported language")
    rows = await session.scalars(select(TelegramSubscription)
        .where(TelegramSubscription.chat_id == chat_id, TelegramSubscription.active.is_(True))
        .with_for_update())
    changed = 0
    for sub in rows:
        if category is not None:
            sub.categories = {**sub.categories, category: enabled}
        if locale is not None:
            sub.locale = locale
        sub.updated_at = now_utc()
        changed += 1
    return changed


async def claim_webhook_update(session: AsyncSession, update_id: int) -> bool:
    """Claim once, in the same transaction as the command."""
    stmt = pg_insert(TelegramWebhookUpdate).values(update_id=update_id)
    claimed = await session.scalar(stmt.on_conflict_do_nothing().returning(
        TelegramWebhookUpdate.update_id
    ))
    return claimed is not None


async def get_cursor(session: AsyncSession) -> int:
    cursor = await session.get(TelegramUpdateCursor, 1)
    return int(cursor.next_update_id) if cursor else 0


async def advance_cursor(session: AsyncSession, update_id: int) -> None:
    # Monotonic update, protecting against replayed Telegram messages.
    stmt = pg_insert(TelegramUpdateCursor).values(id=1, next_update_id=update_id + 1)
    stmt = stmt.on_conflict_do_update(index_elements=[TelegramUpdateCursor.id],
        set_={"next_update_id": __import__("sqlalchemy").func.greatest(
            TelegramUpdateCursor.next_update_id, update_id+1)})
    await session.execute(stmt)
    await session.commit()


async def enqueue_events(session: AsyncSession, events: list[AdvisoryEvent]) -> tuple[int, int]:
    """Idempotent event + per-subscription delivery rows via PostgreSQL unique keys."""
    new_events = new_deliveries = 0
    for event in events:
        stmt = pg_insert(FarmerAlert).values(
            id=uuid4(), dedupe_key=event.dedupe_key, farm_id=event.farm_id,
            plot_id=event.plot_id, category=event.category, kind=event.kind,
            event_date=event.event_date, evidence_hash=event.evidence_hash,
            payload=event.payload(), created_at=now_utc())
        alert_id = await session.scalar(stmt.on_conflict_do_nothing(
            index_elements=[FarmerAlert.dedupe_key]).returning(FarmerAlert.id))
        if alert_id is None:
            alert_id = await session.scalar(select(FarmerAlert.id).where(
                FarmerAlert.dedupe_key == event.dedupe_key))
        else:
            new_events += 1
        rows = await session.scalars(select(TelegramSubscription).where(
            TelegramSubscription.farm_id == event.farm_id,
            TelegramSubscription.active.is_(True)))
        for sub in rows:
            if not (sub.categories or {}).get(event.category, False):
                continue
            delivery_stmt = pg_insert(TelegramDelivery).values(
                id=uuid4(), alert_id=alert_id, subscription_id=sub.id,
                status="pending", attempts=0, next_attempt_at=now_utc(), updated_at=now_utc())
            delivery_id = await session.scalar(delivery_stmt.on_conflict_do_nothing(
                index_elements=[TelegramDelivery.alert_id, TelegramDelivery.subscription_id]).returning(TelegramDelivery.id))
            new_deliveries += int(delivery_id is not None)
    await session.commit()
    return new_events, new_deliveries


def quiet_now(sub: TelegramSubscription, now: datetime) -> bool:
    local_hour = now.astimezone(ZoneInfo(sub.timezone)).hour
    start, end = sub.quiet_start_hour, sub.quiet_end_hour
    if start == end:
        return False
    return start <= local_hour < end if start < end else local_hour >= start or local_hour < end


async def claim_deliveries(session: AsyncSession, *, limit: int = 30, ignore_quiet: bool = False):
    """Lease outbox jobs; a crash after send but before ack may cause a resend.

    Application dedup is enforced, but Telegram has no general sendMessage
    idempotency token: exactly-once external delivery cannot be guaranteed.
    """
    clock = now_utc()
    stmt = select(TelegramDelivery, TelegramSubscription, FarmerAlert).join(
        TelegramSubscription, TelegramDelivery.subscription_id == TelegramSubscription.id
    ).join(FarmerAlert, TelegramDelivery.alert_id == FarmerAlert.id).where(
        TelegramSubscription.active.is_(True),
        TelegramDelivery.next_attempt_at <= clock,
        or_(TelegramDelivery.status == "pending", and_(TelegramDelivery.status == "sending",
              TelegramDelivery.lease_until < clock)),
    ).order_by(TelegramDelivery.next_attempt_at).limit(limit).with_for_update(
        of=TelegramDelivery, skip_locked=True)
    items = list((await session.execute(stmt)).all())
    chosen = []
    for delivery, sub, event in items:
        if not (sub.categories or {}).get(event.category, False):
            delivery.status = "suppressed"
            continue
        # Avoid delivering yesterday's weather or science as if it were current.
        # Calendar reminders get a one-day grace window after a quiet period.
        try:
            local_today = clock.astimezone(ZoneInfo(sub.timezone)).date()
        except (ValueError, KeyError):
            local_today = clock.date()
        age_days = (local_today - event.event_date).days
        if (event.category in ("weather", "science") and age_days > 0) or (event.category == "calendar" and age_days > 1):
            delivery.status = "expired"
            continue
        if not ignore_quiet and quiet_now(sub, clock):
            delivery.next_attempt_at = clock + timedelta(minutes=30)
            continue
        delivery.status = "sending"
        delivery.lease_until = clock + timedelta(minutes=3)
        delivery.attempts += 1
        chosen.append((delivery.id, sub.chat_id, sub.locale, event.payload))
    await session.commit()
    return chosen


async def ack_delivery(session: AsyncSession, delivery_id: UUID, *,
                       message_id: int | None = None, error_code: str | None = None,
                       retry_after: int | None = None) -> None:
    row = await session.get(TelegramDelivery, delivery_id)
    if row is None or row.status != "sending":
        return
    if message_id is not None:
        row.status = "sent"
        row.telegram_message_id = message_id
        row.last_error = None
    elif error_code in ("BOT_BLOCKED", "BAD_REQUEST", "INVALID_CHAT"):
        row.status = "failed"
        row.last_error = error_code
        sub = await session.get(TelegramSubscription, row.subscription_id)
        if sub and error_code == "BOT_BLOCKED":
            await session.execute(update(TelegramSubscription).where(
                TelegramSubscription.chat_id == sub.chat_id).values(active=False))
    else:
        row.last_error = (error_code or "DELIVERY_ERROR")[:160]
        if row.attempts >= 5:
            row.status = "failed"
        else:
            row.status = "pending"
            backoff = min(3600, 30 * (2 ** max(0, row.attempts - 1)))
            row.next_attempt_at = now_utc() + timedelta(seconds=max(backoff, retry_after or 0))
    row.lease_until = None
    row.updated_at = now_utc()
    await session.commit()
