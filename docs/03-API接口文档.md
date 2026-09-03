# DOC-03 API 接口文档

> 文档编号：DOC-03  
> 文件：`03-API接口文档.md`  
> 项目：制造业智能故障分析 Agent  
> 风格：REST + SSE  
> Base URL：`/api`  
> 依据：DOC-01、DOC-02  
> 配套：DOC-04 分阶段开发

---

## 1. 约定

### 1.1 通用响应

成功：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

失败：

```json
{
  "code": 40001,
  "message": "业务错误说明",
  "data": null
}
```

### 1.2 常见错误码

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40001 | 参数错误 |
| 40002 | 状态不允许 |
| 40401 | 资源不存在 |
| 40901 | 冲突（如已有 RUNNING 分析） |
| 50000 | 服务内部错误 |

### 1.3 时间与分页

- 时间字段：ISO-8601，带时区
- 列表默认分页：`page`（从 1 开始）、`page_size`（默认 20）

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 1.4 实时策略

- Dashboard / 设备监控：前端 5~10 秒轮询即可（MVP 不上 WebSocket）
- Agent 执行过程：使用 SSE `GET /api/analysis/{analysis_id}/stream`

---

## 2. Dashboard

### GET `/api/dashboard/overview`

工厂总览。

**Response `data` 示例：**

```json
{
  "device_total": 12,
  "device_running": 9,
  "device_warning": 2,
  "device_fault": 1,
  "alarm_pending": 3,
  "alarm_analyzing": 1,
  "recent_alarms": [
    {
      "id": 101,
      "device_code": "SMT-001",
      "alarm_type": "TEMPERATURE_HIGH",
      "alarm_level": "HIGH",
      "status": "PENDING",
      "created_at": "2026-09-03T10:20:00+08:00"
    }
  ],
  "alarm_trend": [
    {"date": "2026-09-01", "count": 4},
    {"date": "2026-09-02", "count": 6},
    {"date": "2026-09-03", "count": 3}
  ]
}
```

---

## 3. 设备

### GET `/api/devices`

设备列表。

**Query**

| 参数 | 说明 |
|------|------|
| device_type | 可选 |
| status | 可选 |
| page / page_size | 分页 |

**Response item 示例：**

```json
{
  "id": 1,
  "device_code": "SMT-001",
  "device_name": "SMT贴片机",
  "device_type": "SMT",
  "location": "生产车间A",
  "status": "RUNNING"
}
```

### GET `/api/devices/{id}`

设备详情（可附带阈值）。

```json
{
  "id": 1,
  "device_code": "SMT-001",
  "device_name": "SMT贴片机",
  "device_type": "SMT",
  "location": "生产车间A",
  "status": "WARNING",
  "thresholds": [
    {
      "metric_name": "temperature",
      "warning_max": 85,
      "alarm_max": 90,
      "unit": "℃"
    }
  ]
}
```

### GET `/api/devices/{id}/sensor-data`

传感器时序数据。

**Query**

| 参数 | 说明 |
|------|------|
| from / to | 时间窗，可选 |
| limit | 默认最近 N 条 |

```json
{
  "device_id": 1,
  "points": [
    {
      "record_time": "2026-09-03T10:00:00+08:00",
      "temperature": 72,
      "pressure": 1.1,
      "vibration": 0.3,
      "power": 2.2
    }
  ]
}
```

> Agent Tool 侧应对同类数据做聚合，不要把原始海量点位直接塞给 LLM。

### POST `/api/devices`（Phase 1 内部/管理用）

创建设备。MVP 可先用种子数据，接口建议保留。

### POST `/api/device-thresholds`（Phase 1）

创建/更新机型阈值。

```json
{
  "device_type": "SMT",
  "metric_name": "temperature",
  "warning_max": 85,
  "alarm_max": 90,
  "unit": "℃"
}
```

---

## 4. 报警

### GET `/api/alarms`

报警列表。

**Query：** `status` / `device_id` / `alarm_level` / 分页

### GET `/api/alarms/{id}`

报警详情。

```json
{
  "id": 101,
  "device_id": 1,
  "device_code": "SMT-001",
  "alarm_type": "TEMPERATURE_HIGH",
  "alarm_level": "HIGH",
  "alarm_message": "设备温度过高",
  "metric_name": "temperature",
  "measured_value": 98,
  "threshold_value": 90,
  "snapshot_json": {
    "temperature": 98,
    "pressure": 1.2,
    "vibration": 0.4,
    "power": 3.1
  },
  "status": "PENDING",
  "created_at": "2026-09-03T10:20:00+08:00",
  "resolved_at": null,
  "latest_analysis_id": null
}
```

---

## 5. AI 分析

### POST `/api/analysis/{alarm_id}`

创建分析（幂等）。

**行为**

1. 若该报警已有 `RUNNING` 分析：直接返回该记录，`reused=true`（HTTP 200，不新建）
2. 若最近一次为 `SUCCEEDED` 且业务上不允许重复分析：返回已有成功记录，`reused=true`（MVP 默认允许对 `FAILED` 重跑；对 `SUCCEEDED` 默认复用最近成功记录，除非 query `force=true`）
3. 若上一次 `FAILED` 或尚无分析：新建，`reused=false`
4. 成功创建后：`alarm.status = ANALYZING`，`analysis.status = RUNNING`

**Response：**

```json
{
  "analysis_id": 501,
  "alarm_id": 101,
  "status": "RUNNING",
  "reused": false
}
```

