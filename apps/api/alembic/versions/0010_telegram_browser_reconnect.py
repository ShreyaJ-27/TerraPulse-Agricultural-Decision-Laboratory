"""Single-use Telegram-issued access to an existing private farm workspace.

Schema matches the integration Neon revision observed on 2026-11-14.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0010_telegram_browser_reconnect"
down_revision = "0009_pitch_alert_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "farm_workspace_grants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("farm_id", UUID(as_uuid=True), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farm_id", "token_hash", name="uq_farm_workspace_grant"),
    )
    op.create_index("ix_workspace_grant_token", "farm_workspace_grants", ["token_hash"])
    op.create_table(
        "telegram_browser_reconnects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("poll_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("client_hash", sa.String(64), nullable=False),
        sa.Column("farm_id", UUID(as_uuid=True), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=True),
        sa.Column("approved_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("approved_user_id", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_browser_reconnect_client_created", "telegram_browser_reconnects", ["client_hash", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_browser_reconnect_client_created", table_name="telegram_browser_reconnects")
    op.drop_table("telegram_browser_reconnects")
    op.drop_index("ix_workspace_grant_token", table_name="farm_workspace_grants")
    op.drop_table("farm_workspace_grants")
