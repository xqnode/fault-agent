/** 时间格式化 */

export function formatTime(v, fallback = '-') {
  if (!v) return fallback
  const d = v instanceof Date ? v : new Date(v)
  if (Number.isNaN(d.getTime())) return fallback
  return d.toLocaleString()
}

export function formatClockTime(v, fallback = '-') {
  if (!v) return fallback
  const d = v instanceof Date ? v : new Date(v)
  if (Number.isNaN(d.getTime())) return fallback
  return d.toLocaleTimeString()
}
