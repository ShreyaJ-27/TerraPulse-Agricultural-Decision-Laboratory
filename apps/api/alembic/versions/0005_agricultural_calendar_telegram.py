"""Developer A: opt-in Telegram farmer alerts, event deduplication and outbox.

New additive tables only. Does not rewrite prior Alembic revision identifiers.
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_farmer_alerts"
down_revision = "0004_shared_water_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("telegram_link_intents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("used_chat_id", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_telegram_link_farm", "telegram_link_intents", ["farm_id"])
    op.create_table("telegram_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("locale", sa.String(5), nullable=False, server_default="en"),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("quiet_start_hour", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("quiet_end_hour", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farm_id", "chat_id", name="uq_telegram_farm_chat"),
    )
    op.create_index("ix_telegram_sub_farm", "telegram_subscriptions", ["farm_id"])
    op.create_index("ix_telegram_sub_chat", "telegram_subscriptions", ["chat_id"])
    op.create_table("farmer_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dedupe_key", sa.String(64), nullable=False, unique=True),
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plot_id", sa.Uuid(), sa.ForeignKey("plots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_farm", "farmer_alerts", ["farm_id"])
    op.create_index("ix_alert_plot", "farmer_alerts", ["plot_id"])
    op.create_table("telegram_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alert_id", sa.Uuid(), sa.ForeignKey("farmer_alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("telegram_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("telegram_message_id", sa.BigInteger()),
        sa.Column("last_error", sa.String(160)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("alert_id", "subscription_id", name="uq_telegram_delivery"),
    )
    op.create_index("ix_delivery_alert", "telegram_deliveries", ["alert_id"])
    op.create_index("ix_delivery_subscription", "telegram_deliveries", ["subscription_id"])
    op.create_index("ix_delivery_status", "telegram_deliveries", ["status"])
    op.create_table("telegram_update_cursor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("next_update_id", sa.BigInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("telegram_update_cursor")
    op.drop_table("telegram_deliveries")
    op.drop_table("farmer_alerts")
    op.drop_table("telegram_subscriptions")
    op.drop_table("telegram_link_intents")