### GET `/api/analysis/{analysis_id}`

查询分析结果。

```json
{
  "id": 501,
  "alarm_id": 101,
  "status": "SUCCEEDED",
  "analysis_result": {
    "summary": "检测到 SMT-001 高温报警",
    "observations": ["最近2小时温度从72℃升至98℃"],
    "possible_causes": [
      {
        "cause": "冷却系统异常",
        "likelihood": "HIGH",
        "evidence": ["历史类似故障多为冷却异常", "SOP 优先检查冷却系统"]
      }
    ],
    "recommendations": ["检查冷却液循环", "检查散热风扇"],
    "evidence_insufficient": false
  },
  "evidence_list": [],
  "execution_trace": [],
  "engineer_decision": null,
  "selected_cause": null,
  "edit_recommendations": null,
  "feedback_note": null,
  "error_message": null
}
```

### GET `/api/analysis/{analysis_id}/stream`

SSE 执行轨迹。

**Content-Type：** `text/event-stream`

事件示例：

```text
event: node
data: {"name":"load_alarm","status":"done","message":"加载报警信息"}

event: tool
data: {"name":"get_sensor_data","status":"done","message":"温度持续上升，功率同步上升"}

event: node
data: {"name":"generate_report","status":"done"}

event: done
data: {"analysis_id":501,"status":"SUCCEEDED"}
```

约束：

- 禁止推送模型内部思维链
- 只推送节点/工具级轨迹

### POST `/api/analysis/{analysis_id}/decision`

工程师 HITL 确认。

**Body**

```json
{
  "engineer_decision": "EDITED",
  "selected_cause": "冷却系统异常",
  "edit_recommendations": ["检查冷却液循环", "检查散热风扇", "检查风扇滤网"],
  "feedback_note": "同意主因，补充检查风扇滤网"
}
```

| engineer_decision | 含义 |
|-------------------|------|
| APPROVED | 直接采纳 |
| EDITED | 修改后采纳 |
| REJECTED | 驳回，不创建工单 |

**规则**

- 仅 `SUCCEEDED` 的分析可确认
- `APPROVED` / `EDITED` 后才允许创建工单
- `REJECTED` 不创建工单

---

## 6. 工单

### GET `/api/work-orders`

工单列表。支持 `status` / `device_id` 过滤。

### POST `/api/work-orders`

从已确认分析创建工单。

**Body**

```json
{
  "analysis_id": 501,
  "priority": "HIGH"
}
```

**规则**

- `analysis.engineer_decision` 必须为 `APPROVED` 或 `EDITED`
- 写入 `device_id` / `alarm_id` / `suggestion` 等
- 初始状态：`PENDING`（或先 `DRAFT` 再提交，MVP 可直接 `PENDING`）

### POST `/api/work-orders/{id}/start`

开始处理：`PENDING → PROCESSING`

### POST `/api/work-orders/{id}/complete`

结单并闭环回写。

**Body**

```json
{
  "actual_root_cause": "冷却液循环泵异常",
  "actual_solution": "更换循环泵并清洗管路"
}
```

**副作用（同一事务）**

1. 工单 → `COMPLETED`
2. 写入 `fault_record`
3. `alarm → RESOLVED`
4. 视情况恢复设备 `RUNNING`

---

## 7. 模拟器

### POST `/api/simulator/start`

启动模拟采样。

### POST `/api/simulator/stop`

停止模拟。

### POST `/api/simulator/inject`

注入故障剧本。

**Body**

```json
{
  "scenario_code": "SMT_TEMP_RISE_001"
}
```

预期：温度逐步升高，最终稳定产生 `TEMPERATURE_HIGH`，且报警含快照字段。

### POST `/api/simulator/reset`

重置模拟状态与可重复演示数据（不清空全部历史亦可，但需保证黄金路径可复现）。

---

## 8. 知识库（Phase 4，内部/管理）

MVP 可先脚本 ingest，不一定全部做成页面。建议保留：

### POST `/api/knowledge/ingest`

导入文档并切块写入 `knowledge_chunk`（含 embedding）。

### POST `/api/knowledge/search`

调试检索（带 metadata filter）。

**Body**

```json
{
  "query": "SMT 高温报警处理",
  "device_type": "SMT",
  "alarm_type": "TEMPERATURE_HIGH",
  "top_k": 5
}
```

---

## 9. 关键业务时序

```text
inject scenario
   ↓
产生 alarm(PENDING)
   ↓
POST /analysis/{alarm_id}
   ↓
GET /analysis/{id}/stream   （前端展示轨迹）
   ↓
分析 SUCCEEDED，alarm=ANALYZED
   ↓
POST /analysis/{id}/decision
   ↓
POST /work-orders
   ↓
POST /work-orders/{id}/start
   ↓
POST /work-orders/{id}/complete
   ↓
fault_record 写入，alarm=RESOLVED
```

---

## 10. 前端页面对应

| 页面 | 主要接口 |
|------|----------|
| Dashboard | `GET /dashboard/overview` |
| 设备管理 / 详情 | `GET /devices`、`/devices/{id}`、`/sensor-data` |
| 告警中心 | `GET /alarms`、`/alarms/{id}` |
| AI 分析详情 | `POST /analysis/{alarm_id}`、`GET /analysis/{id}`、`/stream`、`/decision` |
| 维修工单 | `GET/POST /work-orders`、`/start`、`/complete` |
| 演示控制（可放调试页） | `/simulator/*` |
