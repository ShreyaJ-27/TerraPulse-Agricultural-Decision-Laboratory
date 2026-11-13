"""Audit pitch scenario sends separately from real agronomic advisories."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009_pitch_alert_receipts"
down_revision = "0008_telegram_webhook_updates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_pitch_sends",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("farm_id", UUID(as_uuid=True), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("telegram_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scenario", sa.String(48), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farm_id", "request_id", name="uq_pitch_farm_request"),
    )
    op.create_index("ix_pitch_farm_created", "telegram_pitch_sends", ["farm_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_pitch_farm_created", table_name="telegram_pitch_sends")
    op.drop_table("telegram_pitch_sends")
