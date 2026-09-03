"""Phase 3 verification: dashboard API + frontend build + inject visibility."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.simulator.device_simulator import get_simulator

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    # API overview fields
    with TestClient(app) as client:
        import sys
        from pathlib import Path

        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from auth_helper import login_headers

        headers = login_headers(client)
        r = client.get("/api/dashboard/overview", headers=headers)
        data = r.json().get("data", {})
        add(
            "Dashboard overview 可用",
            r.status_code == 200 and "device_total" in data and "alarm_trend" in data,
            f"keys={sorted(data.keys())}",
        )
        add(
            "含状态分布与最近报警",
            "status_distribution" in data and "recent_alarms" in data,
            f"trend_len={len(data.get('alarm_trend', []))}",
        )

        # inject then overview pending/warning should move
        get_simulator().reset()
        before_pending = data.get("alarm_pending", 0)
        inj = client.post(
            "/api/simulator/inject",
            headers=headers,
            json={"scenario_code": "SMT_TEMP_RISE_001", "sync": True},
        )
        after = client.get("/api/dashboard/overview", headers=headers).json().get("data", {})
        add(
            "注入剧本后 overview 可见状态变化",
            inj.status_code == 200
            and after.get("alarm_pending", 0) >= 1
            and after.get("device_warning", 0) >= 1,
            f"before_pending={before_pending}, after={json.dumps({k: after.get(k) for k in ['alarm_pending','device_warning','device_running']})}",
        )

        # CORS preflight-ish headers via middleware presence: OPTIONS
        opt = client.options(
            "/api/dashboard/overview",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        add(
            "CORS 允许前端源",
            opt.headers.get("access-control-allow-origin") == "http://localhost:5173",
            str(opt.headers.get("access-control-allow-origin")),
        )

        login_page = FRONTEND / "src/views/LoginView.vue"
        add("登录页存在", login_page.exists(), str(login_page.relative_to(ROOT)))

    # frontend pages exist
    required_files = [
        FRONTEND / "src/views/DashboardView.vue",
        FRONTEND / "src/views/DevicesView.vue",
        FRONTEND / "src/views/DeviceDetailView.vue",
        FRONTEND / "src/views/AlarmsView.vue",
        FRONTEND / "src/views/AlarmDetailView.vue",
        FRONTEND / "src/layouts/MainLayout.vue",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required_files if not p.exists()]
    add("前端页面文件齐全", not missing, f"missing={missing}")

    # build frontend
    build = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        shell=True,
    )
    add(
        "前端 build 成功",
        build.returncode == 0,
        (build.stderr or build.stdout)[-400:],
    )

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print("\n==== SUMMARY ====")
    print(f"passed={passed} failed={failed} total={len(results)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
