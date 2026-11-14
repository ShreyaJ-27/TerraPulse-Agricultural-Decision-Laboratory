from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts import C2FarmDefinition, Coordinates, Geometry, Measurement, PlotDefinition


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    fields: dict[str, list[str]] | None = None


class ApiError(BaseModel):
    error: ApiErrorDetail
    correlation_id: str = Field(alias="correlationId")
    contract_version: str = Field(default="1.0", alias="contractVersion")
    model_config = ConfigDict(populate_by_name=True)


class ApiResponse(BaseModel):
    data: object
    correlation_id: str = Field(alias="correlationId")
    contract_version: str = Field(default="1.0", alias="contractVersion")
    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    status: str
    service: str
    contract_version: str = Field(default="1.0", alias="contractVersion")
    model_config = ConfigDict(populate_by_name=True)


class FarmCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="Farm name")
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=64)
    location: Coordinates
    location_confirmed: bool = Field(alias="locationConfirmed", description="Farmer confirmation of coordinates")
    boundary: Geometry | None = None
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def require_location_confirmed(self) -> "FarmCreateRequest":
        if not self.location_confirmed:
            raise ValueError("Farm location coordinates must be explicitly confirmed by the user before onboarding.")
        return self


class PlotAreaInput(BaseModel):
    value: float = Field(gt=0, description="Plot area value, must be positive")
    unit: Literal["m2"] = Field(default="m2", description="Plot area unit must be m2")
    model_config = ConfigDict(populate_by_name=True)


class PlotCreateRequest(BaseModel):
    area_m2: PlotAreaInput = Field(alias="areaM2")
    crop_id: UUID | None = Field(default=None, alias="cropId")
    crop_query: str | None = Field(
        default=None,
        alias="cropQuery",
        description="Crop common name, alias, or scientific name to resolve",
    )
    planting_date: date | None = Field(default=None, alias="plantingDate")
    geometry: Geometry | None = None
    management: dict[str, Any] | None = None
    shared_resource_ids: list[UUID] = Field(default_factory=list, alias="sharedResourceIds")
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_crop_reference(self) -> "PlotCreateRequest":
        if self.crop_id is None and (self.crop_query is None or not self.crop_query.strip()):
            raise ValueError("A plot must reference a crop identity via cropId or cropQuery.")
        return self


class PlotPlantingDateRequest(BaseModel):
    planting_date: date = Field(alias="plantingDate")
    model_config = ConfigDict(extra="forbid")


class PlotResponse(BaseModel):
    plot_id: UUID = Field(alias="plotId")
    farm_id: UUID = Field(alias="farmId")
    area_m2: Measurement = Field(alias="areaM2")
    crop_id: UUID = Field(alias="cropId")
    crop_canonical_name: str = Field(alias="cropCanonicalName")
    crop_scientific_name: str | None = Field(default=None, alias="cropScientificName")
    planting_date: date | None = Field(default=None, alias="plantingDate")
    geometry: Geometry | None = None
    management: dict[str, Any] | None = None
    shared_resource_ids: list[UUID] = Field(default_factory=list, alias="sharedResourceIds")
    model_config = ConfigDict(populate_by_name=True)

    def to_contract_plot(self) -> PlotDefinition:
        return PlotDefinition(
            plotId=self.plot_id,
            areaM2=self.area_m2,
            geometry=self.geometry,
            cropId=self.crop_id,
            plantingDate=self.planting_date,
            management=self.management,
            sharedResourceIds=self.shared_resource_ids,
        )


class FarmResponse(BaseModel):
    farm_id: UUID = Field(alias="farmId")
    name: str
    timezone: str
    location: Coordinates
    boundary: Geometry | None = None
    plots: list[PlotResponse] = Field(default_factory=list)
    created_at: datetime | None = Field(default=None, alias="createdAt")
    model_config = ConfigDict(populate_by_name=True)

    def to_c2_definition(self) -> C2FarmDefinition:
        return C2FarmDefinition(
            contractVersion="1.0",
            farmId=self.farm_id,
            farmName=self.name,
            location=self.location,
            boundary=self.boundary,
            timezone=self.timezone,
            plots=[p.to_contract_plot() for p in self.plots],
        )
