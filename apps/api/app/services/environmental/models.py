from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.contracts import (
    C1EnvironmentalInput,
    C7ModelCapability,
    Coordinates,
    DataStatus,
    SimulationPeriod,
)
from app.services.soil.models import SoilResult
from app.services.weather.models import WeatherResult
from pydantic import BaseModel, ConfigDict, Field


class EnvironmentalInputRequest(BaseModel):
    """Request parameters for preparing and validating C1 environmental inputs."""

    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID | None = Field(default=None, alias="plotId")
    location: Coordinates | None = None
    timezone: str = "Asia/Kolkata"
    simulation_period: SimulationPeriod = Field(alias="simulationPeriod")
    crop_id: UUID | None = Field(default=None, alias="cropId")
    crop_query: str | None = Field(default=None, alias="cropQuery")
    requested_outputs: list[str] = Field(default_factory=list, alias="requestedOutputs")
    weather_member_id: str | None = Field(default=None, alias="weatherMemberId")
    include_ensemble: bool | None = Field(default=None, alias="includeEnsemble")
    soil_target_depth_cm: float | None = Field(default=None, alias="soilTargetDepthCm")
    require_quantitative_simulation: bool = Field(
        default=True, alias="requireQuantitativeSimulation"
    )
    force_refresh: bool = Field(default=False, alias="forceRefresh")

    model_config = ConfigDict(populate_by_name=True)


class ValidationIssue(BaseModel):
    """Specific validation issue with severity, field, and explanatory message."""

    severity: Literal["error", "warning"]
    field: str
    message: str

    model_config = ConfigDict(populate_by_name=True)


class EnvironmentalInputResult(BaseModel):
    """Consolidated result of C1 environmental input preparation and validation."""

    is_valid: bool = Field(alias="isValid")
    status: DataStatus
    c1_input: C1EnvironmentalInput | None = Field(default=None, alias="c1Input")
    plot_id: UUID | None = Field(default=None, alias="plotId")
    capability: C7ModelCapability | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list, alias="missingFields")
    unsupported_outputs: list[str] = Field(default_factory=list, alias="unsupportedOutputs")
    freshness: str = "live"
    weather_result: WeatherResult | None = Field(default=None, alias="weatherResult")
    soil_result: SoilResult | None = Field(default=None, alias="soilResult")
    provenance: list[dict] = Field(default_factory=list)
    retrieved_at: datetime | None = Field(default=None, alias="retrievedAt")
    input_hash: str | None = Field(default=None, alias="inputHash")

    model_config = ConfigDict(populate_by_name=True)
