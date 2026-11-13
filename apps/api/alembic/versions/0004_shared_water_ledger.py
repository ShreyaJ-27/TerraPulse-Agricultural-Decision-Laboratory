"""Add branch-scoped shared-water resources and append-only allocations."""

import sqlalchemy as sa
from alembic import op

revision = "0004_shared_water_ledger"
down_revision = "0003_branches_comparisons_timeline"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _add(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add("farm_resources", sa.Column("name", sa.String(200), nullable=True))
    _add("farm_resources", sa.Column("metadata", sa.JSON(), nullable=True))
    _add("farm_resources", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    _add("farm_resources", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    _add("resource_ledgers", sa.Column("version", sa.Integer(), nullable=True))
    _add("resource_ledgers", sa.Column("ledger_hash", sa.String(128), nullable=True))
    _add("resource_ledgers", sa.Column("parent_ledger_id", sa.Uuid(), nullable=True))
    _add("resource_ledgers", sa.Column("validation_status", sa.String(30), nullable=True))
    _add("resource_ledgers", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    _add("resource_ledgers", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

    inspector = sa.inspect(op.get_bind())
    if "resource_plot_authorizations" not in inspector.get_table_names():
        op.create_table(
            "resource_plot_authorizations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("farm_resources.id"), nullable=False),
            sa.Column("plot_id", sa.Uuid(), sa.ForeignKey("plots.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("resource_id", "plot_id"),
        )
        op.create_index("ix_resource_plot_authorizations_resource_id", "resource_plot_authorizations", ["resource_id"])
        op.create_index("ix_resource_plot_authorizations_plot_id", "resource_plot_authorizations", ["plot_id"])

    if "resource_allocations" not in inspector.get_table_names():
        op.create_table(
            "resource_allocations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("farm_resources.id"), nullable=False),
            sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("decision_branches.id"), nullable=False),
            sa.Column("plot_id", sa.Uuid(), sa.ForeignKey("plots.id"), nullable=False),
            sa.Column("allocation_id", sa.String(200), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False),
            sa.Column("allocation_date", sa.Date(), nullable=False),
            sa.Column("requested_litres", sa.Numeric(16, 6), nullable=False),
            sa.Column("withdrawn_litres", sa.Numeric(16, 6), nullable=False),
            sa.Column("effective_litres", sa.Numeric(16, 6), nullable=False),
            sa.Column("loss_litres", sa.Numeric(16, 6), nullable=False),
            sa.Column("measurement_provenance", sa.JSON(), nullable=False),
            sa.Column("inherited", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("source_allocation_id", sa.Uuid(), sa.ForeignKey("resource_allocations.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("resource_id", "branch_id", "allocation_id"),
            sa.UniqueConstraint("resource_id", "branch_id", "idempotency_key"),
        )
        op.create_index("ix_resource_allocations_resource_id", "resource_allocations", ["resource_id"])
        op.create_index("ix_resource_allocations_branch_id", "resource_allocations", ["branch_id"])
        op.create_index("ix_resource_allocations_plot_id", "resource_allocations", ["plot_id"])
        op.create_index("ix_resource_allocations_allocation_date", "resource_allocations", ["allocation_date"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "resource_allocations" in inspector.get_table_names():
        op.drop_table("resource_allocations")
    if "resource_plot_authorizations" in inspector.get_table_names():
        op.drop_table("resource_plot_authorizations")
    for name in ("updated_at", "created_at", "validation_status", "parent_ledger_id", "ledger_hash", "version"):
        if name in _columns("resource_ledgers"):
            op.drop_column("resource_ledgers", name)
    for name in ("updated_at", "created_at", "metadata", "name"):
        if name in _columns("farm_resources"):
            op.drop_column("farm_resources", name)
