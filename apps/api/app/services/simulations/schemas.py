from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SimulationSubmitRequest(BaseModel):
    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    environmental_snapshot_id: UUID = Field(alias="environmentalSnapshotId")
    branch_id: UUID | None = Field(default=None, alias="branchId")
    turmeric_mapping: str | None = Field(default=None, alias="turmericMapping")
    irrigation_mode: str = Field(alias="irrigationMode")
    model_config = ConfigDict(populate_by_name=True)


class SimulationRunResponse(BaseModel):
    simulation_run_id: UUID = Field(alias="simulationRunId")
    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    status: str
    engine_name: str | None = Field(default=None, alias="engine")
    engine_version: str | None = Field(default=None, alias="engineVersion")
    parameter_version: str | None = Field(default=None, alias="parameterVersion")
    environmental_snapshot_id: UUID | None = Field(default=None, alias="environmentalSnapshotId")
    weather_realization_id: str | None = Field(default=None, alias="weatherRealizationId")
    weather_member_id: str | None = Field(default=None, alias="weatherMemberId")
    requested_at: datetime | None = Field(default=None, alias="requestedAt")
    started_at: datetime | None = Field(default=None, alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    states: list[dict] = Field(default_factory=list)
    science_envelope: dict | None = Field(default=None, alias="scienceEnvelope")
    input_provenance: dict | None = Field(default=None, alias="inputProvenance")
    model_config = ConfigDict(populate_by_name=True)
