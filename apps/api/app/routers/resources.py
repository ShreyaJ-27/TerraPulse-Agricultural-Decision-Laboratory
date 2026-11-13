from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas import ApiError, ApiErrorDetail, ApiResponse
from app.services.resources import ResourceService
from app.services.resources_schemas import (
    ResourceAllocationRequest,
    ResourceCreateRequest,
    resource_data,
)

router = APIRouter(prefix="/api/v1/farms", tags=["shared-water-resources"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ERROR_STATUS = {
    "RESOURCE_NOT_FOUND": 404,
    "RESOURCE_FARM_MISMATCH": 422,
    "PLOT_FARM_MISMATCH": 422,
    "PLOT_RESOURCE_NOT_ASSIGNED": 422,
    "BRANCH_SCOPE_MISMATCH": 422,
    "INSUFFICIENT_WATER": 409,
    "IDEMPOTENCY_CONFLICT": 409,
    "DUPLICATE_ALLOCATION": 409,
}


def _error(request: Request, code: str) -> JSONResponse:
    body = ApiError(
        error=ApiErrorDetail(code=code, message=code.replace("_", " ").title()),
        correlationId=request.state.correlation_id,
    )
    return JSONResponse(status_code=_ERROR_STATUS.get(code, 422), content=body.model_dump(by_alias=True))


@router.post("/{farm_id}/resources", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    farm_id: UUID, payload: ResourceCreateRequest, request: Request, session: SessionDep
) -> ApiResponse:
    try:
        resource = await ResourceService(session).create_resource(
            farm_id,
            name=payload.name,
            resource_type=payload.resource_type,
            opening_volume=payload.opening_volume,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(data=resource_data(resource), correlationId=request.state.correlation_id)


@router.get("/{farm_id}/resources", response_model=ApiResponse)
async def list_resources(farm_id: UUID, request: Request, session: SessionDep) -> ApiResponse:
    resources = await ResourceService(session).list_resources(farm_id)
    return ApiResponse(
        data={"resources": [resource_data(item) for item in resources]},
        correlationId=request.state.correlation_id,
    )


@router.get("/{farm_id}/resources/{resource_id}", response_model=ApiResponse)
async def get_resource(
    farm_id: UUID, resource_id: UUID, request: Request, session: SessionDep
) -> ApiResponse | JSONResponse:
    try:
        resource = await ResourceService(session).get_resource(farm_id, resource_id)
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(data=resource_data(resource), correlationId=request.state.correlation_id)


@router.post(
    "/{farm_id}/resources/{resource_id}/plots/{plot_id}",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_plot(
    farm_id: UUID, resource_id: UUID, plot_id: UUID, request: Request, session: SessionDep
) -> ApiResponse | JSONResponse:
    try:
        assignment = await ResourceService(session).assign_plot(farm_id, resource_id, plot_id)
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(
        data={
            "resourceId": str(assignment.resource_id),
            "plotId": str(assignment.plot_id),
            "createdAt": assignment.created_at,
        },
        correlationId=request.state.correlation_id,
    )


@router.get(
    "/{farm_id}/resources/{resource_id}/branches/{branch_id}/ledger",
    response_model=ApiResponse,
)
async def get_ledger(
    farm_id: UUID, resource_id: UUID, branch_id: UUID, request: Request, session: SessionDep
) -> ApiResponse | JSONResponse:
    try:
        ledger = await ResourceService(session).get_ledger(farm_id, resource_id, branch_id)
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(
        data={
            "ledgerId": str(ledger.id),
            "version": ledger.version,
            "ledgerHash": ledger.ledger_hash,
            "validationStatus": ledger.validation_status,
            "payload": ledger.payload,
        },
        correlationId=request.state.correlation_id,
    )


@router.get(
    "/{farm_id}/resources/{resource_id}/branches/{branch_id}/allocations",
    response_model=ApiResponse,
)
async def list_allocations(
    farm_id: UUID, resource_id: UUID, branch_id: UUID, request: Request, session: SessionDep
) -> ApiResponse | JSONResponse:
    try:
        allocations = await ResourceService(session).list_allocations(farm_id, resource_id, branch_id)
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(
        data={"allocations": [
            {
                "id": str(item.id),
                "allocationId": item.allocation_id,
                "plotId": str(item.plot_id),
                "allocationDate": item.allocation_date,
                "requestedAmount": item.requested_litres,
                "withdrawnAmount": item.withdrawn_litres,
                "effectiveAmount": item.effective_litres,
                "lossAmount": item.loss_litres,
                "unit": "litre",
            }
            for item in allocations
        ]},
        correlationId=request.state.correlation_id,
    )


@router.get(
    "/{farm_id}/resources/{resource_id}/branches/{branch_id}/ledger/versions",
    response_model=ApiResponse,
)
async def list_ledger_versions(
    farm_id: UUID, resource_id: UUID, branch_id: UUID, request: Request, session: SessionDep
) -> ApiResponse | JSONResponse:
    try:
        ledgers = await ResourceService(session).list_ledger_versions(
            farm_id, resource_id, branch_id
        )
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(
        data={
            "versions": [
                {
                    "ledgerId": str(item.id),
                    "version": item.version,
                    "ledgerHash": item.ledger_hash,
                    "parentLedgerId": str(item.parent_ledger_id) if item.parent_ledger_id else None,
                    "createdAt": item.created_at,
                    "payload": item.payload,
                }
                for item in ledgers
            ]
        },
        correlationId=request.state.correlation_id,
    )


@router.post(
    "/{farm_id}/resources/{resource_id}/branches/{branch_id}/allocations",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_allocation(
    farm_id: UUID,
    resource_id: UUID,
    branch_id: UUID,
    payload: ResourceAllocationRequest,
    request: Request,
    session: SessionDep,
) -> ApiResponse | JSONResponse:
    try:
        allocation, ledger = await ResourceService(session).allocate(
            farm_id,
            resource_id,
            branch_id,
            plot_id=payload.plot_id,
            allocation_id=payload.allocation_id,
            idempotency_key=payload.idempotency_key,
            allocation_date=payload.allocation_date,
            requested=payload.requested_amount,
            withdrawn=payload.withdrawn_amount,
            effective=payload.effective_amount,
            provenance=payload.measurement_provenance,
        )
    except ValueError as exc:
        return _error(request, str(exc))
    return ApiResponse(
        data={
            "allocationId": allocation.allocation_id,
            "ledgerId": str(ledger.id),
            "ledgerVersion": ledger.version,
            "ledgerHash": ledger.ledger_hash,
            "closingVolume": ledger.closing_volume,
        },
        correlationId=request.state.correlation_id,
    )
