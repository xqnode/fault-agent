-- =============================================================================
-- fault_agent · 业务库 DDL（PostgreSQL 17）
-- 规范要点：
--   1) 主键使用 BIGINT GENERATED ALWAYS AS IDENTITY（SQL 标准，替代 BIGSERIAL）
--   2) 时间一律 TIMESTAMPTZ + CURRENT_TIMESTAMP（禁止无时区 timestamp）
--   3) 结构化扩展字段使用 JSONB（禁止 json）
--   4) 约束全部具名（PK / UK / FK / CK），外键显式 ON DELETE
--   5) 表/字段中文注释使用 COMMENT ON（PG 标准方式）
--   6) updated_at 由触发器维护，避免应用层漏更新
--   7) 状态类字段用 VARCHAR + CHECK（比 PG ENUM 更利于演进）
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- 公共：updated_at 触发器函数 ----------
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION trg_set_updated_at() IS '通用触发器：行更新时自动刷新 updated_at';

-- 开发环境可重复执行：按依赖逆序清理后重建
DROP TABLE IF EXISTS fault_record CASCADE;
DROP TABLE IF EXISTS maintenance_work_order CASCADE;
DROP TABLE IF EXISTS agent_analysis CASCADE;
DROP TABLE IF EXISTS alarm CASCADE;
DROP TABLE IF EXISTS device_sensor_data CASCADE;
DROP TABLE IF EXISTS device_threshold CASCADE;
DROP TABLE IF EXISTS device CASCADE;
DROP TABLE IF EXISTS app_user CASCADE;

-- =============================================================================
-- 设备主数据
-- =============================================================================
CREATE TABLE device (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    device_code     VARCHAR(64)  NOT NULL,
    device_name     VARCHAR(128) NOT NULL,
    device_type     VARCHAR(32)  NOT NULL,
    location        VARCHAR(128),
    status          VARCHAR(32)  NOT NULL DEFAULT 'RUNNING',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_device PRIMARY KEY (id),
    CONSTRAINT uk_device_code UNIQUE (device_code),
    CONSTRAINT ck_device_type CHECK (
        device_type IN ('SMT', 'REFLOW', 'ROBOT', 'ASSEMBLY')
    ),
    CONSTRAINT ck_device_status CHECK (
        status IN ('RUNNING', 'WARNING', 'FAULT', 'STOPPED')
    )
);

CREATE INDEX idx_device_type ON device (device_type);
CREATE INDEX idx_device_status ON device (status);

CREATE TRIGGER trg_device_set_updated_at
BEFORE UPDATE ON device
FOR EACH ROW
EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE device IS '设备主数据表：工厂产线设备档案与当前运行状态';
COMMENT ON COLUMN device.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN device.device_code IS '设备业务编号，全局唯一，如 SMT-001';
COMMENT ON COLUMN device.device_name IS '设备名称';
COMMENT ON COLUMN device.device_type IS '设备类型：SMT / REFLOW / ROBOT / ASSEMBLY';
COMMENT ON COLUMN device.location IS '设备安装位置/产线区域';
COMMENT ON COLUMN device.status IS '设备状态：RUNNING/WARNING/FAULT/STOPPED';
COMMENT ON COLUMN device.created_at IS '创建时间（带时区）';
COMMENT ON COLUMN device.updated_at IS '最后更新时间（触发器自动维护）';

-- =============================================================================
-- 设备/机型阈值
-- =============================================================================
CREATE TABLE device_threshold (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    device_type     VARCHAR(32),
    device_id       BIGINT,
    metric_name     VARCHAR(64) NOT NULL,
    warning_max     NUMERIC(12, 4),
    alarm_max       NUMERIC(12, 4) NOT NULL,
    unit            VARCHAR(16),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_device_threshold PRIMARY KEY (id),
    CONSTRAINT fk_threshold_device
        FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE,
    CONSTRAINT ck_threshold_scope CHECK (
        device_type IS NOT NULL OR device_id IS NOT NULL
    ),
    CONSTRAINT ck_threshold_device_type CHECK (
        device_type IS NULL
        OR device_type IN ('SMT', 'REFLOW', 'ROBOT', 'ASSEMBLY')
    ),
    CONSTRAINT ck_threshold_metric CHECK (
        metric_name IN ('temperature', 'pressure', 'vibration', 'power')
    ),
    CONSTRAINT ck_threshold_bounds CHECK (
        warning_max IS NULL OR warning_max <= alarm_max
    )
);

