from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.core.database import get_db
from app.models import Device, DeviceThreshold
from app.schemas.common import (
    ApiResponse,
    DeviceCreate,
    DeviceDetailOut,
    DeviceOut,
    PageResult,
    ThresholdCreate,
    ThresholdOut,
)
from app.services import business

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=ApiResponse)
def get_devices(
    device_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = business.paginate_devices(
        db,
        device_type=device_type,
        status=status,
        q=q,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResult(
            items=[DeviceOut.model_validate(x).model_dump() for x in items],
            total=total,
            page=page,
            page_size=page_size,
        ).model_dump()
    )


@router.post("", response_model=ApiResponse)
def post_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    device = business.create_device(db, payload)
    return ApiResponse(data=DeviceOut.model_validate(device).model_dump())


@router.get("/{device_id}", response_model=ApiResponse)
def get_device_detail(device_id: int, db: Session = Depends(get_db)):
    device = db.scalar(
        select(Device)
        .options(selectinload(Device.thresholds))
        .where(Device.id == device_id)
    )
    if not device:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="device not found")

    type_thresholds = list(
        db.scalars(
            select(DeviceThreshold).where(
                DeviceThreshold.device_type == device.device_type,
                DeviceThreshold.device_id.is_(None),
            )
        ).all()
    )
    merged = {t.metric_name: t for t in type_thresholds}
    for t in device.thresholds:
        merged[t.metric_name] = t

    data = DeviceDetailOut(
        **DeviceOut.model_validate(device).model_dump(),
        thresholds=[ThresholdOut.model_validate(t) for t in merged.values()],
    )
    return ApiResponse(data=data.model_dump())


@router.get("/{device_id}/sensor-data", response_model=ApiResponse)
def get_sensor_data(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from app.models import DeviceSensorData

    business.get_device(db, device_id)
    rows = list(
        db.scalars(
            select(DeviceSensorData)
            .where(DeviceSensorData.device_id == device_id)
            .order_by(DeviceSensorData.record_time.desc())
            .limit(limit)
        ).all()
    )
    points = [
        {
            "record_time": r.record_time,
            "temperature": r.temperature,
            "pressure": r.pressure,
            "vibration": r.vibration,
            "power": r.power,
        }
        for r in reversed(rows)
    ]
    return ApiResponse(data={"device_id": device_id, "points": points})
