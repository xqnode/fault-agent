"""Device simulator: sampling, retention, threshold debounce, scenario inject."""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Alarm, Device, DeviceSensorData, DeviceThreshold, MaintenanceWorkOrder
from app.simulator.scenarios import Scenario, get_scenario

logger = logging.getLogger(__name__)

METRIC_ALARM_TYPE = {
    "temperature": "TEMPERATURE_HIGH",
    "pressure": "PRESSURE_HIGH",
    "vibration": "VIBRATION_HIGH",
    "power": "POWER_HIGH",
}

OPEN_ALARM_STATUSES = ("PENDING", "ANALYZING", "ANALYZED", "FAILED")
OPEN_WO_STATUSES = ("DRAFT", "PENDING", "PROCESSING")


@dataclass
class ActiveScenarioState:
    scenario: Scenario
    device_id: int
    index: int = 0
    done: bool = False


@dataclass
class SimulatorStatus:
    running: bool = False
    sample_interval_seconds: int = 10
    retention_days: int = 7
    debounce_n: int = 3
    active_scenarios: dict[str, str] = field(default_factory=dict)
    last_tick_at: str | None = None
    last_alarm_id: int | None = None
    stop_pending: bool = False


class DeviceSimulator:
    def __init__(self) -> None:
        settings = get_settings()
        self.sample_interval_seconds = settings.simulator_sample_interval_seconds
        self.retention_days = settings.simulator_retention_days
        self.debounce_n = settings.simulator_debounce_n
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._generation = 0
        self._active: dict[int, ActiveScenarioState] = {}
        self._exceed_streak: dict[tuple[int, str], int] = {}
        self._last_tick_at: datetime | None = None
        self._last_alarm_id: int | None = None

    def status(self) -> SimulatorStatus:
        with self._lock:
            active = {
                str(device_id): state.scenario.code
                for device_id, state in self._active.items()
                if not state.done
            }
            thread_alive = bool(self._thread and self._thread.is_alive())
            return SimulatorStatus(
                running=self._running and thread_alive,
                sample_interval_seconds=self.sample_interval_seconds,
                retention_days=self.retention_days,
                debounce_n=self.debounce_n,
                active_scenarios=active,
                last_tick_at=self._last_tick_at.isoformat() if self._last_tick_at else None,
                last_alarm_id=self._last_alarm_id,
                stop_pending=bool(self._stop_event.is_set() and thread_alive),
            )

    def start(self) -> SimulatorStatus:
        with self._lock:
            if self._thread and self._thread.is_alive():
                if self._running and not self._stop_event.is_set():
                    return self.status()
                raise RuntimeError("simulator thread still stopping; retry start later")

            self._stop_event.clear()
            self._generation += 1
            generation = self._generation
            self._running = True
            self._thread = threading.Thread(
                target=self._loop,
                name="device-simulator",
                args=(generation,),
                daemon=True,
            )
            self._thread.start()
            logger.info("device simulator started generation=%s", generation)
            return self.status()

    def stop(self) -> SimulatorStatus:
        with self._lock:
            thread = self._thread
            if not thread:
                self._running = False
                return self.status()
            self._stop_event.set()
            self._running = False

        if thread.is_alive():
            thread.join(timeout=5)

        with self._lock:
            if thread.is_alive():
                # Do not drop the thread reference — prevents a second start()
                logger.warning("simulator thread still alive after stop timeout")
                return self.status()
            self._thread = None
            logger.info("device simulator stopped")
            return self.status()

    def inject(self, scenario_code: str, *, sync: bool = True) -> dict[str, Any]:
        """Inject a scenario. sync=True runs trajectory immediately (demo/acceptance)."""
        scenario = get_scenario(scenario_code)
        with self._lock:
            # Serialize against tick streak/active mutations
            with SessionLocal() as db:
                device = db.scalar(select(Device).where(Device.device_code == scenario.device_code))
                if not device:
                    raise ValueError(f"device not found: {scenario.device_code}")

                self._assert_device_injectable(db, device.id)

                # Only close PENDING same-type alarms (never ANALYZED / in-progress WO alarms)
                self._close_pending_metric_alarms(db, device.id, scenario.metric_name)
                self._exceed_streak.pop((device.id, scenario.metric_name), None)
                self._active.pop(device.id, None)

                if sync:
                    alarm = self._run_scenario_sync(db, device, scenario)
                    db.commit()
                    self._last_alarm_id = alarm.id if alarm else None
                    return {
                        "scenario_code": scenario.code,
                        "device_code": device.device_code,
                        "device_id": device.id,
                        "mode": "sync",
                        "points_written": len(scenario.trajectory),
                        "alarm_id": alarm.id if alarm else None,
                        "alarm_type": alarm.alarm_type if alarm else None,
                        "alarm_status": alarm.status if alarm else None,
                        "expected_alarm_type": scenario.expected_alarm_type,
                    }

                self._active[device.id] = ActiveScenarioState(
                    scenario=scenario,
                    device_id=device.id,
                    index=0,
                )
                db.commit()

        if not sync and not self.status().running:
            self.start()
        return {
            "scenario_code": scenario.code,
            "device_code": scenario.device_code,
            "mode": "async",
            "points_total": len(scenario.trajectory),
            "expected_alarm_type": scenario.expected_alarm_type,
        }

    def reset(self) -> dict[str, Any]:
        """Reset simulator runtime state and restore SMT-001 demo baseline safely."""
        was_running = False
        with self._lock:
            was_running = bool(self._thread and self._thread.is_alive() and self._running)
        if was_running or (self._thread and self._thread.is_alive()):
            self.stop()
            if self._thread and self._thread.is_alive():
                raise RuntimeError("cannot reset while simulator thread is still stopping")

        with self._lock:
            self._active.clear()
            self._exceed_streak.clear()
            self._last_alarm_id = None
            self._last_tick_at = None

        with SessionLocal() as db:
            device = db.scalar(select(Device).where(Device.device_code == "SMT-001"))
            cleared_alarms = 0
            deleted_sensors = 0
            cancelled_orders = 0
            if device:
                open_orders = list(
                    db.scalars(
                        select(MaintenanceWorkOrder).where(
                            MaintenanceWorkOrder.device_id == device.id,
                            MaintenanceWorkOrder.status.in_(list(OPEN_WO_STATUSES)),
                        )
                    ).all()
                )
                for wo in open_orders:
                    wo.status = "CANCELLED"
                    cancelled_orders += 1

                open_alarms = list(
                    db.scalars(
                        select(Alarm).where(
                            Alarm.device_id == device.id,
                            Alarm.status.in_(list(OPEN_ALARM_STATUSES)),
                        )
                    ).all()
                )
                now = datetime.now(timezone.utc)
                for alarm in open_alarms:
                    alarm.status = "RESOLVED"
                    alarm.resolved_at = now
                    cleared_alarms += 1

                result = db.execute(
                    delete(DeviceSensorData).where(DeviceSensorData.device_id == device.id)
                )
                deleted_sensors = result.rowcount or 0
                device.status = "RUNNING"
            self._purge_old_sensor_data(db)
            db.commit()

        if was_running:
            self.start()

        return {
            "running": self.status().running,
            "cleared_open_alarms": cleared_alarms,
            "cancelled_open_work_orders": cancelled_orders,
            "deleted_sensor_rows": deleted_sensors,
            "active_scenarios": {},
        }

    def _loop(self, generation: int) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                if generation != self._generation:
                    break
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                logger.exception("simulator tick failed")
            self._stop_event.wait(self.sample_interval_seconds)

    def tick(self) -> None:
        with self._lock:
            with SessionLocal() as db:
                devices = list(db.scalars(select(Device)).all())
                created_alarms: list[Alarm] = []
                for device in devices:
                    sample = self._next_sample_locked(device)
                    row = DeviceSensorData(
                        device_id=device.id,
                        temperature=Decimal(str(sample["temperature"])),
                        pressure=Decimal(str(sample["pressure"])),
                        vibration=Decimal(str(sample["vibration"])),
                        power=Decimal(str(sample["power"])),
                        record_time=datetime.now(timezone.utc),
                    )
                    db.add(row)
                    db.flush()
                    alarm = self._evaluate_thresholds_locked(db, device, sample)
                    if alarm:
                        created_alarms.append(alarm)
                self._purge_old_sensor_data(db)
                db.commit()
                self._last_tick_at = datetime.now(timezone.utc)
                if created_alarms:
                    self._last_alarm_id = created_alarms[-1].id

    def _run_scenario_sync(
        self, db: Session, device: Device, scenario: Scenario
    ) -> Alarm | None:
        alarm: Alarm | None = None
        base_time = datetime.now(timezone.utc) - timedelta(seconds=len(scenario.trajectory))
        for i, value in enumerate(scenario.trajectory):
            sample = self._sample_from_scenario(scenario, value)
            row = DeviceSensorData(
                device_id=device.id,
                temperature=Decimal(str(sample["temperature"])),
                pressure=Decimal(str(sample["pressure"])),
                vibration=Decimal(str(sample["vibration"])),
                power=Decimal(str(sample["power"])),
                record_time=base_time + timedelta(seconds=i),
            )
            db.add(row)
            db.flush()
            maybe = self._evaluate_thresholds_locked(db, device, sample)
            if maybe:
                alarm = maybe
        return alarm

    def _next_sample_locked(self, device: Device) -> dict[str, float]:
        state = self._active.get(device.id)
        if state and not state.done:
            if state.index >= len(state.scenario.trajectory):
                state.done = True
            else:
                value = state.scenario.trajectory[state.index]
                state.index += 1
                if state.index >= len(state.scenario.trajectory):
                    state.done = True
                return self._sample_from_scenario(state.scenario, value)
        return self._normal_sample(device.device_type)

    def _sample_from_scenario(self, scenario: Scenario, primary_value: float) -> dict[str, float]:
        sample = {
            "temperature": scenario.baseline_temperature,
            "pressure": scenario.baseline_pressure,
            "vibration": scenario.baseline_vibration,
            "power": scenario.baseline_power,
        }
        sample[scenario.metric_name] = float(primary_value)
        if scenario.metric_name == "temperature":
            sample["power"] = round(
                scenario.baseline_power + max(0.0, (primary_value - 80.0) * 0.04),
                4,
            )
        return sample

    def _normal_sample(self, device_type: str) -> dict[str, float]:
        base = {
            "SMT": {"temperature": 72.0, "pressure": 1.15, "vibration": 0.35, "power": 2.4},
            "REFLOW": {"temperature": 220.0, "pressure": 1.8, "vibration": 0.4, "power": 7.0},
            "ROBOT": {"temperature": 55.0, "pressure": 1.2, "vibration": 0.6, "power": 2.0},
            "ASSEMBLY": {"temperature": 60.0, "pressure": 1.3, "vibration": 0.5, "power": 3.2},
        }.get(device_type, {"temperature": 70.0, "pressure": 1.2, "vibration": 0.4, "power": 2.5})
        return {
            "temperature": round(base["temperature"] + random.uniform(-1.5, 1.5), 4),
            "pressure": round(base["pressure"] + random.uniform(-0.05, 0.05), 4),
            "vibration": round(base["vibration"] + random.uniform(-0.05, 0.05), 4),
            "power": round(base["power"] + random.uniform(-0.1, 0.1), 4),
        }

    def _resolve_threshold(
        self, db: Session, device: Device, metric_name: str
    ) -> DeviceThreshold | None:
        device_level = db.scalar(
            select(DeviceThreshold).where(
                DeviceThreshold.device_id == device.id,
                DeviceThreshold.metric_name == metric_name,
            )
        )
        if device_level:
            return device_level
        return db.scalar(
            select(DeviceThreshold).where(
                DeviceThreshold.device_type == device.device_type,
                DeviceThreshold.device_id.is_(None),
                DeviceThreshold.metric_name == metric_name,
            )
        )

    def _evaluate_thresholds_locked(
        self, db: Session, device: Device, sample: dict[str, float]
    ) -> Alarm | None:
        created: Alarm | None = None
        for metric_name, value in sample.items():
            threshold = self._resolve_threshold(db, device, metric_name)
            if not threshold:
                continue
            alarm_max = float(threshold.alarm_max)
            key = (device.id, metric_name)
            if value > alarm_max:
                self._exceed_streak[key] = self._exceed_streak.get(key, 0) + 1
            else:
                self._exceed_streak[key] = 0
                continue

            if self._exceed_streak[key] < self.debounce_n:
                continue
            if self._has_open_alarm(db, device.id, METRIC_ALARM_TYPE[metric_name]):
                continue

            alarm = Alarm(
                device_id=device.id,
                alarm_type=METRIC_ALARM_TYPE[metric_name],
                alarm_level="HIGH",
                alarm_message=(
                    f"{device.device_code} {metric_name} 过高，"
                    f"实测 {value}，阈值 {alarm_max}"
                ),
                metric_name=metric_name,
                measured_value=Decimal(str(value)),
                threshold_value=Decimal(str(alarm_max)),
                snapshot_json={k: float(v) for k, v in sample.items()},
                status="PENDING",
            )
            db.add(alarm)
            if device.status == "RUNNING":
                device.status = "WARNING"
            db.flush()
            created = alarm
            self._exceed_streak[key] = 0
        return created

    def _has_open_alarm(self, db: Session, device_id: int, alarm_type: str) -> bool:
        return (
            db.scalar(
                select(Alarm.id).where(
                    Alarm.device_id == device_id,
                    Alarm.alarm_type == alarm_type,
                    Alarm.status.in_(list(OPEN_ALARM_STATUSES)),
                )
            )
            is not None
        )

    def _assert_device_injectable(self, db: Session, device_id: int) -> None:
        open_wo = db.scalar(
            select(func.count())
            .select_from(MaintenanceWorkOrder)
            .where(
                MaintenanceWorkOrder.device_id == device_id,
                MaintenanceWorkOrder.status.in_(list(OPEN_WO_STATUSES)),
            )
        )
        if open_wo:
            raise ValueError(
                "device has open work orders; complete/cancel them before inject"
            )

        blocked = db.scalar(
            select(func.count())
            .select_from(Alarm)
            .where(
                Alarm.device_id == device_id,
                Alarm.status.in_(["ANALYZING", "ANALYZED"]),
            )
        )
        if blocked:
            raise ValueError(
                "device has ANALYZING/ANALYZED alarms; finish the closed loop before inject"
            )

    def _close_pending_metric_alarms(self, db: Session, device_id: int, metric_name: str) -> None:
        alarm_type = METRIC_ALARM_TYPE[metric_name]
        now = datetime.now(timezone.utc)
        alarms = list(
            db.scalars(
                select(Alarm).where(
                    Alarm.device_id == device_id,
                    Alarm.alarm_type == alarm_type,
                    Alarm.status.in_(["PENDING", "FAILED"]),
                )
            ).all()
        )
        for alarm in alarms:
            alarm.status = "RESOLVED"
            alarm.resolved_at = now

    def _purge_old_sensor_data(self, db: Session) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        db.execute(delete(DeviceSensorData).where(DeviceSensorData.record_time < cutoff))


_simulator: DeviceSimulator | None = None
_simulator_lock = threading.Lock()


def get_simulator() -> DeviceSimulator:
    global _simulator
    with _simulator_lock:
        if _simulator is None:
            _simulator = DeviceSimulator()
        return _simulator