-- 按机型配置：同一机型同一指标唯一
CREATE UNIQUE INDEX uk_threshold_type_metric
    ON device_threshold (device_type, metric_name)
    WHERE device_type IS NOT NULL AND device_id IS NULL;

-- 按单设备覆盖：同一设备同一指标唯一
CREATE UNIQUE INDEX uk_threshold_device_metric
    ON device_threshold (device_id, metric_name)
    WHERE device_id IS NOT NULL;

COMMENT ON TABLE device_threshold IS '报警阈值配置表：优先按机型，可按单设备覆盖';
COMMENT ON COLUMN device_threshold.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN device_threshold.device_type IS '机型维度阈值（与 device_id 二选一优先）';
COMMENT ON COLUMN device_threshold.device_id IS '单设备覆盖阈值，可空';
COMMENT ON COLUMN device_threshold.metric_name IS '监测指标：temperature/pressure/vibration/power';
COMMENT ON COLUMN device_threshold.warning_max IS '预警上限';
COMMENT ON COLUMN device_threshold.alarm_max IS '报警上限';
COMMENT ON COLUMN device_threshold.unit IS '计量单位，如 ℃、bar、kW';
COMMENT ON COLUMN device_threshold.created_at IS '创建时间（带时区）';

-- =============================================================================
-- 设备传感器时序数据
-- =============================================================================
CREATE TABLE device_sensor_data (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    device_id       BIGINT NOT NULL,
    temperature     NUMERIC(12, 4),
    pressure        NUMERIC(12, 4),
    vibration       NUMERIC(12, 4),
    power           NUMERIC(12, 4),
    record_time     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_device_sensor_data PRIMARY KEY (id),
    CONSTRAINT fk_sensor_device
        FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE
);

CREATE INDEX idx_sensor_device_time
    ON device_sensor_data (device_id, record_time DESC);

COMMENT ON TABLE device_sensor_data IS '设备传感器采样数据表（时序，建议定期清理）';
COMMENT ON COLUMN device_sensor_data.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN device_sensor_data.device_id IS '所属设备 ID';
COMMENT ON COLUMN device_sensor_data.temperature IS '温度采样值';
COMMENT ON COLUMN device_sensor_data.pressure IS '压力采样值';
COMMENT ON COLUMN device_sensor_data.vibration IS '振动采样值';
COMMENT ON COLUMN device_sensor_data.power IS '功率采样值';
COMMENT ON COLUMN device_sensor_data.record_time IS '采样时间（带时区）';

-- =============================================================================
-- 报警
-- =============================================================================
CREATE TABLE alarm (
    id               BIGINT GENERATED ALWAYS AS IDENTITY,
    device_id        BIGINT NOT NULL,
    alarm_type       VARCHAR(64) NOT NULL,
    alarm_level      VARCHAR(16) NOT NULL,
    alarm_message    TEXT,
    metric_name      VARCHAR(64) NOT NULL,
    measured_value   NUMERIC(12, 4) NOT NULL,
    threshold_value  NUMERIC(12, 4) NOT NULL,
    snapshot_json    JSONB NOT NULL,
    status           VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at      TIMESTAMPTZ,

    CONSTRAINT pk_alarm PRIMARY KEY (id),
    CONSTRAINT fk_alarm_device
        FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE,
    CONSTRAINT ck_alarm_level CHECK (
        alarm_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    ),
    CONSTRAINT ck_alarm_status CHECK (
        status IN ('PENDING', 'ANALYZING', 'ANALYZED', 'FAILED', 'RESOLVED')
    ),
    CONSTRAINT ck_alarm_metric CHECK (
        metric_name IN ('temperature', 'pressure', 'vibration', 'power')
    ),
    CONSTRAINT ck_alarm_resolved_pair CHECK (
        (status = 'RESOLVED' AND resolved_at IS NOT NULL)
        OR (status <> 'RESOLVED' AND resolved_at IS NULL)
    )
);

