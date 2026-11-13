from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ComparisonCreateRequest(BaseModel):
    baseline_branch_id: UUID = Field(alias="baselineBranchId")
    alternative_branch_id: UUID = Field(alias="alternativeBranchId")
    baseline_run_id: UUID = Field(alias="baselineRunId")
    alternative_run_id: UUID = Field(alias="alternativeRunId")
    fork_date: date | None = Field(default=None, alias="forkDate")
    model_config = ConfigDict(populate_by_name=True)


class ComparisonResponse(BaseModel):
    comparison_id: UUID = Field(alias="comparisonId")
    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    branch_a_id: UUID = Field(alias="baselineBranchId")
    branch_b_id: UUID = Field(alias="alternativeBranchId")
    run_a_id: UUID = Field(alias="baselineRunId")
    run_b_id: UUID = Field(alias="alternativeRunId")
    comparison_date: date = Field(alias="comparisonDate")
    status: str
    matched_inputs: bool = Field(alias="matchedInputs")
    non_comparable_reasons: list[str] = Field(alias="reasons")
    payload: dict[str, Any]
    created_at: datetime | None = Field(alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
