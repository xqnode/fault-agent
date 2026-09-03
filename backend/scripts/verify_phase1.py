"""Phase 1 verification against DOC-04 acceptance criteria."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal, engine
from app.main import app
from app.schemas.common import (
    AlarmCreate,
    AnalysisBootstrapCreate,
    DeviceCreate,
    ThresholdCreate,
    WorkOrderComplete,
    WorkOrderCreate,
)
from app.services import business


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    items: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.items.append(CheckResult(name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def all_ok(self) -> bool:
        return all(i.ok for i in self.items)


def collect_paths(routes) -> set[str]:
    paths: set[str] = set()
    for route in routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            paths.add(path)
        children = getattr(route, "routes", None)
        if children:
            paths |= collect_paths(children)
    return paths


def expect_http_error(fn, status_code: int) -> tuple[bool, str]:
    try:
        fn()
        return False, "expected HTTPException but succeeded"
    except HTTPException as exc:
        if exc.status_code == status_code:
            return True, f"HTTP {exc.status_code}: {exc.detail}"
        return False, f"expected {status_code}, got {exc.status_code}: {exc.detail}"
    except Exception as exc:  # noqa: BLE001
        return False, f"unexpected {type(exc).__name__}: {exc}"


def cleanup_test_device(db, code: str) -> None:
    device_id = db.execute(text("SELECT id FROM device WHERE device_code=:c"), {"c": code}).scalar()
    if not device_id:
        return
    db.execute(
        text(
            "DELETE FROM fault_record WHERE device_id=:id OR work_order_id IN "
            "(SELECT id FROM maintenance_work_order WHERE device_id=:id)"
        ),
        {"id": device_id},
    )
    db.execute(text("DELETE FROM maintenance_work_order WHERE device_id=:id"), {"id": device_id})
    db.execute(
        text(
            "DELETE FROM agent_analysis WHERE alarm_id IN "
            "(SELECT id FROM alarm WHERE device_id=:id)"
        ),
        {"id": device_id},
    )
    db.execute(text("DELETE FROM alarm WHERE device_id=:id"), {"id": device_id})
    db.execute(text("DELETE FROM device_sensor_data WHERE device_id=:id"), {"id": device_id})
    db.execute(text("DELETE FROM device_threshold WHERE device_id=:id"), {"id": device_id})
    db.execute(text("DELETE FROM device WHERE id=:id"), {"id": device_id})
    db.commit()


def main() -> int:
    report = Report()
    db = SessionLocal()
    code = "TST-PHASE1-001"

    try:
        cleanup_test_device(db, code)

        tables = {
            "device",
            "device_threshold",
            "device_sensor_data",
            "alarm",
            "agent_analysis",
            "maintenance_work_order",
            "fault_record",
        }
        existing = set(
            db.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname='public' AND tablename = ANY(:names)"
                ),
                {"names": list(tables)},
            ).scalars()
        )
        report.add("任务：建表齐全", tables <= existing, f"missing={sorted(tables - existing)}")

        id_style = db.execute(
            text(
                "SELECT is_identity, identity_generation "
                "FROM information_schema.columns "
                "WHERE table_name='device' AND column_name='id'"
            )
        ).one()
        report.add(
            "规范：主键 IDENTITY ALWAYS",
            id_style[0] == "YES" and id_style[1] == "ALWAYS",
            str(id_style),
        )

        comments = db.execute(
            text(
                "SELECT obj_description('device'::regclass), "
                "col_description('device'::regclass, 1)"
            )
        ).one()
        report.add(
            "规范：表/字段中文注释",
            bool(comments[0]) and bool(comments[1]),
            f"table={comments[0]!r}",
        )

        device = business.create_device(
            db,
            DeviceCreate(
                device_code=code,
                device_name="Phase1验收测试机",
                device_type="SMT",
                location="测试区",
            ),
        )
        thr = business.create_threshold(
            db,
            ThresholdCreate(
                device_id=device.id,
                metric_name="temperature",
                warning_max=85,
                alarm_max=90,
                unit="℃",
            ),
        )
        report.add(
            "验收：可创建设备与阈值",
            device.id > 0 and thr.id > 0,
            f"device_id={device.id}, threshold_id={thr.id}",
        )

        alarm = business.create_alarm(
            db,
            AlarmCreate(
                device_id=device.id,
                alarm_type="TEMPERATURE_HIGH",
                alarm_level="HIGH",
                alarm_message="验收测试高温报警",
                metric_name="temperature",
                measured_value=98,
                threshold_value=90,
                snapshot_json={
                    "temperature": 98,
                    "pressure": 1.2,
                    "vibration": 0.4,
                    "power": 3.1,
                },
            ),
        )
        fetched = business.get_alarm(db, alarm.id)
        device_after_alarm = business.get_device(db, device.id)
        report.add(
            "验收：可创建/查询含 snapshot 的报警",
            fetched.snapshot_json.get("temperature") == 98
            and fetched.measured_value is not None
            and fetched.threshold_value is not None,
            f"alarm_id={fetched.id}",
        )
        report.add(
            "状态：HIGH 报警后设备 WARNING",
            device_after_alarm.status == "WARNING",
            device_after_alarm.status,
        )

        analysis = business.bootstrap_analysis(
            db, AnalysisBootstrapCreate(alarm_id=alarm.id)
        )
        wo = business.create_work_order(
            db, WorkOrderCreate(analysis_id=analysis.id, priority="HIGH")
        )
        wo = business.start_work_order(db, wo.id)
        before_faults = len(business.list_fault_records(db, device_id=device.id))
        wo = business.complete_work_order(
            db,
            wo.id,
            WorkOrderComplete(actual_root_cause="验收根因", actual_solution="验收措施"),
        )
        alarm_done = business.get_alarm(db, alarm.id)
        device_done = business.get_device(db, device.id)
        after_faults = business.list_fault_records(db, device_id=device.id)
        report.add(
            "验收：complete 后 fault_record + alarm=RESOLVED",
            wo.status == "COMPLETED"
            and alarm_done.status == "RESOLVED"
            and alarm_done.resolved_at is not None
            and len(after_faults) == before_faults + 1,
            f"wo={wo.status}, alarm={alarm_done.status}, faults={len(after_faults)}",
        )
        report.add(
            "状态：结单后设备恢复 RUNNING",
            device_done.status == "RUNNING",
            device_done.status,
        )

        ok, detail = expect_http_error(lambda: business.start_work_order(db, wo.id), 400)
        report.add("验收：非法跳转拒绝（COMPLETED 不可 start）", ok, detail)

        alarm2 = business.create_alarm(
            db,
            AlarmCreate(
                device_id=device.id,
                alarm_type="TEMPERATURE_HIGH",
                alarm_level="HIGH",
                alarm_message="用于非法跳转测试",
                metric_name="temperature",
                measured_value=95,
                threshold_value=90,
                snapshot_json={
                    "temperature": 95,
                    "pressure": 1.1,
                    "vibration": 0.3,
                    "power": 2.8,
                },
            ),
        )
        analysis2 = business.bootstrap_analysis(
            db, AnalysisBootstrapCreate(alarm_id=alarm2.id)
        )
        analysis2.engineer_decision = "REJECTED"
        db.commit()
        ok, detail = expect_http_error(
            lambda: business.create_work_order(
                db, WorkOrderCreate(analysis_id=analysis2.id)
            ),
            400,
        )
        report.add("验收：非法跳转拒绝（未确认不可建单）", ok, detail)

        analysis2.engineer_decision = "APPROVED"
        db.commit()
        wo2 = business.create_work_order(db, WorkOrderCreate(analysis_id=analysis2.id))
        ok, detail = expect_http_error(
            lambda: business.complete_work_order(
                db,
                wo2.id,
                WorkOrderComplete(actual_root_cause="x", actual_solution="y"),
            ),
            400,
        )
        report.add("验收：非法跳转拒绝（PENDING 不可 complete）", ok, detail)

        # 以 OpenAPI 为准（include_router 在部分 Starlette 版本不直接暴露 path）
        paths = set(app.openapi().get("paths", {}).keys())
        required = {
            "/api/auth/login",
            "/api/auth/me",
            "/api/devices",
            "/api/device-thresholds",
            "/api/alarms",
            "/api/work-orders",
            "/api/work-orders/{work_order_id}/start",
            "/api/work-orders/{work_order_id}/complete",
            "/api/analysis/bootstrap",
            "/api/dashboard/overview",
        }
        report.add(
            "任务：Phase1 API 路由齐全",
            required <= paths,
            f"missing={sorted(required - paths)}",
        )

        with TestClient(app) as client:
            from pathlib import Path
            import sys

            scripts_dir = Path(__file__).resolve().parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from auth_helper import login_headers

            headers = login_headers(client)
            r1 = client.get("/health")
            r2 = client.get("/api/dashboard/overview", headers=headers)
            r3 = client.get("/api/devices", headers=headers)
            r4 = client.get("/api/alarms", headers=headers)
            report.add(
                "任务：HTTP 健康检查与只读接口",
                r1.status_code == 200
                and r2.status_code == 200
                and r3.status_code == 200
                and r4.status_code == 200
                and r2.json().get("code") == 0,
                f"health={r1.status_code}, overview={r2.status_code}, devices={r3.status_code}",
            )

            devices_payload = r3.json()["data"]
            devices = devices_payload["items"] if isinstance(devices_payload, dict) else devices_payload
            smt = next(d for d in devices if d["device_code"] == "SMT-001")
            r5 = client.post(
                "/api/alarms",
                headers=headers,
                json={
                    "device_id": smt["id"],
                    "alarm_type": "TEMPERATURE_HIGH",
                    "alarm_level": "HIGH",
                    "alarm_message": "HTTP验收报警",
                    "metric_name": "temperature",
                    "measured_value": 97,
                    "threshold_value": 90,
                    "snapshot_json": {
                        "temperature": 97,
                        "pressure": 1.15,
                        "vibration": 0.35,
                        "power": 2.9,
                    },
                },
            )
            report.add(
                "任务：HTTP 创建报警（含 snapshot）",
                r5.status_code == 200 and r5.json().get("code") == 0,
                f"status={r5.status_code}",
            )

        seed_devices = db.execute(text("SELECT count(*) FROM device")).scalar()
        report.add(
            "任务：种子数据可读写",
            seed_devices is not None and seed_devices >= 5,
            f"device_count={seed_devices}",
        )

        cleanup_test_device(db, code)

    except Exception as exc:  # noqa: BLE001
        report.add("执行异常", False, f"{exc}\n{traceback.format_exc()}")
        db.rollback()
    finally:
        db.close()
        engine.dispose()

    print("\n==== SUMMARY ====")
    passed = sum(1 for i in report.items if i.ok)
    failed = sum(1 for i in report.items if not i.ok)
    print(f"passed={passed} failed={failed} total={len(report.items)}")
    return 0 if report.all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
