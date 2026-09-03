/** 统一提取后端 / 前端错误文案 */

export function getErrorMessage(err, fallback = '操作失败') {
  if (!err) return fallback
  if (typeof err === 'string') return err
  return err.response?.data?.detail || err.message || fallback
}