CREATE INDEX idx_alarm_device_created
    ON alarm (device_id, created_at DESC);
CREATE INDEX idx_alarm_status ON alarm (status);
CREATE INDEX idx_alarm_type ON alarm (alarm_type);
CREATE INDEX idx_alarm_snapshot_gin ON alarm USING GIN (snapshot_json);

COMMENT ON TABLE alarm IS '设备报警表：含触发快照，支撑追溯与 AI 分析入口';
COMMENT ON COLUMN alarm.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN alarm.device_id IS '报警所属设备 ID';
COMMENT ON COLUMN alarm.alarm_type IS '报警类型编码，如 TEMPERATURE_HIGH';
COMMENT ON COLUMN alarm.alarm_level IS '报警等级：LOW/MEDIUM/HIGH/CRITICAL';
COMMENT ON COLUMN alarm.alarm_message IS '报警可读描述';
COMMENT ON COLUMN alarm.metric_name IS '触发指标名称';
COMMENT ON COLUMN alarm.measured_value IS '触发时刻实测值';
COMMENT ON COLUMN alarm.threshold_value IS '触发时刻使用的阈值';
COMMENT ON COLUMN alarm.snapshot_json IS '触发时刻多指标快照（JSONB）';
COMMENT ON COLUMN alarm.status IS '报警状态：PENDING/ANALYZING/ANALYZED/FAILED/RESOLVED';
COMMENT ON COLUMN alarm.created_at IS '报警产生时间';
COMMENT ON COLUMN alarm.resolved_at IS '报警关闭时间；仅 RESOLVED 时非空';

-- =============================================================================
-- AI 分析结果
-- =============================================================================
CREATE TABLE agent_analysis (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY,
    alarm_id                BIGINT NOT NULL,
    status                  VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
    analysis_result         JSONB,
    execution_trace         JSONB,
    evidence_list           JSONB,
    engineer_decision       VARCHAR(32),
    selected_cause          TEXT,
    edit_recommendations    JSONB,
    feedback_note           TEXT,
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_agent_analysis PRIMARY KEY (id),
    CONSTRAINT fk_analysis_alarm
        FOREIGN KEY (alarm_id) REFERENCES alarm (id) ON DELETE CASCADE,
    CONSTRAINT ck_analysis_status CHECK (
        status IN ('RUNNING', 'SUCCEEDED', 'FAILED')
    ),
    CONSTRAINT ck_engineer_decision CHECK (
        engineer_decision IS NULL
        OR engineer_decision IN ('APPROVED', 'REJECTED', 'EDITED')
    )
);

-- 同一报警同一时刻仅允许一条 RUNNING 分析（幂等）
CREATE UNIQUE INDEX uk_agent_analysis_alarm_running
    ON agent_analysis (alarm_id)
    WHERE status = 'RUNNING';

CREATE INDEX idx_analysis_alarm ON agent_analysis (alarm_id);
CREATE INDEX idx_analysis_status ON agent_analysis (status);

