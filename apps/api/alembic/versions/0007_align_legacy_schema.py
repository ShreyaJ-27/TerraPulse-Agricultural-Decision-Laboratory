"""Reconcile nullable legacy columns, indexes and PostgreSQL types with the models.

Older revisions could have been installed either through live ORM metadata or
through incremental DDL. Only backfill values that can be derived from records.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_align_legacy_schema"
down_revision = "0006_workspace_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE decision_branches b SET plot_id = derived.plot_id
        FROM (
            SELECT branch_id, min(plot_id::text)::uuid AS plot_id
            FROM simulation_runs GROUP BY branch_id HAVING count(DISTINCT plot_id) = 1
        ) derived
        WHERE b.id = derived.branch_id AND b.plot_id IS NULL
    """)
    op.execute("""
        UPDATE simulation_comparisons c SET
            farm_id = COALESCE(c.farm_id, a.farm_id),
            plot_id = COALESCE(c.plot_id, a.plot_id),
            run_a_id = COALESCE(c.run_a_id, ra.id),
            run_b_id = COALESCE(c.run_b_id, rb.id)
        FROM decision_branches a, decision_branches b,
            simulation_runs ra, simulation_runs rb
        WHERE a.id = c.branch_a_id AND b.id = c.branch_b_id
            AND a.farm_id = b.farm_id AND a.plot_id = b.plot_id
            AND ra.branch_id = a.id AND rb.branch_id = b.id
            AND (SELECT count(*) FROM simulation_runs WHERE branch_id = a.id) = 1
            AND (SELECT count(*) FROM simulation_runs WHERE branch_id = b.id) = 1
    """)
    for table, column, value in (
        ("decision_branches", "decision_type", "'baseline'"),
        ("decision_branches", "decision_diff", "'{}'"),
        ("simulation_comparisons", "status", "'completed'"),
        ("simulation_comparisons", "non_comparable_reasons", "'[]'"),
        ("farm_resources", "name", "resource_type"),
        ("farm_resources", "metadata", "'{}'"),
        ("resource_ledgers", "version", "1"),
        ("resource_ledgers", "ledger_hash", "encode(sha256(convert_to(payload::text, 'UTF8')), 'hex')"),
        ("resource_ledgers", "validation_status", "'valid'"),
    ):
        op.execute(f"UPDATE {table} SET {column} = {value} WHERE {column} IS NULL")
        op.alter_column(table, column, nullable=False)

    for table, column in (
        ("decision_branches", "plot_id"),
        ("simulation_comparisons", "farm_id"),
        ("simulation_comparisons", "plot_id"),
        ("simulation_comparisons", "run_a_id"),
        ("simulation_comparisons", "run_b_id"),
    ):
        # If a legacy record cannot be linked unambiguously, retain it and fail
        # the migration transaction rather than assigning it to a guessed plot.
        op.alter_column(table, column, nullable=False)
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_{column} ON {table} ({column})")

    for table, columns in (
        ("simulation_runs", ("warnings", "science_envelope", "input_provenance")),
        ("decision_branches", ("decision_diff",)),
        ("simulation_comparisons", ("non_comparable_reasons",)),
        ("timeline_events", ("payload",)),
        ("farm_resources", ("metadata",)),
        ("resource_allocations", ("measurement_provenance",)),
    ):
        for column in columns:
            op.alter_column(table, column, type_=JSONB(), postgresql_using=f"{column}::jsonb")
    op.alter_column("farm_resources", "opening_volume", type_=sa.Numeric(16, 6))
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'resource_ledgers'::regclass
                    AND confrelid = 'resource_ledgers'::regclass
                    AND contype = 'f'
            ) THEN
                ALTER TABLE resource_ledgers ADD CONSTRAINT fk_resource_ledgers_parent
                    FOREIGN KEY (parent_ledger_id) REFERENCES resource_ledgers (id);
            END IF;
        END $$
    """)


def downgrade() -> None:
    # Keep normalized storage types and data. The prior revisions accept this
    # representation, and downgrading numeric precision could discard values.
    pass
