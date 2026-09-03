"""Phase 2 verification against DOC-04 acceptance criteria."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Alarm, Device, DeviceSensorData
from app.simulator.device_simulator import get_simulator
from sqlalchemy import func, select


@dataclass
class Report:
    items: list[tuple[str, bool, str]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.items.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def all_ok(self) -> bool:
        return all(ok for _, ok, _ in self.items)


def main() -> int:
    report = Report()
    settings = get_settings()
    sim = get_simulator()

    try:
        report.add(
            "配置：采样周期在 10~30 秒",
            10 <= settings.simulator_sample_interval_seconds <= 30,
            str(settings.simulator_sample_interval_seconds),
        )
        report.add(
            "配置：保留天数=7 / 防抖N=3",
            settings.simulator_retention_days == 7 and settings.simulator_debounce_n == 3,
            f"days={settings.simulator_retention_days}, n={settings.simulator_debounce_n}",
        )

        # ensure clean slate
        reset1 = sim.reset()
        report.add("API能力：reset 可执行", True, str(reset1))

        # inject must create TEMPERATURE_HIGH with full snapshot
        result = sim.inject("SMT_TEMP_RISE_001", sync=True)
        alarm_id = result.get("alarm_id")
        report.add(
            "验收：inject(SMT_TEMP_RISE_001) 产生 TEMPERATURE_HIGH",
            result.get("alarm_type") == "TEMPERATURE_HIGH" and alarm_id is not None,
            str(result),
        )

        with SessionLocal() as db:
            alarm = db.get(Alarm, alarm_id) if alarm_id else None
            snapshot_ok = bool(
                alarm
                and alarm.measured_value is not None
                and alarm.threshold_value is not None
                and isinstance(alarm.snapshot_json, dict)
                and "temperature" in alarm.snapshot_json
                and "power" in alarm.snapshot_json
            )
            report.add(
                "验收：报警快照字段完整",
                snapshot_ok,
                None
                if not alarm
                else {
                    "measured_value": str(alarm.measured_value),
                    "threshold_value": str(alarm.threshold_value),
                    "snapshot_json": alarm.snapshot_json,
                    "status": alarm.status,
                }.__str__(),
            )

            device = db.scalar(select(Device).where(Device.device_code == "SMT-001"))
            sensor_count = db.scalar(
                select(func.count()).select_from(DeviceSensorData).where(
                    DeviceSensorData.device_id == device.id
                )
            )
            report.add(
                "任务：inject 写入传感器采样",
                (sensor_count or 0) >= 6,
                f"sensor_count={sensor_count}",
            )
            report.add(
                "状态：设备进入 WARNING",
                device is not None and device.status == "WARNING",
                None if not device else device.status,
            )

        # reset then inject again => repeatable
        sim.reset()
        result2 = sim.inject("SMT_TEMP_RISE_001", sync=True)
        report.add(
            "验收：reset 后可重复演示",
            result2.get("alarm_type") == "TEMPERATURE_HIGH" and result2.get("alarm_id") is not None,
            str(result2),
        )

        # background start/stop + one tick
        status = sim.start()
        report.add("任务：simulator start", status.running is True, str(status.__dict__))
        before = SessionLocal()
        try:
            device = before.scalar(select(Device).where(Device.device_code == "SMT-001"))
            count_before = before.scalar(
                select(func.count()).select_from(DeviceSensorData).where(
                    DeviceSensorData.device_id == device.id
                )
            )
        finally:
            before.close()

        sim.tick()
        after = SessionLocal()
        try:
            device = after.scalar(select(Device).where(Device.device_code == "SMT-001"))
            count_after = after.scalar(
                select(func.count()).select_from(DeviceSensorData).where(
                    DeviceSensorData.device_id == device.id
                )
            )
        finally:
            after.close()
        report.add(
            "任务：tick 持续采样写入",
            (count_after or 0) > (count_before or 0),
            f"before={count_before}, after={count_after}",
        )

        stopped = sim.stop()
        report.add("任务：simulator stop", stopped.running is False, str(stopped.__dict__))

        # HTTP API
        with TestClient(app) as client:
            import sys
            from pathlib import Path

            scripts_dir = Path(__file__).resolve().parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from auth_helper import login_headers

            headers = login_headers(client)
            r_status = client.get("/api/simulator/status", headers=headers)
            r_inject = client.post(
                "/api/simulator/inject",
                headers=headers,
                json={"scenario_code": "SMT_TEMP_RISE_001", "sync": True},
            )
            r_reset = client.post("/api/simulator/reset", headers=headers)
            report.add(
                "任务：HTTP simulator 接口可用",
                r_status.status_code == 200
                and r_inject.status_code == 200
                and r_reset.status_code == 200
                and r_inject.json().get("data", {}).get("alarm_type") == "TEMPERATURE_HIGH",
                f"status={r_status.status_code}, inject={r_inject.status_code}, reset={r_reset.status_code}",
            )

            paths = set(app.openapi().get("paths", {}).keys())
            required = {
                "/api/simulator/start",
                "/api/simulator/stop",
                "/api/simulator/inject",
                "/api/simulator/reset",
                "/api/simulator/status",
            }
            report.add(
                "任务：Simulator OpenAPI 路由齐全",
                required <= paths,
                f"missing={sorted(required - paths)}",
            )

        # leave demo ready: one pending alarm via inject after final reset
        sim.reset()
        final = sim.inject("SMT_TEMP_RISE_001", sync=True)
        report.add(
            "收尾：demo 报警已就绪",
            final.get("alarm_id") is not None,
            str(final),
        )

    except Exception as exc:  # noqa: BLE001
        report.add("执行异常", False, f"{exc}\n{traceback.format_exc()}")
    finally:
        try:
            get_simulator().stop()
        except Exception:  # noqa: BLE001
            pass
        engine.dispose()

    passed = sum(1 for _, ok, _ in report.items if ok)
    failed = sum(1 for _, ok, _ in report.items if not ok)
    print("\n==== SUMMARY ====")
    print(f"passed={passed} failed={failed} total={len(report.items)}")
    return 0 if report.all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
