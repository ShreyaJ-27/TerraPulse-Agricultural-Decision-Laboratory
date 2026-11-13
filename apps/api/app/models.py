from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Farm(Timestamped, Base):
    __tablename__ = "farms"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64))
    location: Mapped[object] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False))
    boundary: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False)
    )
    workspace_key_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    plots: Mapped[list[Plot]] = relationship(back_populates="farm", cascade="all, delete-orphan")


class Plot(Timestamped, Base):
    __tablename__ = "plots"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    area_m2: Mapped[float] = mapped_column(Numeric(14, 3))
    geometry: Mapped[object | None] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False)
    )
    crop_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crop_identities.id", ondelete="SET NULL")
    )
    planting_date: Mapped[date | None] = mapped_column(Date)
    management: Mapped[dict] = mapped_column(JSONB, default=dict)
    farm: Mapped[Farm] = relationship(back_populates="plots")
    resource_assignments: Mapped[list[ResourcePlotAuthorization]] = relationship(
        back_populates="plot", cascade="all, delete-orphan"
    )


class CropIdentity(Timestamped, Base):
    __tablename__ = "crop_identities"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_name: Mapped[str] = mapped_column(String(200), unique=True)
    scientific_name: Mapped[str | None] = mapped_column(String(200))
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    provenance: Mapped[list] = mapped_column(JSONB, default=list)


class EnvironmentalSnapshot(Timestamped, Base):
    __tablename__ = "environmental_snapshots"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), index=True)
    plot_id: Mapped[UUID | None] = mapped_column(ForeignKey("plots.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    availability: Mapped[str] = mapped_column(String(20))
    input_hash: Mapped[str] = mapped_column(String(128), unique=True)


class EnvironmentalProvenance(Base):
    __tablename__ = "environmental_provenance"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("environmental_snapshots.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(String(200))
    source_version: Mapped[str | None] = mapped_column(String(100))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class SimulationRun(Timestamped, Base):
    __tablename__ = "simulation_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), index=True)
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    engine_name: Mapped[str] = mapped_column(String(100))
    engine_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    input_hash: Mapped[str] = mapped_column(String(128))
    environmental_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("environmental_snapshots.id"), index=True
    )
    parameter_version: Mapped[str | None] = mapped_column(String(100))
    weather_realization_id: Mapped[str | None] = mapped_column(String(200))
    weather_member_id: Mapped[str | None] = mapped_column(String(100))
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(1000))
    science_envelope: Mapped[dict | None] = mapped_column(JSONB)
    input_provenance: Mapped[dict | None] = mapped_column(JSONB)


class ScientificState(Base):
    __tablename__ = "scientific_states"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    simulation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), index=True
    )
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    state_date: Mapped[date] = mapped_column(Date)
    payload: Mapped[dict] = mapped_column(JSONB)
    availability: Mapped[str] = mapped_column(String(20))


class DecisionBranch(Timestamped, Base):
    __tablename__ = "decision_branches"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), index=True)
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    parent_branch_id: Mapped[UUID | None] = mapped_column(ForeignKey("decision_branches.id"))
    base_snapshot_hash: Mapped[str] = mapped_column(String(128))
    effective_date: Mapped[date] = mapped_column(Date)
    weather_member_id: Mapped[str | None] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(100))
    input_hashes: Mapped[list] = mapped_column(JSONB, default=list)
    decision_type: Mapped[str] = mapped_column(String(100), default="baseline")
    decision_diff: Mapped[dict] = mapped_column(JSONB, default=dict)


class BranchDecision(Base):
    __tablename__ = "branch_decisions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("decision_branches.id", ondelete="CASCADE"), index=True
    )
    decision_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)


class SimulationComparison(Base):
    __tablename__ = "simulation_comparisons"
    __table_args__ = (UniqueConstraint("branch_a_id", "branch_b_id", "comparison_date"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), index=True)
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    branch_a_id: Mapped[UUID] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    branch_b_id: Mapped[UUID] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    run_a_id: Mapped[UUID] = mapped_column(ForeignKey("simulation_runs.id"), index=True)
    run_b_id: Mapped[UUID] = mapped_column(ForeignKey("simulation_runs.id"), index=True)
    comparison_date: Mapped[date] = mapped_column(Date)
    matched_inputs: Mapped[bool]
    status: Mapped[str] = mapped_column(String(30), default="completed")
    non_comparable_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    payload: Mapped[dict] = mapped_column(JSONB)


class TimelineEvent(Timestamped, Base):
    __tablename__ = "timeline_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), index=True)
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    branch_id: Mapped[UUID | None] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class ModelCapability(Base):
    __tablename__ = "model_capabilities"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    crop_id: Mapped[UUID] = mapped_column(ForeignKey("crop_identities.id"), index=True)
    engine_name: Mapped[str] = mapped_column(String(100))
    engine_version: Mapped[str] = mapped_column(String(100))
    supported_outputs: Mapped[list] = mapped_column(JSONB)
    parameters: Mapped[dict] = mapped_column(JSONB)
    limitations: Mapped[list] = mapped_column(JSONB)


class ModelParameterProvenance(Base):
    __tablename__ = "model_parameter_provenance"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    capability_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_capabilities.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(String(200))
    source_version: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class FarmResource(Timestamped, Base):
    __tablename__ = "farm_resources"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("farms.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    resource_type: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(30))
    opening_volume: Mapped[float] = mapped_column(Numeric(16, 6))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    assignments: Mapped[list[ResourcePlotAuthorization]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class ResourcePlotAuthorization(Base):
    __tablename__ = "resource_plot_authorizations"
    __table_args__ = (UniqueConstraint("resource_id", "plot_id"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("farm_resources.id"), index=True)
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resource: Mapped[FarmResource] = relationship(back_populates="assignments")
    plot: Mapped[Plot] = relationship(back_populates="resource_assignments")


class ResourceLedger(Timestamped, Base):
    __tablename__ = "resource_ledgers"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(
        ForeignKey("farm_resources.id", ondelete="CASCADE"), index=True
    )
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    closing_volume: Mapped[float] = mapped_column(Numeric(16, 3))
    version: Mapped[int] = mapped_column(default=1)
    ledger_hash: Mapped[str] = mapped_column(String(128))
    parent_ledger_id: Mapped[UUID | None] = mapped_column(ForeignKey("resource_ledgers.id"))
    validation_status: Mapped[str] = mapped_column(String(30), default="valid")


class ResourceAllocation(Base):
    __tablename__ = "resource_allocations"
    __table_args__ = (
        UniqueConstraint("resource_id", "branch_id", "allocation_id"),
        UniqueConstraint("resource_id", "branch_id", "idempotency_key"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("farm_resources.id"), index=True)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("decision_branches.id"), index=True)
    plot_id: Mapped[UUID] = mapped_column(ForeignKey("plots.id"), index=True)
    allocation_id: Mapped[str] = mapped_column(String(200))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    allocation_date: Mapped[date] = mapped_column(Date, index=True)
    requested_litres: Mapped[float] = mapped_column(Numeric(16, 6))
    withdrawn_litres: Mapped[float] = mapped_column(Numeric(16, 6))
    effective_litres: Mapped[float] = mapped_column(Numeric(16, 6))
    loss_litres: Mapped[float] = mapped_column(Numeric(16, 6))
    measurement_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)
    inherited: Mapped[bool] = mapped_column(default=False)
    source_allocation_id: Mapped[UUID | None] = mapped_column(ForeignKey("resource_allocations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_farms_location", Farm.location, postgresql_using="gist")
Index("ix_plots_geometry", Plot.geometry, postgresql_using="gist")
