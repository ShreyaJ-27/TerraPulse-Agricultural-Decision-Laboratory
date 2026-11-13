"""Create the original application schema without consulting live ORM metadata."""

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


_SCHEMA = (
    """CREATE TABLE farms (
    id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    timezone VARCHAR(64) NOT NULL,
    location geometry(POINT,4326) NOT NULL,
    boundary geometry(MULTIPOLYGON,4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
)""",
    """CREATE INDEX ix_farms_location ON farms USING gist (location)""",
    """CREATE TABLE crop_identities (
    id UUID NOT NULL,
    canonical_name VARCHAR(200) NOT NULL,
    scientific_name VARCHAR(200),
    aliases JSONB NOT NULL,
    provenance JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (canonical_name)
)""",
    """CREATE TABLE plots (
    id UUID NOT NULL,
    farm_id UUID NOT NULL,
    area_m2 NUMERIC(14, 3) NOT NULL,
    geometry geometry(MULTIPOLYGON,4326),
    crop_id UUID,
    planting_date DATE,
    management JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(farm_id) REFERENCES farms (id) ON DELETE CASCADE,
    FOREIGN KEY(crop_id) REFERENCES crop_identities (id) ON DELETE SET NULL
)""",
    """CREATE INDEX ix_plots_geometry ON plots USING gist (geometry)""",
    """CREATE INDEX ix_plots_farm_id ON plots (farm_id)""",
    """CREATE TABLE environmental_snapshots (
    id UUID NOT NULL,
    farm_id UUID NOT NULL,
    payload JSONB NOT NULL,
    availability VARCHAR(20) NOT NULL,
    input_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(farm_id) REFERENCES farms (id),
    UNIQUE (input_hash)
)""",
    """CREATE INDEX ix_environmental_snapshots_farm_id ON environmental_snapshots (farm_id)""",
    """CREATE TABLE decision_branches (
    id UUID NOT NULL,
    farm_id UUID NOT NULL,
    parent_branch_id UUID,
    base_snapshot_hash VARCHAR(128) NOT NULL,
    effective_date DATE NOT NULL,
    weather_member_id VARCHAR(100),
    model_version VARCHAR(100) NOT NULL,
    input_hashes JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(farm_id) REFERENCES farms (id),
    FOREIGN KEY(parent_branch_id) REFERENCES decision_branches (id)
)""",
    """CREATE INDEX ix_decision_branches_farm_id ON decision_branches (farm_id)""",
    """CREATE TABLE model_capabilities (
    id UUID NOT NULL,
    crop_id UUID NOT NULL,
    engine_name VARCHAR(100) NOT NULL,
    engine_version VARCHAR(100) NOT NULL,
    supported_outputs JSONB NOT NULL,
    parameters JSONB NOT NULL,
    limitations JSONB NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(crop_id) REFERENCES crop_identities (id)
)""",
    """CREATE INDEX ix_model_capabilities_crop_id ON model_capabilities (crop_id)""",
    """CREATE TABLE farm_resources (
    id UUID NOT NULL,
    farm_id UUID NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    opening_volume NUMERIC(16, 3) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(farm_id) REFERENCES farms (id)
)""",
    """CREATE INDEX ix_farm_resources_farm_id ON farm_resources (farm_id)""",
    """CREATE TABLE environmental_provenance (
    id UUID NOT NULL,
    snapshot_id UUID NOT NULL,
    source_id VARCHAR(200) NOT NULL,
    source_version VARCHAR(100),
    retrieved_at TIMESTAMP WITH TIME ZONE NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(snapshot_id) REFERENCES environmental_snapshots (id) ON DELETE CASCADE
)""",
    """CREATE INDEX ix_environmental_provenance_snapshot_id ON environmental_provenance (snapshot_id)""",
    """CREATE TABLE simulation_runs (
    id UUID NOT NULL,
    farm_id UUID NOT NULL,
    plot_id UUID NOT NULL,
    branch_id UUID NOT NULL,
    engine_name VARCHAR(100) NOT NULL,
    engine_version VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL,
    input_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(farm_id) REFERENCES farms (id),
    FOREIGN KEY(plot_id) REFERENCES plots (id),
    FOREIGN KEY(branch_id) REFERENCES decision_branches (id)
)""",
    """CREATE INDEX ix_simulation_runs_branch_id ON simulation_runs (branch_id)""",
    """CREATE INDEX ix_simulation_runs_plot_id ON simulation_runs (plot_id)""",
    """CREATE INDEX ix_simulation_runs_farm_id ON simulation_runs (farm_id)""",
    """CREATE TABLE branch_decisions (
    id UUID NOT NULL,
    branch_id UUID NOT NULL,
    decision_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(branch_id) REFERENCES decision_branches (id) ON DELETE CASCADE
)""",
    """CREATE INDEX ix_branch_decisions_branch_id ON branch_decisions (branch_id)""",
    """CREATE TABLE simulation_comparisons (
    id UUID NOT NULL,
    branch_a_id UUID NOT NULL,
    branch_b_id UUID NOT NULL,
    comparison_date DATE NOT NULL,
    matched_inputs BOOLEAN NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (branch_a_id, branch_b_id, comparison_date),
    FOREIGN KEY(branch_a_id) REFERENCES decision_branches (id),
    FOREIGN KEY(branch_b_id) REFERENCES decision_branches (id)
)""",
    """CREATE INDEX ix_simulation_comparisons_branch_b_id ON simulation_comparisons (branch_b_id)""",
    """CREATE INDEX ix_simulation_comparisons_branch_a_id ON simulation_comparisons (branch_a_id)""",
    """CREATE TABLE model_parameter_provenance (
    id UUID NOT NULL,
    capability_id UUID NOT NULL,
    source_id VARCHAR(200) NOT NULL,
    source_version VARCHAR(100),
    payload JSONB NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(capability_id) REFERENCES model_capabilities (id) ON DELETE CASCADE
)""",
    """CREATE INDEX ix_model_parameter_provenance_capability_id ON model_parameter_provenance (capability_id)""",
    """CREATE TABLE resource_ledgers (
    id UUID NOT NULL,
    resource_id UUID NOT NULL,
    branch_id UUID NOT NULL,
    payload JSONB NOT NULL,
    closing_volume NUMERIC(16, 3) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(resource_id) REFERENCES farm_resources (id) ON DELETE CASCADE,
    FOREIGN KEY(branch_id) REFERENCES decision_branches (id)
)""",
    """CREATE INDEX ix_resource_ledgers_branch_id ON resource_ledgers (branch_id)""",
    """CREATE INDEX ix_resource_ledgers_resource_id ON resource_ledgers (resource_id)""",
    """CREATE TABLE scientific_states (
    id UUID NOT NULL,
    simulation_run_id UUID NOT NULL,
    plot_id UUID NOT NULL,
    branch_id UUID NOT NULL,
    state_date DATE NOT NULL,
    payload JSONB NOT NULL,
    availability VARCHAR(20) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(simulation_run_id) REFERENCES simulation_runs (id) ON DELETE CASCADE,
    FOREIGN KEY(plot_id) REFERENCES plots (id),
    FOREIGN KEY(branch_id) REFERENCES decision_branches (id)
)""",
    """CREATE INDEX ix_scientific_states_plot_id ON scientific_states (plot_id)""",
    """CREATE INDEX ix_scientific_states_branch_id ON scientific_states (branch_id)""",
    """CREATE INDEX ix_scientific_states_simulation_run_id ON scientific_states (simulation_run_id)""",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    for statement in _SCHEMA:
        op.execute(statement)


def downgrade() -> None:
    op.drop_table("scientific_states")
    op.drop_table("simulation_runs")
    op.drop_table("simulation_comparisons")
    op.drop_table("resource_ledgers")
    op.drop_table("model_parameter_provenance")
    op.drop_table("environmental_provenance")
    op.drop_table("branch_decisions")
    op.drop_table("plots")
    op.drop_table("model_capabilities")
    op.drop_table("farm_resources")
    op.drop_table("environmental_snapshots")
    op.drop_table("decision_branches")
    op.drop_table("farms")
    op.drop_table("crop_identities")
