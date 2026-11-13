from __future__ import annotations

from datetime import datetime
from typing import Any

from app.contracts import Availability, Coordinates, Provenance, SoilProperties
from pydantic import BaseModel, ConfigDict, Field


class SoilDepthObservation(BaseModel):
    """Observation of a soil property at a specific depth interval."""

    depth_label: str = Field(alias="depthLabel")
    top_depth_cm: float = Field(alias="topDepthCm")
    bottom_depth_cm: float = Field(alias="bottomDepthCm")
    raw_mean: float | None = Field(default=None, alias="rawMean")
    converted_value: float | None = Field(default=None, alias="convertedValue")
    target_unit: str = Field(alias="targetUnit")
    uncertainty: float | None = None
    quantiles: dict[str, float | None] | None = None
    availability: Availability
    model_config = ConfigDict(populate_by_name=True)


class SoilLayerProperty(BaseModel):
    """Detailed multi-depth observations for a single SoilGrids property."""

    property_name: str = Field(alias="propertyName")
    mapped_units: str | None = Field(default=None, alias="mappedUnits")
    target_units: str | None = Field(default=None, alias="targetUnits")
    conversion_factor: float = Field(default=1.0, alias="conversionFactor")
    depths: list[SoilDepthObservation] = Field(default_factory=list)
    model_config = ConfigDict(populate_by_name=True)


class SoilResult(BaseModel):
    """Consolidated normalized soil data adapter output compatible with C1EnvironmentalInput."""

    location: Coordinates
    profile_depth_cm: float = Field(alias="profileDepthCm")
    soil_properties: SoilProperties = Field(alias="soilProperties")
    layers: dict[str, SoilLayerProperty] = Field(default_factory=dict)
    data_source_ids: list[str] = Field(default_factory=list, alias="dataSourceIds")
    provenance: list[Provenance] = Field(default_factory=list)
    retrieved_at: datetime = Field(alias="retrievedAt")
    availability: Availability
    raw_metadata: dict[str, Any] = Field(default_factory=dict, alias="rawMetadata")
    model_config = ConfigDict(populate_by_name=True)
