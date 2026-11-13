from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DataStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"


class Availability(BaseModel):
    status: DataStatus
    reason: str | None = None


class Measurement(BaseModel):
    value: float | None = None
    unit: str = Field(min_length=1)
    availability: Availability

    @model_validator(mode="after")
    def value_matches_status(self) -> "Measurement":
        if self.availability.status == DataStatus.AVAILABLE and self.value is None:
            raise ValueError("available measurements must contain a value")
        if self.availability.status != DataStatus.AVAILABLE and self.value is not None:
            raise ValueError("unavailable measurements must not contain a value")
        return self


class Provenance(BaseModel):
    source_id: str = Field(alias="sourceId", min_length=1)
    source_version: str | None = Field(default=None, alias="sourceVersion")
    retrieved_at: datetime = Field(alias="retrievedAt")
    reference: str | None = None
    model_config = ConfigDict(populate_by_name=True)


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    crs: Literal["EPSG:4326"]


class Geometry(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[Any]


class SimulationPeriod(BaseModel):
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    model_config = ConfigDict(populate_by_name=True)


class SoilProperties(BaseModel):
    depth_cm: Measurement = Field(alias="depthCm")
    texture: str | None = None
    field_capacity: Measurement = Field(alias="fieldCapacity")
    wilting_point: Measurement = Field(alias="wiltingPoint")
    bulk_density: Measurement | None = Field(default=None, alias="bulkDensity")
    model_config = ConfigDict(populate_by_name=True)


class DailyWeather(BaseModel):
    date: date
    temperature_min_c: Measurement = Field(alias="temperatureMinC")
    temperature_max_c: Measurement = Field(alias="temperatureMaxC")
    rainfall_mm: Measurement = Field(alias="rainfallMm")
    reference_evapotranspiration_mm: Measurement | None = Field(default=None, alias="referenceEvapotranspirationMm")
    ensemble_member_id: str | None = Field(default=None, alias="ensembleMemberId")
    model_config = ConfigDict(populate_by_name=True)


class C1EnvironmentalInput(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    farm_id: UUID = Field(alias="farmId")
    location: Coordinates
    timezone: str
    simulation_period: SimulationPeriod = Field(alias="simulationPeriod")
    daily_weather: list[DailyWeather] = Field(alias="dailyWeather")
    soil: SoilProperties
    data_source_ids: list[str] = Field(alias="dataSourceIds")
    retrieved_at: datetime = Field(alias="retrievedAt")
    availability: Availability
    provenance: list[Provenance]
    model_config = ConfigDict(populate_by_name=True)


class C2FarmDefinition(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    farm_id: UUID = Field(alias="farmId")
    farm_name: str = Field(alias="farmName", min_length=1)
    location: Coordinates
    boundary: Geometry | None = None
    timezone: str
    plots: list["PlotDefinition"]
    model_config = ConfigDict(populate_by_name=True)


class PlotDefinition(BaseModel):
    plot_id: UUID = Field(alias="plotId")
    area_m2: Measurement = Field(alias="areaM2")
    geometry: Geometry | None = None
    crop_id: UUID | None = Field(default=None, alias="cropId")
    planting_date: date | None = Field(default=None, alias="plantingDate")
    management: dict[str, Any] | None = None
    shared_resource_ids: list[UUID] = Field(alias="sharedResourceIds")
    model_config = ConfigDict(populate_by_name=True)


class C3ScientificState(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    farm_id: UUID = Field(alias="farmId")
    plot_id: UUID = Field(alias="plotId")
    branch_id: UUID = Field(alias="branchId")
    simulation_run_id: UUID = Field(alias="simulationRunId")
    date: date
    engine: "EngineReference"
    soil_water: Measurement = Field(alias="soilWater")
    root_zone: Measurement = Field(alias="rootZone")
    crop_water_demand: Measurement = Field(alias="cropWaterDemand")
    actual_evapotranspiration: Measurement = Field(alias="actualEvapotranspiration")
    water_stress: Measurement = Field(alias="waterStress")
    irrigation: Measurement
    rainfall: Measurement
    drainage: Measurement
    runoff: Measurement
    biomass: Measurement | None = None
    yield_: Measurement | None = Field(default=None, alias="yield")
    availability: Availability
    provenance: list[Provenance]
    model_config = ConfigDict(populate_by_name=True)


class C4BranchDecision(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    branch_id: UUID = Field(alias="branchId")
    parent_branch_id: UUID | None = Field(default=None, alias="parentBranchId")
    base_snapshot_hash: str = Field(alias="baseSnapshotHash", min_length=1)
    effective_date: date = Field(alias="effectiveDate")
    weather_member_id: str | None = Field(default=None, alias="weatherMemberId")
    management_decisions: dict[str, Any] = Field(alias="managementDecisions")
    changed_planting_date: date | None = Field(default=None, alias="changedPlantingDate")
    changed_irrigation: Measurement | None = Field(default=None, alias="changedIrrigation")
    changed_crop_id: UUID | None = Field(default=None, alias="changedCropId")
    model_version: str = Field(alias="modelVersion")
    input_hashes: list[str] = Field(alias="inputHashes")
    created_at: datetime = Field(alias="createdAt")
    model_config = ConfigDict(populate_by_name=True)


class C5Comparison(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    branch_a: UUID = Field(alias="branchA")
    branch_b: UUID = Field(alias="branchB")
    comparison_date: date = Field(alias="comparisonDate")
    matched_inputs: bool = Field(alias="matchedInputs")
    metrics: list["ComparisonMetric"]
    availability: Availability
    assumptions: list[str]
    provenance: list[Provenance]
    model_config = ConfigDict(populate_by_name=True)


class C6VisualState(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    plot_id: UUID = Field(alias="plotId")
    branch_id: UUID = Field(alias="branchId")
    date: date
    crop_visual_identity: str = Field(alias="cropVisualIdentity")
    growth_presentation: dict[str, Any] = Field(alias="growthPresentation")
    soil_layer_presentation: dict[str, Any] = Field(alias="soilLayerPresentation")
    scientific_state_reference: UUID = Field(alias="scientificStateReference")
    interpolation: "InterpolationMetadata"
    model_config = ConfigDict(populate_by_name=True)


class C7ModelCapability(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    crop_id: UUID = Field(alias="cropId")
    accepted_crop_names: list[str] = Field(alias="acceptedCropNames")
    scientific_name: str | None = Field(default=None, alias="scientificName")
    selected_engine: Literal["AquaCrop", "FAO-56", "identity/ecology-only"] = Field(alias="selectedEngine")
    engine_version: str = Field(alias="engineVersion")
    supported_outputs: list[str] = Field(alias="supportedOutputs")
    model_parameters: dict[str, float | str] = Field(alias="modelParameters")
    parameter_sources: list[Provenance] = Field(alias="parameterSources")
    parameter_versions: list[str] = Field(alias="parameterVersions")
    known_limitations: list[str] = Field(alias="knownLimitations")
    provenance_references: list[Provenance] = Field(alias="provenanceReferences")
    model_config = ConfigDict(populate_by_name=True)


class C8ResourceLedger(BaseModel):
    contract_version: Literal["1.0"] = Field(alias="contractVersion")
    farm_id: UUID = Field(alias="farmId")
    branch_id: UUID = Field(alias="branchId")
    resource_id: UUID = Field(alias="resourceId")
    unit: str
    opening_volume: Measurement = Field(alias="openingVolume")
    plot_allocations: list["PlotAllocation"] = Field(alias="plotAllocations")
    losses: Measurement
    closing_volume: Measurement = Field(alias="closingVolume")
    accounting_validation: "AccountingValidation" = Field(alias="accountingValidation")
    errors: list[str]
    model_config = ConfigDict(populate_by_name=True)


class EngineReference(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


class ComparisonMetric(BaseModel):
    metric: str = Field(min_length=1)
    value_a: Measurement = Field(alias="valueA")
    value_b: Measurement = Field(alias="valueB")
    difference: Measurement
    model_config = ConfigDict(populate_by_name=True)


class InterpolationMetadata(BaseModel):
    enabled: bool
    method: str | None = None
    source_dates: list[date] = Field(alias="sourceDates")
    model_config = ConfigDict(populate_by_name=True)


class PlotAllocation(BaseModel):
    plot_id: UUID = Field(alias="plotId")
    requested_amount: Measurement = Field(alias="requestedAmount")
    withdrawn_amount: Measurement = Field(alias="withdrawnAmount")
    effective_amount: Measurement = Field(alias="effectiveAmount")
    model_config = ConfigDict(populate_by_name=True)


class AccountingValidation(BaseModel):
    is_valid: bool = Field(alias="isValid")
    difference: Measurement
    model_config = ConfigDict(populate_by_name=True)

