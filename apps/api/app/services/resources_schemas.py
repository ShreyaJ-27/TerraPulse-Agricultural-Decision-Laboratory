from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    resource_type: str = Field(alias="resourceType", min_length=1, max_length=100)
    opening_volume: Decimal = Field(alias="openingVolume", ge=0)
    unit: Literal["litre"] = "litre"
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(populate_by_name=True)


class ResourceResponse(BaseModel):
    resource_id: UUID = Field(alias="resourceId")
    farm_id: UUID = Field(alias="farmId")
    name: str
    resource_type: str = Field(alias="resourceType")
    unit: str
    opening_volume: Decimal = Field(alias="openingVolume")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = Field(default=None, alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResourceAllocationRequest(BaseModel):
    plot_id: UUID = Field(alias="plotId")
    allocation_id: str = Field(alias="allocationId", min_length=1, max_length=200)
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=200)
    allocation_date: date = Field(alias="allocationDate")
    requested_amount: Decimal = Field(alias="requestedAmount", ge=0)
    withdrawn_amount: Decimal = Field(alias="withdrawnAmount", ge=0)
    effective_amount: Decimal = Field(alias="effectiveAmount", ge=0)
    unit: Literal["litre"] = "litre"
    measurement_provenance: dict[str, Any] = Field(
        default_factory=dict, alias="measurementProvenance"
    )
    model_config = ConfigDict(populate_by_name=True)


def resource_data(resource) -> dict[str, Any]:
    return ResourceResponse(
        resourceId=resource.id,
        farmId=resource.farm_id,
        name=resource.name,
        resourceType=resource.resource_type,
        unit=resource.unit,
        openingVolume=resource.opening_volume,
        metadata=resource.metadata_json or {},
        createdAt=resource.created_at,
    ).model_dump(by_alias=True, mode="json")
