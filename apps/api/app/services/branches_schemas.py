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
    branch_id: UUID = Field(
        validation_alias=AliasChoices("id", "branch_id", "branchId"),
        serialization_alias="branchId",
    )
    farm_id: UUID = Field(
        validation_alias=AliasChoices("farm_id", "farmId"),
        serialization_alias="farmId",
    )
    plot_id: UUID = Field(
        validation_alias=AliasChoices("plot_id", "plotId"),
        serialization_alias="plotId",
    )
    parent_branch_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("parent_branch_id", "parentBranchId"),
        serialization_alias="parentBranchId",
    )
    base_snapshot_hash: str = Field(
        default="",
        validation_alias=AliasChoices("base_snapshot_hash", "baseSnapshotHash"),
        serialization_alias="baseSnapshotHash",
    )
    effective_date: date = Field(
        validation_alias=AliasChoices("effective_date", "effectiveDate"),
        serialization_alias="effectiveDate",
    )
    decision_type: str = Field(
        default="baseline",
        validation_alias=AliasChoices("decision_type", "decisionType"),
        serialization_alias="decisionType",
    )
    decision_diff: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("decision_diff", "decisionDiff"),
        serialization_alias="decisionDiff",
    )
    model_version: str = Field(
        default="1.0",
        validation_alias=AliasChoices("model_version", "modelVersion"),
        serialization_alias="modelVersion",
    )
    weather_member_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("weather_member_id", "weatherMemberId"),
        serialization_alias="weatherMemberId",
    )
    input_hashes: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("input_hashes", "inputHashes"),
        serialization_alias="inputHashes",
    )
    created_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("created_at", "createdAt"),
        serialization_alias="createdAt",
    )
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimelineResponse(BaseModel):
    event_id: UUID = Field(
        validation_alias=AliasChoices("id", "event_id", "eventId"),
        serialization_alias="eventId",
    )
    event_type: str = Field(
        validation_alias=AliasChoices("event_type", "eventType"),
        serialization_alias="eventType",
    )
    event_date: date = Field(
        validation_alias=AliasChoices("event_date", "eventDate"),
        serialization_alias="eventDate",
    )
    branch_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("branch_id", "branchId"),
        serialization_alias="branchId",
    )
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("created_at", "createdAt"),
        serialization_alias="createdAt",
    )
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
