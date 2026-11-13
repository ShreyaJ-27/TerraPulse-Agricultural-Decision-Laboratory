"""Persist immutable branch decisions, timeline events and comparisons."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "0003_branches_timeline"
down_revision = "0002_scientific_integration"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if column.name not in {item["name"] for item in inspector.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "decision_branches",
        sa.Column("plot_id", sa.Uuid(), sa.ForeignKey("plots.id"), nullable=True),
    )
    _add_column_if_missing("decision_branches", sa.Column("decision_type", sa.String(100), nullable=True))
    _add_column_if_missing("decision_branches", sa.Column("decision_diff", JSONB(), nullable=True))
    _add_column_if_missing(
        "simulation_comparisons",
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id"), nullable=True),
    )
    _add_column_if_missing(
        "simulation_comparisons",
        sa.Column("plot_id", sa.Uuid(), sa.ForeignKey("plots.id"), nullable=True),
    )
    _add_column_if_missing(
        "simulation_comparisons",
        sa.Column("run_a_id", sa.Uuid(), sa.ForeignKey("simulation_runs.id"), nullable=True),
    )
    _add_column_if_missing(
        "simulation_comparisons",
        sa.Column("run_b_id", sa.Uuid(), sa.ForeignKey("simulation_runs.id"), nullable=True),
    )
    _add_column_if_missing(
        "simulation_comparisons", sa.Column("status", sa.String(30), nullable=True)
    )
    _add_column_if_missing(
        "simulation_comparisons", sa.Column("non_comparable_reasons", JSONB(), nullable=True)
    )
    inspector = sa.inspect(op.get_bind())
    if "timeline_events" not in inspector.get_table_names():
        op.create_table(
            "timeline_events",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id"), nullable=False),
            sa.Column("plot_id", sa.Uuid(), sa.ForeignKey("plots.id"), nullable=False),
            sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("decision_branches.id"), nullable=True),
            sa.Column("event_type", sa.String(100), nullable=False),
            sa.Column("event_date", sa.Date(), nullable=False),
            sa.Column("description", sa.String(500), nullable=False),
            sa.Column("payload", JSONB(), nullable=False),
        )
        op.create_index("ix_timeline_events_farm_id", "timeline_events", ["farm_id"])
        op.create_index("ix_timeline_events_plot_id", "timeline_events", ["plot_id"])
        op.create_index("ix_timeline_events_branch_id", "timeline_events", ["branch_id"])
        op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"])
        op.create_index("ix_timeline_events_event_date", "timeline_events", ["event_date"])


def downgrade() -> None:
    op.drop_index("ix_timeline_events_event_date", table_name="timeline_events")
    op.drop_index("ix_timeline_events_event_type", table_name="timeline_events")
    op.drop_index("ix_timeline_events_branch_id", table_name="timeline_events")
    op.drop_index("ix_timeline_events_plot_id", table_name="timeline_events")
    op.drop_index("ix_timeline_events_farm_id", table_name="timeline_events")
    op.drop_table("timeline_events")
    for name in (
        "non_comparable_reasons",
        "status",
        "run_b_id",
        "run_a_id",
        "plot_id",
        "farm_id",
    ):
        op.drop_column("simulation_comparisons", name)
    for name in ("decision_diff", "decision_type", "plot_id"):
        op.drop_column("decision_branches", name)
