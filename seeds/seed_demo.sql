-- Phase 1 demo seed data for fault_agent
-- Idempotent-ish: clears business tables then reloads (dev only)

BEGIN;

TRUNCATE TABLE
    fault_record,
    maintenance_work_order,
    agent_analysis,
    alarm,
    device_sensor_data,
    device_threshold,
    device
RESTART IDENTITY CASCADE;

-- ---------- devices ----------
INSERT INTO device (device_code, device_name, device_type, location, status) VALUES
('SMT-001', 'SMT贴片机-1号', 'SMT', '生产车间A-线体1', 'RUNNING'),
('SMT-002', 'SMT贴片机-2号', 'SMT', '生产车间A-线体2', 'RUNNING'),
('RF-001',  '回流焊设备-1号', 'REFLOW', '生产车间A-回流区', 'RUNNING'),
('RB-001',  '工业机器人-1号', 'ROBOT', '生产车间B-装配区', 'RUNNING'),
('ASM-001', '自动化装配设备-1号', 'ASSEMBLY', '生产车间B-总装区', 'RUNNING');

-- ---------- thresholds (by device_type) ----------
INSERT INTO device_threshold (device_type, metric_name, warning_max, alarm_max, unit) VALUES
-- SMT
('SMT', 'temperature', 85, 90, '℃'),
('SMT', 'pressure', 1.8, 2.2, 'bar'),
('SMT', 'vibration', 0.8, 1.2, 'mm/s'),
('SMT', 'power', 3.5, 4.5, 'kW'),
-- REFLOW
('REFLOW', 'temperature', 240, 260, '℃'),
('REFLOW', 'pressure', 2.0, 2.5, 'bar'),
('REFLOW', 'vibration', 0.6, 1.0, 'mm/s'),
('REFLOW', 'power', 8.0, 10.0, 'kW'),
-- ROBOT
('ROBOT', 'temperature', 70, 80, '℃'),
('ROBOT', 'pressure', 1.5, 2.0, 'bar'),
('ROBOT', 'vibration', 1.0, 1.5, 'mm/s'),
('ROBOT', 'power', 2.5, 3.5, 'kW'),
-- ASSEMBLY
('ASSEMBLY', 'temperature', 75, 85, '℃'),
('ASSEMBLY', 'pressure', 1.6, 2.0, 'bar'),
('ASSEMBLY', 'vibration', 0.9, 1.3, 'mm/s'),
('ASSEMBLY', 'power', 4.0, 5.0, 'kW');

-- ---------- historical fault records (for Agent later) ----------
INSERT INTO fault_record (
    device_id, alarm_id, work_order_id,
    fault_type, fault_description, root_cause, solution, fault_time
) VALUES
(
    (SELECT id FROM device WHERE device_code = 'SMT-001'),
    NULL, NULL,
    'TEMPERATURE_HIGH',
    '贴片机温度持续升高触发高温报警',
    '冷却系统异常',
    '检查冷却液循环；检查散热风扇',
    NOW() - INTERVAL '45 days'
),
(
    (SELECT id FROM device WHERE device_code = 'SMT-001'),
    NULL, NULL,
    'TEMPERATURE_HIGH',
    '贴片机再次出现高温异常',
    '冷却系统异常',
    '更换冷却液并清洗循环管路',
    NOW() - INTERVAL '20 days'
),
(
    (SELECT id FROM device WHERE device_code = 'SMT-001'),
    NULL, NULL,
    'TEMPERATURE_HIGH',
    '温度传感器读数异常偏高',
    '温度传感器漂移',
    '校准/更换温度传感器',
    NOW() - INTERVAL '10 days'
),
(
    (SELECT id FROM device WHERE device_code = 'RF-001'),
    NULL, NULL,
    'TEMPERATURE_HIGH',
    '回流焊炉温区超温',
    '加热模块功率失控',
    '检查加热模块与温控回路',
    NOW() - INTERVAL '30 days'
),
(
    (SELECT id FROM device WHERE device_code = 'RB-001'),
    NULL, NULL,
    'VIBRATION_HIGH',
    '机器人关节振动超限',
    '减速机磨损',
    '更换减速机并重新标定',
    NOW() - INTERVAL '15 days'
);

-- ---------- sample sensor points (recent normal baseline for SMT-001) ----------
INSERT INTO device_sensor_data (device_id, temperature, pressure, vibration, power, record_time)
SELECT
    d.id,
    72 + (gs.i % 5),
    1.10 + (gs.i % 3) * 0.02,
    0.30 + (gs.i % 4) * 0.02,
    2.20 + (gs.i % 3) * 0.05,
    NOW() - ((20 - gs.i) * INTERVAL '30 seconds')
FROM device d
CROSS JOIN generate_series(1, 20) AS gs(i)
WHERE d.device_code = 'SMT-001';

-- ---------- demo pending alarm with snapshot (ALARM-DEMO path) ----------
INSERT INTO alarm (
    device_id, alarm_type, alarm_level, alarm_message,
    metric_name, measured_value, threshold_value, snapshot_json, status
)
SELECT
    d.id,
    'TEMPERATURE_HIGH',
    'HIGH',
    'SMT-001 设备温度过高，实测 98℃，阈值 90℃',
    'temperature',
    98,
    90,
    '{"temperature": 98, "pressure": 1.2, "vibration": 0.4, "power": 3.1}'::jsonb,
    'PENDING'
FROM device d
WHERE d.device_code = 'SMT-001';

UPDATE device
SET status = 'WARNING', updated_at = NOW()
WHERE device_code = 'SMT-001';

COMMIT;

-- sanity checks
SELECT 'device' AS table_name, COUNT(*) AS cnt FROM device
UNION ALL SELECT 'device_threshold', COUNT(*) FROM device_threshold
UNION ALL SELECT 'fault_record', COUNT(*) FROM fault_record
UNION ALL SELECT 'device_sensor_data', COUNT(*) FROM device_sensor_data
UNION ALL SELECT 'alarm', COUNT(*) FROM alarm;
