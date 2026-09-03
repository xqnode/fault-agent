from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import AlarmCreate, AlarmOut, ApiResponse, PageResult
from app.services import business

router = APIRouter(prefix="/alarms", tags=["alarms"])


@router.get("", response_model=ApiResponse)
def get_alarms(
    status: str | None = None,
    device_id: int | None = None,
    alarm_level: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows, total = business.paginate_alarms(
        db,
        status=status,
        device_id=device_id,
        alarm_level=alarm_level,
        q=q,
        page=page,
        page_size=page_size,
    )
    items = []
    for alarm, device_code in rows:
        data = AlarmOut.model_validate(alarm).model_dump()
        data["device_code"] = device_code
        items.append(data)
    return ApiResponse(
        data=PageResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ).model_dump()
    )


@router.post("", response_model=ApiResponse)
def post_alarm(payload: AlarmCreate, db: Session = Depends(get_db)):
    alarm = business.create_alarm(db, payload)
    return ApiResponse(data=AlarmOut.model_validate(alarm).model_dump())


@router.get("/{alarm_id}", response_model=ApiResponse)
def get_alarm(alarm_id: int, db: Session = Depends(get_db)):
    alarm = business.get_alarm(db, alarm_id)
    data = AlarmOut.model_validate(alarm).model_dump()
    device = business.get_device(db, alarm.device_id)
    data["device_code"] = device.device_code
    return ApiResponse(data=data)
