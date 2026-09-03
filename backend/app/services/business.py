from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AgentAnalysis,
    Alarm,
    Device,
    DeviceThreshold,
    FaultRecord,
    MaintenanceWorkOrder,
)
from app.schemas.common import (
    AlarmCreate,
    AnalysisBootstrapCreate,
    DeviceCreate,
    ThresholdCreate,
    WorkOrderComplete,
    WorkOrderCreate,
)


def _clamp_page(page: int, page_size: int) -> tuple[int, int]:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    return page, page_size


def create_device(db: Session, payload: DeviceCreate) -> Device:
    exists = db.scalar(select(Device).where(Device.device_code == payload.device_code))
    if exists:
        raise HTTPException(status_code=409, detail="device_code already exists")
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def list_devices(db: Session, device_type: str | None = None, status: str | None = None) -> list[Device]:
    items, _ = paginate_devices(db, device_type=device_type, status=status, page=1, page_size=1000)
    return items


def paginate_devices(
    db: Session,
    device_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Device], int]:
    page, page_size = _clamp_page(page, page_size)
    filters = []
    if device_type:
        filters.append(Device.device_type == device_type)
    if status:
        filters.append(Device.status == status)
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                Device.device_code.ilike(like),
                Device.device_name.ilike(like),
                Device.device_type.ilike(like),
                Device.location.ilike(like),
            )
        )

    count_stmt = select(func.count()).select_from(Device)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(db.scalar(count_stmt) or 0)

    stmt = select(Device).order_by(Device.id)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt).all()), total