CREATE TRIGGER trg_agent_analysis_set_updated_at
BEFORE UPDATE ON agent_analysis
FOR EACH ROW
EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE agent_analysis IS 'AI 故障分析任务与结果表（含 HITL 确认字段）';
COMMENT ON COLUMN agent_analysis.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN agent_analysis.alarm_id IS '关联报警 ID';
COMMENT ON COLUMN agent_analysis.status IS '分析状态：RUNNING/SUCCEEDED/FAILED';
COMMENT ON COLUMN agent_analysis.analysis_result IS '结构化分析报告 JSON';
COMMENT ON COLUMN agent_analysis.execution_trace IS 'Agent 节点/工具执行轨迹 JSON';
COMMENT ON COLUMN agent_analysis.evidence_list IS '可追溯证据列表 JSON';
COMMENT ON COLUMN agent_analysis.engineer_decision IS '工程师决策：APPROVED/REJECTED/EDITED';
COMMENT ON COLUMN agent_analysis.selected_cause IS '工程师确认或修改后的根因';
COMMENT ON COLUMN agent_analysis.edit_recommendations IS '工程师修改后的建议列表 JSON';
COMMENT ON COLUMN agent_analysis.feedback_note IS '工程师备注';
COMMENT ON COLUMN agent_analysis.error_message IS '分析失败原因';
COMMENT ON COLUMN agent_analysis.created_at IS '创建时间';
COMMENT ON COLUMN agent_analysis.updated_at IS '最后更新时间（触发器自动维护）';

-- =============================================================================
-- 维修工单
-- =============================================================================
CREATE TABLE maintenance_work_order (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY,
    work_order_no        VARCHAR(64) NOT NULL,
    device_id            BIGINT NOT NULL,
    alarm_id             BIGINT NOT NULL,
    analysis_id          BIGINT NOT NULL,
    fault_description    TEXT,
    priority             VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    status               VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    suggestion           TEXT,
    actual_root_cause    TEXT,
    actual_solution      TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at         TIMESTAMPTZ,

    CONSTRAINT pk_maintenance_work_order PRIMARY KEY (id),
    CONSTRAINT uk_work_order_no UNIQUE (work_order_no),
    CONSTRAINT fk_wo_device
        FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE RESTRICT,
    CONSTRAINT fk_wo_alarm
        FOREIGN KEY (alarm_id) REFERENCES alarm (id) ON DELETE RESTRICT,
    CONSTRAINT fk_wo_analysis
        FOREIGN KEY (analysis_id) REFERENCES agent_analysis (id) ON DELETE RESTRICT,
    CONSTRAINT ck_wo_status CHECK (
        status IN ('DRAFT', 'PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED')
    ),
    CONSTRAINT ck_wo_priority CHECK (
        priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    ),
    CONSTRAINT ck_wo_complete_fields CHECK (
        (
            status = 'COMPLETED'
            AND actual_root_cause IS NOT NULL
            AND actual_solution IS NOT NULL
            AND completed_at IS NOT NULL
        )
        OR (status <> 'COMPLETED')
    )
);

CREATE INDEX idx_wo_device ON maintenance_work_order (device_id);
CREATE INDEX idx_wo_alarm ON maintenance_work_order (alarm_id);
CREATE INDEX idx_wo_status ON maintenance_work_order (status);

-- 同一分析仅允许一条非取消工单
CREATE UNIQUE INDEX uk_wo_analysis_active
    ON maintenance_work_order (analysis_id)
    WHERE status <> 'CANCELLED';

COMMENT ON TABLE maintenance_work_order IS '维修工单表：由已确认分析派生，结单回写故障案例';
COMMENT ON COLUMN maintenance_work_order.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN maintenance_work_order.work_order_no IS '工单业务编号，全局唯一';
COMMENT ON COLUMN maintenance_work_order.device_id IS '维修设备 ID';
COMMENT ON COLUMN maintenance_work_order.alarm_id IS '关联报警 ID';
COMMENT ON COLUMN maintenance_work_order.analysis_id IS '关联 AI 分析 ID';
COMMENT ON COLUMN maintenance_work_order.fault_description IS '故障描述';
COMMENT ON COLUMN maintenance_work_order.priority IS '优先级：LOW/MEDIUM/HIGH/CRITICAL';
COMMENT ON COLUMN maintenance_work_order.status IS '工单状态：DRAFT/PENDING/PROCESSING/COMPLETED/CANCELLED';
COMMENT ON COLUMN maintenance_work_order.suggestion IS '维修建议（AI 或工程师确认后）';
COMMENT ON COLUMN maintenance_work_order.actual_root_cause IS '结单实际根因（COMPLETED 必填）';
COMMENT ON COLUMN maintenance_work_order.actual_solution IS '结单实际措施（COMPLETED 必填）';
COMMENT ON COLUMN maintenance_work_order.created_at IS '创建时间';
COMMENT ON COLUMN maintenance_work_order.completed_at IS '结单完成时间';

