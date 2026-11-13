from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class BranchCreateRequest(BaseModel):
    plot_id: UUID = Field(alias="plotId")
    environmental_snapshot_id: UUID = Field(alias="environmentalSnapshotId")
    effective_date: date = Field(alias="effectiveDate")
    decision_type: str = Field(default="baseline", alias="decisionType")
    decision_diff: dict[str, Any] = Field(default_factory=dict, alias="decisionDiff")
    parent_branch_id: UUID | None = Field(default=None, alias="parentBranchId")
    model_config = ConfigDict(populate_by_name=True)


class BranchResponse(BaseModel):
    branch_id: UUID = Field(alias="branchId", validation_alias=AliasChoices("branchId", "branch_id", "id"))
    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    parent_branch_id: UUID | None = Field(alias="parentBranchId")
    base_snapshot_hash: str = Field(alias="baseSnapshotHash")
    effective_date: date = Field(alias="effectiveDate")
    decision_type: str = Field(alias="decisionType")
    decision_diff: dict[str, Any] = Field(alias="decisionDiff")
    model_version: str = Field(alias="modelVersion")
    weather_member_id: str | None = Field(alias="weatherMemberId")
    input_hashes: list[str] = Field(alias="inputHashes")
    created_at: datetime | None = Field(alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimelineResponse(BaseModel):
    event_id: UUID = Field(alias="eventId", validation_alias=AliasChoices("eventId", "event_id", "id"))
    event_type: str = Field(alias="eventType")
    event_date: date = Field(alias="eventDate")
    branch_id: UUID | None = Field(alias="branchId")
    description: str
    payload: dict[str, Any]
    created_at: datetime | None = Field(alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
