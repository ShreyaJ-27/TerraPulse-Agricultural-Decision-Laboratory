"""Persistent opt-in Telegram links, subscriptions, alert identities and outbox.

Import these models only in the feature worker; schema is created by migration 0005.
No live request or network activity occurs on import.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import (BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer,
                        JSON, String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TelegramLink(Base):
    __tablename__ = "telegram_link_intents"
    __table_args__ = (
        Index("ix_telegram_link_farm", "farm_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class TelegramSubscription(Base):
    __tablename__ = "telegram_subscriptions"
    __table_args__ = (
        UniqueConstraint("farm_id", "chat_id", name="uq_telegram_farm_chat"),
        Index("ix_telegram_sub_farm", "farm_id"),
        Index("ix_telegram_sub_chat", "chat_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    locale: Mapped[str] = mapped_column(String(5), default="en")
    categories: Mapped[dict] = mapped_column(JSON, default=lambda: {"calendar": True, "weather": True, "science": True})
    quiet_start_hour: Mapped[int] = mapped_column(Integer, default=22)
    quiet_end_hour: Mapped[int] = mapped_column(Integer, default=7)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class FarmerAlert(Base):
    __tablename__ = "farmer_alerts"
    __table_args__ = (
        Index("ix_alert_farm", "farm_id"),
        Index("ix_alert_plot", "plot_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dedupe_key: Mapped[str] = mapped_column(String(64), unique=True)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(80))
    event_date: Mapped[date] = mapped_column(Date)
    evidence_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class TelegramDelivery(Base):
    __tablename__ = "telegram_deliveries"
    __table_args__ = (
        UniqueConstraint("alert_id", "subscription_id", name="uq_telegram_delivery"),
        Index("ix_delivery_alert", "alert_id"),
        Index("ix_delivery_subscription", "subscription_id"),
        Index("ix_delivery_status", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("farmer_alerts.id", ondelete="CASCADE"))
    subscription_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_subscriptions.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class TelegramUpdateCursor(Base):
    __tablename__ = "telegram_update_cursor"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_update_id: Mapped[int] = mapped_column(BigInteger, default=0)


class TelegramWebhookUpdate(Base):
    __tablename__ = "telegram_webhook_updates"
    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)


class PitchAlertSend(Base):
    """Logged scenario messages, distinct from real evidence-backed advisories."""
    __tablename__ = "telegram_pitch_sends"
    __table_args__ = (
        UniqueConstraint("farm_id", "request_id", name="uq_pitch_farm_request"),
        Index("ix_pitch_farm_created", "farm_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    subscription_id: Mapped[UUID] = mapped_column(ForeignKey("telegram_subscriptions.id", ondelete="CASCADE"))
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    scenario: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
