from fastapi import APIRouter

from app.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="terrapulse-api")


@router.get("/api/v1/health", response_model=HealthResponse)
async def versioned_health() -> HealthResponse:
    return HealthResponse(status="ok", service="terrapulse-api")
