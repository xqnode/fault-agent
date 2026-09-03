from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import (
    ApiResponse,
    FaultRecordOut,
    WorkOrderComplete,
    WorkOrderCreate,
    WorkOrderOut,
)
from app.services import business

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


@router.get("", response_model=ApiResponse)
def get_work_orders(status: str | None = None, db: Session = Depends(get_db)):
    items = business.list_work_orders(db, status=status)
    return ApiResponse(data=[WorkOrderOut.model_validate(x).model_dump() for x in items])


@router.post("", response_model=ApiResponse)
def post_work_order(payload: WorkOrderCreate, db: Session = Depends(get_db)):
    wo = business.create_work_order(db, payload)
    return ApiResponse(data=WorkOrderOut.model_validate(wo).model_dump())


@router.post("/{work_order_id}/start", response_model=ApiResponse)
def post_start(work_order_id: int, db: Session = Depends(get_db)):
    wo = business.start_work_order(db, work_order_id)
    return ApiResponse(data=WorkOrderOut.model_validate(wo).model_dump())


@router.post("/{work_order_id}/complete", response_model=ApiResponse)
def post_complete(
    work_order_id: int,
    payload: WorkOrderComplete,
    db: Session = Depends(get_db),
):
    wo = business.complete_work_order(db, work_order_id, payload)
    return ApiResponse(data=WorkOrderOut.model_validate(wo).model_dump())


fault_router = APIRouter(prefix="/fault-records", tags=["fault-records"])


@fault_router.get("", response_model=ApiResponse)
def get_fault_records(device_id: int | None = None, db: Session = Depends(get_db)):
    items = business.list_fault_records(db, device_id=device_id)
    return ApiResponse(data=[FaultRecordOut.model_validate(x).model_dump() for x in items])
