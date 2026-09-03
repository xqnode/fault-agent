# Backend (Phase 1)

## 数据库

```powershell
pwsh ./seeds/init_db.ps1
```

连接串（见 `backend/.env`）：

```text
postgresql+psycopg://postgres:123456@localhost:5432/fault_agent
```

## 启动

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --port 8000
```

## Phase 1 验收

```powershell
cd backend
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe scripts\verify_phase1.py
```

通过标准：输出 `passed=15 failed=0`。

## Phase 2 模拟器

```powershell
# 注入黄金剧本（同步立即出报警）
POST /api/simulator/inject
{ "scenario_code": "SMT_TEMP_RISE_001", "sync": true }

# 其他
POST /api/simulator/start
POST /api/simulator/stop
POST /api/simulator/reset
GET  /api/simulator/status
```

验收：

```powershell
.\.venv\Scripts\python.exe scripts\verify_phase2.py
```

## 说明

- 正式 AI 分析在 Phase 6；当前用 `POST /api/analysis/bootstrap` 模拟已确认分析，便于测工单闭环。
- 重新灌种子会清空业务表数据。
- Phase 2 默认采样间隔 10s、保留 7 天、防抖连续 3 次超限。
