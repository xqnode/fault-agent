"""Smoke test Phase 1 closed loop against live DB (uses first PENDING alarm)."""

from app.core.database import SessionLocal
from app.schemas.common import AnalysisBootstrapCreate, WorkOrderComplete, WorkOrderCreate
from app.services import business


def main() -> None:
    db = SessionLocal()
    try:
        alarms = business.list_alarms(db, status="PENDING")
        if not alarms:
            print("No PENDING alarm; re-run seeds/init_db.ps1")
            return
        alarm = alarms[0]
        print("alarm", alarm.id, alarm.status)

        analysis = business.bootstrap_analysis(
            db,
            AnalysisBootstrapCreate(alarm_id=alarm.id),
        )
        print("analysis", analysis.id, analysis.engineer_decision)

        wo = business.create_work_order(db, WorkOrderCreate(analysis_id=analysis.id))
        print("work_order", wo.id, wo.work_order_no, wo.status)

        wo = business.start_work_order(db, wo.id)
        print("started", wo.status)

        wo = business.complete_work_order(
            db,
            wo.id,
            WorkOrderComplete(
                actual_root_cause="冷却液循环泵异常",
                actual_solution="更换循环泵并清洗管路",
            ),
        )
        print("completed", wo.status, wo.completed_at)

        alarm2 = business.get_alarm(db, alarm.id)
        device = business.get_device(db, alarm.device_id)
        faults = business.list_fault_records(db, device_id=alarm.device_id)
        print("alarm_after", alarm2.status, alarm2.resolved_at)
        print("device_after", device.device_code, device.status)
        print("fault_count", len(faults))
        print("PHASE1_LOOP_OK")
    finally:
        db.close()


if __name__ == "__main__":
    main()
