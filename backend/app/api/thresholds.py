from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import ApiResponse, ThresholdCreate, ThresholdOut
from app.services import business

router = APIRouter(prefix="/device-thresholds", tags=["device-thresholds"])


@router.get("", response_model=ApiResponse)
def get_thresholds(
    device_type: str | None = None,
    device_id: int | None = None,
    db: Session = Depends(get_db),
):
    items = business.list_thresholds(db, device_type=device_type, device_id=device_id)
    return ApiResponse(data=[ThresholdOut.model_validate(x).model_dump() for x in items])


@router.post("", response_model=ApiResponse)
def post_threshold(payload: ThresholdCreate, db: Session = Depends(get_db)):
    row = business.create_threshold(db, payload)
    return ApiResponse(data=ThresholdOut.model_validate(row).model_dump())
