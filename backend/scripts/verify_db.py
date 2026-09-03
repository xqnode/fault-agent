from sqlalchemy import text

from app.core.database import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        print("devices:", db.execute(text("SELECT count(*) FROM device")).scalar())
        print(
            "SMT-001:",
            db.execute(
                text("SELECT device_code, status FROM device WHERE device_code='SMT-001'")
            ).all(),
        )
        print(
            "alarms:",
            db.execute(
                text(
                    "SELECT id, alarm_type, status, measured_value, threshold_value "
                    "FROM alarm"
                )
            ).all(),
        )
        print(
            "fault_records:",
            db.execute(text("SELECT count(*) FROM fault_record")).scalar(),
        )
        print(
            "thresholds:",
            db.execute(text("SELECT count(*) FROM device_threshold")).scalar(),
        )
        print("OK")
    finally:
        db.close()


if __name__ == "__main__":
    main()
