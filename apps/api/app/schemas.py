from pydantic import BaseModel, ConfigDict, Field


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
