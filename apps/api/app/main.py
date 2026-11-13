import logging
import sys
from uuid import uuid4

if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers.analysis import router as analysis_router
from app.routers.agri_calendar import router as agri_calendar_router
from app.routers.notifications import router as notifications_router
from app.routers.branches import router as branches_router
from app.routers.comparisons import router as comparisons_router
from app.routers.crops import router as crops_router
from app.routers.environment import router as environment_router
from app.routers.farms import router as farms_router
from app.routers.advisory import router as advisory_router
from app.routers.health import router as health_router
from app.routers.observatory import router as observatory_router
from app.routers.resources import router as resources_router
from app.routers.simulations import router as simulations_router
from app.routers.telegram_integration import router as telegram_integration_router
from app.schemas import ApiError, ApiErrorDetail

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("terrapulse.api")

app = FastAPI(title="TerraPulse API", version="2.0.0")


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if origin:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    return {}


@app.middleware("http")
async def correlation_id(request: Request, call_next):
    value = request.headers.get("X-Correlation-ID", str(uuid4()))
    request.state.correlation_id = value
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = value
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    corr_id = getattr(request.state, "correlation_id", str(uuid4()))
    fields: dict[str, list[str]] = {}
    for error in exc.errors():
        location = ".".join(str(item) for item in error["loc"])
        fields.setdefault(location, []).append(error["msg"])
    body = ApiError(
        error=ApiErrorDetail(
            code="VALIDATION_ERROR", message="Request validation failed", fields=fields
        ),
        correlation_id=corr_id,
    )
    return JSONResponse(
        status_code=422,
        content=body.model_dump(by_alias=True),
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled API request failure", exc_info=exc)
    corr_id = getattr(request.state, "correlation_id", str(uuid4()))
    body = ApiError(
        error=ApiErrorDetail(
            code="API_REQUEST_FAILED",
            message=f"The API could not complete this request: {exc}",
        ),
        correlation_id=corr_id,
    )
    return JSONResponse(
        status_code=500,
        content=body.model_dump(by_alias=True),
        headers=_cors_headers(request),
    )


app.include_router(health_router)
app.include_router(crops_router)
app.include_router(farms_router)
app.include_router(advisory_router)
app.include_router(environment_router)
app.include_router(simulations_router)
app.include_router(telegram_integration_router)
app.include_router(branches_router)
app.include_router(comparisons_router)
app.include_router(observatory_router)
app.include_router(resources_router)
app.include_router(analysis_router)
app.include_router(agri_calendar_router)
app.include_router(notifications_router)
