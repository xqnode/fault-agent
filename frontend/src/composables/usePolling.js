import { onMounted, onUnmounted } from 'vue'

const DEFAULT_INTERVAL = 8000

/**
 * 页面轮询：挂载后立即执行，并按间隔重复；卸载时清理。
 */
export function usePolling(task, intervalMs = DEFAULT_INTERVAL, { immediate = true } = {}) {
  let timer

  async function run() {
    try {
      await task()
    } catch {
      // 轮询任务自行处理业务异常；此处吞掉避免打断定时器
    }
  }

  onMounted(async () => {
    if (immediate) await run()
    timer = setInterval(run, intervalMs)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { refresh: run }
}
