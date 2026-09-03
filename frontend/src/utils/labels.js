export const DEVICE_STATUS_LABEL = {
  RUNNING: '运行中',
  WARNING: '告警中',
  FAULT: '故障',
  STOPPED: '已停机',
}

export const ALARM_STATUS_LABEL = {
  PENDING: '待处理',
  ANALYZING: '分析中',
  ANALYZED: '已分析',
  FAILED: '分析失败',
  RESOLVED: '已关闭',
}

export const ALARM_LEVEL_LABEL = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  CRITICAL: '紧急',
}

export const ALARM_TYPE_LABEL = {
  TEMPERATURE_HIGH: '温度过高',
  PRESSURE_HIGH: '压力过高',
  VIBRATION_HIGH: '振动过高',
  POWER_HIGH: '功率过高',
}

export const METRIC_LABEL = {
  temperature: '温度',
  pressure: '压力',
  vibration: '振动',
  power: '功率',
}

export const METRIC_UNIT = {
  temperature: '℃',
  pressure: 'MPa',
  vibration: 'mm/s',
  power: 'kW',
}

export const ROLE_LABEL = {
  ADMIN: '管理员',
  ENGINEER: '运维工程师',
}

export const DEVICE_STATUS_OPTIONS = Object.entries(DEVICE_STATUS_LABEL).map(([value, label]) => ({
  value,
  label,
}))

export const ALARM_STATUS_OPTIONS = Object.entries(ALARM_STATUS_LABEL).map(([value, label]) => ({
  value,
  label,
}))

function pickLabel(map, v, fallback = '-') {
  if (v == null || v === '') return fallback
  return map[v] || v || fallback
}

export function labelDeviceStatus(v) {
  return pickLabel(DEVICE_STATUS_LABEL, v)
}

export function labelAlarmStatus(v) {
  return pickLabel(ALARM_STATUS_LABEL, v)
}

export function labelAlarmLevel(v) {
  return pickLabel(ALARM_LEVEL_LABEL, v)
}

export function labelAlarmType(v) {
  return pickLabel(ALARM_TYPE_LABEL, v)
}

export function labelRole(v) {
  return pickLabel(ROLE_LABEL, v)
}

export function labelMetric(v) {
  return pickLabel(METRIC_LABEL, v)
}

export function metricUnit(v) {
  return METRIC_UNIT[v] || ''
}