def get_device(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return device


def create_threshold(db: Session, payload: ThresholdCreate) -> DeviceThreshold:
    if not payload.device_type and not payload.device_id:
        raise HTTPException(status_code=400, detail="device_type or device_id required")
    row = DeviceThreshold(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_thresholds(
    db: Session, device_type: str | None = None, device_id: int | None = None
) -> list[DeviceThreshold]:
    stmt = select(DeviceThreshold).order_by(DeviceThreshold.id)
    if device_type:
        stmt = stmt.where(DeviceThreshold.device_type == device_type)
    if device_id:
        stmt = stmt.where(DeviceThreshold.device_id == device_id)
    return list(db.scalars(stmt).all())


def create_alarm(db: Session, payload: AlarmCreate) -> Alarm:
    device = get_device(db, payload.device_id)
    data = payload.model_dump()
    alarm = Alarm(**data, status="PENDING")
    db.add(alarm)
    if payload.alarm_level == "CRITICAL":
        device.status = "FAULT"
        device.updated_at = datetime.now(timezone.utc)
    elif payload.alarm_level == "HIGH" and device.status == "RUNNING":
        device.status = "WARNING"
        device.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alarm)
    return alarm


def list_alarms(db: Session, status: str | None = None, device_id: int | None = None) -> list[Alarm]:
    items, _ = paginate_alarms(db, status=status, device_id=device_id, page=1, page_size=1000)
    return items


def paginate_alarms(
    db: Session,
    status: str | None = None,
    device_id: int | None = None,
    alarm_level: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Alarm, str | None]], int]:
    """Return ((alarm, device_code), ...) with total count."""
    page, page_size = _clamp_page(page, page_size)
    filters = []
    if status:
        filters.append(Alarm.status == status)
    if device_id:
        filters.append(Alarm.device_id == device_id)
    if alarm_level:
        filters.append(Alarm.alarm_level == alarm_level)
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                Alarm.alarm_type.ilike(like),
                Alarm.alarm_level.ilike(like),
                Alarm.status.ilike(like),
                Alarm.metric_name.ilike(like),
                Alarm.alarm_message.ilike(like),
                Device.device_code.ilike(like),
                Device.device_name.ilike(like),
            )
        )

    base = select(Alarm, Device.device_code).join(Device, Device.id == Alarm.device_id)
    count_stmt = select(func.count()).select_from(Alarm).join(Device, Device.id == Alarm.device_id)
    if filters:
        base = base.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.execute(
        base.order_by(Alarm.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [(row[0], row[1]) for row in rows], total


def get_alarm(db: Session, alarm_id: int) -> Alarm:
    alarm = db.get(Alarm, alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="alarm not found")
    return alarm


def bootstrap_analysis(db: Session, payload: AnalysisBootstrapCreate) -> AgentAnalysis:
    """Phase 1 helper: mock a confirmed analysis so work-order closed loop can be tested."""
    alarm = get_alarm(db, payload.alarm_id)
    if alarm.status not in {"PENDING", "FAILED"}:
        raise HTTPException(
            status_code=400,
            detail=f"alarm status {alarm.status} cannot bootstrap",
        )

    existing_confirmed = db.scalar(
        select(AgentAnalysis).where(
            AgentAnalysis.alarm_id == alarm.id,
            AgentAnalysis.status == "SUCCEEDED",
            AgentAnalysis.engineer_decision.in_(["APPROVED", "EDITED"]),
        )
    )
    if existing_confirmed:
        return existing_confirmed

    running = db.scalar(
        select(AgentAnalysis).where(
            AgentAnalysis.alarm_id == alarm.id,
            AgentAnalysis.status == "RUNNING",
        )
    )
    if running:
        raise HTTPException(status_code=409, detail="running analysis already exists")

    # Respect DOC-02 transition: PENDING/FAILED -> ANALYZING -> ANALYZED
    alarm.status = "ANALYZING"
    db.flush()

    analysis = AgentAnalysis(
        alarm_id=alarm.id,
        status="SUCCEEDED",
        analysis_result={
            "summary": f"Phase1 bootstrap for alarm {alarm.id}",
            "observations": [alarm.alarm_message or alarm.alarm_type],
            "possible_causes": [
                {
                    "cause": payload.selected_cause,
                    "likelihood": "HIGH",
                    "evidence": ["seed/bootstrap"],
                }
            ],
            "recommendations": [payload.suggestion],
            "evidence_insufficient": False,
        },
        engineer_decision=payload.engineer_decision,
        selected_cause=payload.selected_cause,
        edit_recommendations=[payload.suggestion],
    )
    alarm.status = "ANALYZED"
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _next_work_order_no(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"WO-{today}-"
    count = db.scalar(
        select(func.count()).select_from(MaintenanceWorkOrder).where(
            MaintenanceWorkOrder.work_order_no.like(f"{prefix}%")
        )
    )
    return f"{prefix}{(count or 0) + 1:04d}"


def create_work_order(db: Session, payload: WorkOrderCreate) -> MaintenanceWorkOrder:
    analysis = db.get(AgentAnalysis, payload.analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="analysis not found")
    if analysis.status != "SUCCEEDED":
        raise HTTPException(status_code=400, detail="analysis not succeeded")
    if analysis.engineer_decision not in {"APPROVED", "EDITED"}:
        raise HTTPException(status_code=400, detail="analysis not confirmed by engineer")

    existing = db.scalar(
        select(MaintenanceWorkOrder).where(
            MaintenanceWorkOrder.analysis_id == analysis.id,
            MaintenanceWorkOrder.status != "CANCELLED",
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="work order already exists for analysis")

    alarm = get_alarm(db, analysis.alarm_id)
    suggestion = payload.suggestion or analysis.selected_cause
    if analysis.edit_recommendations:
        suggestion = "; ".join(str(x) for x in analysis.edit_recommendations)

    for attempt in range(3):
        wo = MaintenanceWorkOrder(
            work_order_no=_next_work_order_no(db),
            device_id=alarm.device_id,
            alarm_id=alarm.id,
            analysis_id=analysis.id,
            fault_description=payload.fault_description or alarm.alarm_message,
            priority=payload.priority,
            status="PENDING",
            suggestion=suggestion,
        )
        db.add(wo)
        try:
            db.commit()
            db.refresh(wo)
            return wo
        except IntegrityError as exc:
            db.rollback()
            # unique analysis_id collision
            existing_after = db.scalar(
                select(MaintenanceWorkOrder).where(
                    MaintenanceWorkOrder.analysis_id == analysis.id,
                    MaintenanceWorkOrder.status != "CANCELLED",
                )
            )
            if existing_after:
                raise HTTPException(
                    status_code=409, detail="work order already exists for analysis"
                ) from exc
            if attempt == 2:
                raise HTTPException(status_code=500, detail="failed to allocate work_order_no") from exc
            analysis = db.get(AgentAnalysis, payload.analysis_id)
            alarm = get_alarm(db, analysis.alarm_id)
    raise HTTPException(status_code=500, detail="failed to create work order")


def list_work_orders(db: Session, status: str | None = None) -> list[MaintenanceWorkOrder]:
    stmt = select(MaintenanceWorkOrder).order_by(MaintenanceWorkOrder.id.desc())
    if status:
        stmt = stmt.where(MaintenanceWorkOrder.status == status)
    return list(db.scalars(stmt).all())


def start_work_order(db: Session, work_order_id: int) -> MaintenanceWorkOrder:
    wo = db.get(MaintenanceWorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail="work order not found")
    if wo.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"cannot start from status {wo.status}")
    wo.status = "PROCESSING"
    db.commit()
    db.refresh(wo)
    return wo


def complete_work_order(db: Session, work_order_id: int, payload: WorkOrderComplete) -> MaintenanceWorkOrder:
    wo = db.get(MaintenanceWorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail="work order not found")
    if wo.status != "PROCESSING":
        raise HTTPException(status_code=400, detail=f"cannot complete from status {wo.status}")

    now = datetime.now(timezone.utc)
    alarm = get_alarm(db, wo.alarm_id)
    device = get_device(db, wo.device_id)

    wo.actual_root_cause = payload.actual_root_cause
    wo.actual_solution = payload.actual_solution
    wo.status = "COMPLETED"
    wo.completed_at = now

    fault = FaultRecord(
        device_id=wo.device_id,
        alarm_id=wo.alarm_id,
        work_order_id=wo.id,
        fault_type=alarm.alarm_type,
        fault_description=wo.fault_description,
        root_cause=payload.actual_root_cause,
        solution=payload.actual_solution,
        fault_time=now,
    )
    db.add(fault)

    alarm.status = "RESOLVED"
    alarm.resolved_at = now

    open_alarms = db.scalar(
        select(func.count()).select_from(Alarm).where(
            Alarm.device_id == device.id,
            Alarm.status.in_(["PENDING", "ANALYZING", "ANALYZED", "FAILED"]),
            Alarm.id != alarm.id,
        )
    )
    open_orders = db.scalar(
        select(func.count()).select_from(MaintenanceWorkOrder).where(
            MaintenanceWorkOrder.device_id == device.id,
            MaintenanceWorkOrder.status.in_(["PENDING", "PROCESSING", "DRAFT"]),
            MaintenanceWorkOrder.id != wo.id,
        )
    )
    if not open_alarms and not open_orders:
        device.status = "RUNNING"
        device.updated_at = now

    db.commit()
    db.refresh(wo)
    return wo


def list_fault_records(db: Session, device_id: int | None = None) -> list[FaultRecord]:
    stmt = select(FaultRecord).order_by(FaultRecord.id.desc())
    if device_id:
        stmt = stmt.where(FaultRecord.device_id == device_id)
    return list(db.scalars(stmt).all())
