"""Persist environmental snapshots and simulation execution metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0002_scientific_integration"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    snapshot_columns = {item["name"] for item in inspector.get_columns("environmental_snapshots")}
    if "plot_id" not in snapshot_columns:
        op.add_column("environmental_snapshots", sa.Column("plot_id", sa.Uuid(), nullable=True))
    if "ix_environmental_snapshots_plot_id" not in {
        index["name"] for index in inspector.get_indexes("environmental_snapshots")
    }:
        op.create_index("ix_environmental_snapshots_plot_id", "environmental_snapshots", ["plot_id"])
    if "fk_environmental_snapshots_plot_id" not in {
        fk["name"] for fk in inspector.get_foreign_keys("environmental_snapshots")
    }:
        op.create_foreign_key(
            "fk_environmental_snapshots_plot_id",
            "environmental_snapshots",
            "plots",
            ["plot_id"],
            ["id"],
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
    run_columns = {item["name"] for item in inspector.get_columns("simulation_runs")}
    for name, type_, nullable in columns:
        if name not in run_columns:
            op.add_column(
                "simulation_runs",
                sa.Column(
                    name,
                    type_,
                    nullable=nullable,
                    server_default="[]" if name == "warnings" else None,
                ),
            )
    if "ix_simulation_runs_environmental_snapshot_id" not in {
        index["name"] for index in inspector.get_indexes("simulation_runs")
    }:
        op.create_index(
            "ix_simulation_runs_environmental_snapshot_id",
            "simulation_runs",
            ["environmental_snapshot_id"],
        )
    if "fk_simulation_runs_environmental_snapshot_id" not in {
        fk["name"] for fk in inspector.get_foreign_keys("simulation_runs")
    }:
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