-- =============================================================================
-- 历史故障案例
-- =============================================================================
CREATE TABLE fault_record (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY,
    device_id            BIGINT NOT NULL,
    alarm_id             BIGINT,
    work_order_id        BIGINT,
    fault_type           VARCHAR(64) NOT NULL,
    fault_description    TEXT,
    root_cause           TEXT,
    solution             TEXT,
    fault_time           TIMESTAMPTZ NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_fault_record PRIMARY KEY (id),
    CONSTRAINT fk_fault_device
        FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE RESTRICT,
    CONSTRAINT fk_fault_alarm
        FOREIGN KEY (alarm_id) REFERENCES alarm (id) ON DELETE SET NULL,
    CONSTRAINT fk_fault_work_order
        FOREIGN KEY (work_order_id) REFERENCES maintenance_work_order (id) ON DELETE SET NULL
);

CREATE INDEX idx_fault_device_type_time
    ON fault_record (device_id, fault_type, fault_time DESC);

COMMENT ON TABLE fault_record IS '历史故障案例表：种子预置 + 工单结单沉淀，供后续检索';
COMMENT ON COLUMN fault_record.id IS '主键 ID（系统生成）';
COMMENT ON COLUMN fault_record.device_id IS '设备 ID';
COMMENT ON COLUMN fault_record.alarm_id IS '关联报警 ID（种子数据可空）';
COMMENT ON COLUMN fault_record.work_order_id IS '关联工单 ID（种子数据可空）';
COMMENT ON COLUMN fault_record.fault_type IS '故障类型编码';
COMMENT ON COLUMN fault_record.fault_description IS '故障描述';
COMMENT ON COLUMN fault_record.root_cause IS '根因';
COMMENT ON COLUMN fault_record.solution IS '解决方案/措施';
COMMENT ON COLUMN fault_record.fault_time IS '故障发生时间';
COMMENT ON COLUMN fault_record.created_at IS '记录创建时间';

-- =============================================================================
-- 系统用户（轻量角色）
-- =============================================================================
CREATE TABLE app_user (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    username        VARCHAR(64)  NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    nickname        VARCHAR(64)  NOT NULL,
    role            VARCHAR(32)  NOT NULL DEFAULT 'ENGINEER',
    status          VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_app_user PRIMARY KEY (id),
    CONSTRAINT uk_app_user_username UNIQUE (username),
    CONSTRAINT ck_app_user_role CHECK (role IN ('ADMIN', 'ENGINEER')),
    CONSTRAINT ck_app_user_status CHECK (status IN ('ACTIVE', 'DISABLED'))
);

CREATE INDEX idx_app_user_role ON app_user (role);
CREATE INDEX idx_app_user_status ON app_user (status);

CREATE TRIGGER trg_app_user_set_updated_at
BEFORE UPDATE ON app_user
FOR EACH ROW
EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE app_user IS '系统用户表：登录账号与轻量角色（ADMIN/ENGINEER）';
COMMENT ON COLUMN app_user.username IS '登录用户名，唯一';
COMMENT ON COLUMN app_user.password_hash IS '口令摘要：pbkdf2_sha256$iter$salt$hex';
COMMENT ON COLUMN app_user.nickname IS '显示昵称';
COMMENT ON COLUMN app_user.role IS '角色：ADMIN 全量权限；ENGINEER 运维读写';
COMMENT ON COLUMN app_user.status IS '状态：ACTIVE / DISABLED';
