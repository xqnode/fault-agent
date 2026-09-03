from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int | None = None
    username: str
    nickname: str
    role: str = "ADMIN"
    permissions: list[str] = Field(default_factory=list)


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DeviceCreate(BaseModel):
    device_code: str
    device_name: str
    device_type: str
    location: str | None = None
    status: str = "RUNNING"


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_code: str
    device_name: str
    device_type: str
    location: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ThresholdCreate(BaseModel):
    device_type: str | None = None
    device_id: int | None = None
    metric_name: str
    warning_max: Decimal | None = None
    alarm_max: Decimal
    unit: str | None = None


class ThresholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_type: str | None
    device_id: int | None
    metric_name: str
    warning_max: Decimal | None
    alarm_max: Decimal
    unit: str | None
    created_at: datetime


class DeviceDetailOut(DeviceOut):
    thresholds: list[ThresholdOut] = Field(default_factory=list)


class AlarmCreate(BaseModel):
    device_id: int
    alarm_type: str
    alarm_level: str
    alarm_message: str | None = None
    metric_name: str
    measured_value: Decimal
    threshold_value: Decimal
    snapshot_json: dict[str, Any]


class AlarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    device_code: str | None = None
    alarm_type: str
    alarm_level: str
    alarm_message: str | None
    metric_name: str
    measured_value: Decimal
    threshold_value: Decimal
    snapshot_json: dict[str, Any]
    status: str
    created_at: datetime
    resolved_at: datetime | None


class PageResult(BaseModel):
    items: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class AnalysisBootstrapCreate(BaseModel):
    """Phase 1 helper: create a SUCCEEDED+APPROVED analysis so work orders can be tested."""

    alarm_id: int
    selected_cause: str = "冷却系统异常"
    suggestion: str = "检查冷却液循环；检查散热风扇"
    engineer_decision: str = "APPROVED"


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alarm_id: int
    status: str
    analysis_result: dict[str, Any] | None
    engineer_decision: str | None
    selected_cause: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class WorkOrderCreate(BaseModel):
    analysis_id: int
    priority: str = "HIGH"
    fault_description: str | None = None
    suggestion: str | None = None


class WorkOrderComplete(BaseModel):
    actual_root_cause: str
    actual_solution: str


class WorkOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_no: str
    device_id: int
    alarm_id: int
    analysis_id: int
    fault_description: str | None
    priority: str | None
    status: str
    suggestion: str | None
    actual_root_cause: str | None
    actual_solution: str | None
    created_at: datetime
    completed_at: datetime | None


class FaultRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    alarm_id: int | None
    work_order_id: int | None
    fault_type: str
    fault_description: str | None
    root_cause: str | None
    solution: str | None
    fault_time: datetime
    created_at: datetime
