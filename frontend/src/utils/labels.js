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

export function labelDeviceStatus(v) {
  return DEVICE_STATUS_LABEL[v] || v || '-'
}

export function labelAlarmStatus(v) {
  return ALARM_STATUS_LABEL[v] || v || '-'
}

export function labelAlarmLevel(v) {
  return ALARM_LEVEL_LABEL[v] || v || '-'
}

export function labelAlarmType(v) {
  return ALARM_TYPE_LABEL[v] || v || '-'
}
