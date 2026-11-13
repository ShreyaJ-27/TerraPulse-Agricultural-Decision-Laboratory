"""Store processed webhook update IDs for transactional deduplication."""

import sqlalchemy as sa
from alembic import op

revision = "0008_telegram_webhook_updates"
down_revision = "0007_align_legacy_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_webhook_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True, autoincrement=False),
    )


def downgrade() -> None:
    op.drop_table("telegram_webhook_updates")
