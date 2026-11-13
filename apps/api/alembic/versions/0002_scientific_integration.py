"""Persist environmental snapshots and simulation execution metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0002_scientific_integration"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("environmental_snapshots", sa.Column("plot_id", sa.Uuid(), nullable=True))
    op.create_index("ix_environmental_snapshots_plot_id", "environmental_snapshots", ["plot_id"])
    op.create_foreign_key(
        "fk_environmental_snapshots_plot_id", "environmental_snapshots", "plots", ["plot_id"], ["id"]
    )
    columns = [
        ("environmental_snapshot_id", sa.Uuid(), True),
        ("parameter_version", sa.String(100), True),
        ("weather_realization_id", sa.String(200), True),
        ("weather_member_id", sa.String(100), True),
        ("requested_at", sa.DateTime(timezone=True), True),
        ("started_at", sa.DateTime(timezone=True), True),
        ("completed_at", sa.DateTime(timezone=True), True),
        ("warnings", sa.JSON(), False),
        ("error_code", sa.String(100), True),
        ("error_message", sa.String(1000), True),
        ("science_envelope", sa.JSON(), True),
        ("input_provenance", sa.JSON(), True),
    ]
    for name, type_, nullable in columns:
        op.add_column("simulation_runs", sa.Column(name, type_, nullable=nullable, server_default="[]" if name == "warnings" else None))
    op.create_index("ix_simulation_runs_environmental_snapshot_id", "simulation_runs", ["environmental_snapshot_id"])
    op.create_foreign_key(
        "fk_simulation_runs_environmental_snapshot_id",
        "simulation_runs",
        "environmental_snapshots",
        ["environmental_snapshot_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_simulation_runs_environmental_snapshot_id", "simulation_runs", type_="foreignkey")
    op.drop_index("ix_simulation_runs_environmental_snapshot_id", table_name="simulation_runs")
    for name in (
        "input_provenance", "science_envelope", "error_message", "error_code", "warnings",
        "completed_at", "started_at", "requested_at", "weather_member_id",
        "weather_realization_id", "parameter_version", "environmental_snapshot_id",
    ):
        op.drop_column("simulation_runs", name)
    op.drop_constraint("fk_environmental_snapshots_plot_id", "environmental_snapshots", type_="foreignkey")
    op.drop_index("ix_environmental_snapshots_plot_id", table_name="environmental_snapshots")
    op.drop_column("environmental_snapshots", "plot_id")
