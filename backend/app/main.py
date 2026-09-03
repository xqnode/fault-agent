from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.alarms import router as alarms_router
from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.simulator import router as simulator_router
from app.api.thresholds import router as thresholds_router
from app.api.work_orders import fault_router, router as work_orders_router
from app.core.config import get_settings
from app.schemas.common import ApiResponse

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.3.1")
prefix = settings.api_prefix

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_API_PATHS = {
    f"{prefix}/auth/login",
}


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS":
        return await call_next(request)
    if path == "/health" or path in PUBLIC_API_PATHS:
        return await call_next(request)
    if path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
        return await call_next(request)
    if path.startswith(prefix):
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "未登录或缺少 Authorization Bearer"},
            )
        token = auth.split(" ", 1)[1].strip()
        try:
            from app.core.security import (
                decode_token,
                resolve_required_permissions,
                role_has_permission,
            )

            payload = decode_token(token)
            role = payload.get("role")
            if role not in {"ADMIN", "ENGINEER"}:
                return JSONResponse(status_code=403, content={"detail": "无访问权限"})

            required = resolve_required_permissions(request.method, path)
            if required is not None and not role_has_permission(role, required):
                return JSONResponse(status_code=403, content={"detail": "权限不足"})

            request.state.user = {
                "id": payload.get("uid"),
                "username": payload.get("sub"),
                "role": role,
                "nickname": payload.get("nickname"),
            }
        except Exception as exc:
            detail = getattr(exc, "detail", None) or "无效或过期的登录凭证"
            return JSONResponse(status_code=401, content={"detail": detail})
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


@app.get(f"{prefix}/dashboard/overview", response_model=ApiResponse)
def dashboard_overview():
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import Date, cast, func, select

    from app.core.database import SessionLocal
    from app.models import Alarm, Device

    with SessionLocal() as db:
        device_total = db.scalar(select(func.count()).select_from(Device)) or 0
        device_running = (
            db.scalar(select(func.count()).select_from(Device).where(Device.status == "RUNNING"))
            or 0
        )
        device_warning = (
            db.scalar(select(func.count()).select_from(Device).where(Device.status == "WARNING"))
            or 0
        )
        device_fault = (
            db.scalar(select(func.count()).select_from(Device).where(Device.status == "FAULT"))
            or 0
        )
        alarm_pending = (
            db.scalar(select(func.count()).select_from(Alarm).where(Alarm.status == "PENDING"))
            or 0
        )
        alarm_analyzing = (
            db.scalar(select(func.count()).select_from(Alarm).where(Alarm.status == "ANALYZING"))
            or 0
        )

        recent = list(db.scalars(select(Alarm).order_by(Alarm.id.desc()).limit(8)).all())
        recent_ids = [a.device_id for a in recent] or [-1]
        device_map = {
            d.id: d.device_code
            for d in db.scalars(select(Device).where(Device.id.in_(recent_ids))).all()
        }
        recent_alarms = [
            {
                "id": a.id,
                "device_id": a.device_id,
                "device_code": device_map.get(a.device_id),
                "alarm_type": a.alarm_type,
                "alarm_level": a.alarm_level,
                "status": a.status,
                "measured_value": float(a.measured_value) if a.measured_value is not None else None,
                "threshold_value": float(a.threshold_value) if a.threshold_value is not None else None,
                "created_at": a.created_at,
            }
            for a in recent
        ]

        start = datetime.now(timezone.utc).date() - timedelta(days=6)
        rows = db.execute(
            select(cast(Alarm.created_at, Date).label("day"), func.count().label("count"))
            .where(cast(Alarm.created_at, Date) >= start)
            .group_by("day")
            .order_by("day")
        ).all()
        count_by_day = {str(r.day): int(r.count) for r in rows}
        alarm_trend = []
        for i in range(7):
            day = start + timedelta(days=i)
            key = str(day)
            alarm_trend.append({"date": key, "count": count_by_day.get(key, 0)})

        status_distribution = [
            {"name": "RUNNING", "value": device_running},
            {"name": "WARNING", "value": device_warning},
            {"name": "FAULT", "value": device_fault},
            {
                "name": "STOPPED",
                "value": max(device_total - device_running - device_warning - device_fault, 0),
            },
        ]

    return ApiResponse(
        data={
            "device_total": device_total,
            "device_running": device_running,
            "device_warning": device_warning,
            "device_fault": device_fault,
            "alarm_pending": alarm_pending,
            "alarm_analyzing": alarm_analyzing,
            "recent_alarms": recent_alarms,
            "alarm_trend": alarm_trend,
            "status_distribution": status_distribution,
        }
    )


app.include_router(auth_router, prefix=prefix)
app.include_router(devices_router, prefix=prefix)
app.include_router(thresholds_router, prefix=prefix)
app.include_router(alarms_router, prefix=prefix)
app.include_router(analysis_router, prefix=prefix)
app.include_router(work_orders_router, prefix=prefix)
app.include_router(fault_router, prefix=prefix)
app.include_router(simulator_router, prefix=prefix)
