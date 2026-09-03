from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Device(Base):
    __tablename__ = "device"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    thresholds: Mapped[list["DeviceThreshold"]] = relationship(back_populates="device")
    alarms: Mapped[list["Alarm"]] = relationship(back_populates="device")


class DeviceThreshold(Base):
    __tablename__ = "device_threshold"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_type: Mapped[str | None] = mapped_column(String(32))
    device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    warning_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    alarm_max: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device | None] = relationship(back_populates="thresholds")


class DeviceSensorData(Base):
    __tablename__ = "device_sensor_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id", ondelete="CASCADE"), nullable=False)
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    pressure: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    vibration: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    power: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    record_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alarm(Base):
    __tablename__ = "alarm"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id", ondelete="CASCADE"), nullable=False)
    alarm_type: Mapped[str] = mapped_column(String(64), nullable=False)
    alarm_level: Mapped[str] = mapped_column(String(16), nullable=False)
    alarm_message: Mapped[str | None] = mapped_column(Text)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    measured_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship(back_populates="alarms")
    analyses: Mapped[list["AgentAnalysis"]] = relationship(back_populates="alarm")


class AgentAnalysis(Base):
    __tablename__ = "agent_analysis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alarm_id: Mapped[int] = mapped_column(ForeignKey("alarm.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    analysis_result: Mapped[dict | None] = mapped_column(JSONB)
    execution_trace: Mapped[dict | None] = mapped_column(JSONB)
    evidence_list: Mapped[dict | None] = mapped_column(JSONB)
    engineer_decision: Mapped[str | None] = mapped_column(String(32))
    selected_cause: Mapped[str | None] = mapped_column(Text)
    edit_recommendations: Mapped[dict | None] = mapped_column(JSONB)
    feedback_note: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    alarm: Mapped[Alarm] = relationship(back_populates="analyses")


class MaintenanceWorkOrder(Base):
    __tablename__ = "maintenance_work_order"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    work_order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), nullable=False)
    alarm_id: Mapped[int] = mapped_column(ForeignKey("alarm.id"), nullable=False)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("agent_analysis.id"), nullable=False)
    fault_description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    suggestion: Mapped[str | None] = mapped_column(Text)
    actual_root_cause: Mapped[str | None] = mapped_column(Text)
    actual_solution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FaultRecord(Base):
    __tablename__ = "fault_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("device.id"), nullable=False)
    alarm_id: Mapped[int | None] = mapped_column(ForeignKey("alarm.id"))
    work_order_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_work_order.id"))
    fault_type: Mapped[str] = mapped_column(String(64), nullable=False)
    fault_description: Mapped[str | None] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text)
    solution: Mapped[str | None] = mapped_column(Text)
    fault_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="ENGINEER")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
