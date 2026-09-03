/** 数值展示 */

export function formatNumber(v, { digits = 2, fallback = '-' } = {}) {
  if (v == null || v === '') return fallback
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  // 去掉多余尾随 0，但保留合理精度
  return Number(n.toFixed(digits)).toString()
}

export function formatPair(a, b, options) {
  return `${formatNumber(a, options)} / ${formatNumber(b, options)}`
}
