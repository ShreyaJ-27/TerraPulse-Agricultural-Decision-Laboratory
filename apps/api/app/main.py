import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers.branches import router as branches_router
from app.routers.comparisons import router as comparisons_router
from app.routers.crops import router as crops_router
from app.routers.environment import router as environment_router
from app.routers.farms import router as farms_router
from app.routers.health import router as health_router
from app.routers.observatory import router as observatory_router
from app.routers.resources import router as resources_router
from app.routers.simulations import router as simulations_router
from app.schemas import ApiError, ApiErrorDetail

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("terrapulse.api")

app = FastAPI(title="TerraPulse API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id(request: Request, call_next):
    value = request.headers.get("X-Correlation-ID", str(uuid4()))
    request.state.correlation_id = value
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = value
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    correlation_id = request.state.correlation_id
    fields: dict[str, list[str]] = {}
    for error in exc.errors():
        location = ".".join(str(item) for item in error["loc"])
        fields.setdefault(location, []).append(error["msg"])
    body = ApiError(
        error=ApiErrorDetail(
            code="VALIDATION_ERROR", message="Request validation failed", fields=fields
        ),
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=422, content=body.model_dump(by_alias=True))


app.include_router(health_router)
app.include_router(crops_router)
app.include_router(farms_router)
app.include_router(environment_router)
app.include_router(simulations_router)
app.include_router(branches_router)
app.include_router(comparisons_router)
app.include_router(observatory_router)
app.include_router(resources_router)
