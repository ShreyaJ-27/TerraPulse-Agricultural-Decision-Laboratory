"""Scope private farms to their workspace credentials."""

import sqlalchemy as sa
from alembic import op

revision = "0006_workspace_access"
down_revision = "0005_farmer_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("farms", sa.Column("workspace_key_hash", sa.String(64), nullable=True))
    op.create_index("ix_farms_workspace_key_hash", "farms", ["workspace_key_hash"])


def downgrade() -> None:
    op.drop_index("ix_farms_workspace_key_hash", table_name="farms")
    op.drop_column("farms", "workspace_key_hash")
