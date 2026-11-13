from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Request

from app.schemas import ApiResponse
from app.services.advisory import AdvisoryProfile, get_advisory_profile

router = APIRouter(prefix="/api/v1/advisory", tags=["farmer-advisory"])


class AdvisoryResponse(ApiResponse):
    data: AdvisoryProfile


@router.get("/regions/{region_id}/crops/{crop_id}", response_model=AdvisoryResponse)
def crop_advisory(
    request: Request,
    crop_id: UUID,
    region_id: str = Path(pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$"),
) -> AdvisoryResponse:
    profile = get_advisory_profile(crop_id, region_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Crop not found in the crop catalogue.")
    return AdvisoryResponse(data=profile, correlationId=request.state.correlation_id)
