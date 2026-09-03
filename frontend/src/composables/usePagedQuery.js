import { onUnmounted, ref, watch } from 'vue'
import { usePolling } from '@/composables/usePolling'

/**
 * 列表页：分页 + 状态筛选 + 关键词防抖搜索 + 轮询刷新
 * @param {(params: object) => Promise<{items,total,page,page_size}>} fetcher
 */
export function usePagedQuery(fetcher, { pageSize = 10, debounceMs = 350, pollMs = 8000 } = {}) {
  const items = ref([])
  const loading = ref(false)
  const status = ref()
  const keyword = ref('')
  const page = ref(1)
  const pageSizeRef = ref(pageSize)
  const total = ref(0)
  let searchTimer

  async function load() {
    loading.value = true
    try {
      const data = await fetcher({
        status: status.value || undefined,
        q: keyword.value.trim() || undefined,
        page: page.value,
        page_size: pageSizeRef.value,
      })
      items.value = data?.items || []
      total.value = data?.total || 0
      if (data?.page) page.value = data.page
      if (data?.page_size) pageSizeRef.value = data.page_size
    } finally {
      loading.value = false
    }
  }

  function resetAndLoad() {
    page.value = 1
    return load()
  }

  watch(keyword, () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(resetAndLoad, debounceMs)
  })

  usePolling(load, pollMs)

  onUnmounted(() => {
    clearTimeout(searchTimer)
  })

  return {
    items,
    loading,
    status,
    keyword,
    page,
    pageSize: pageSizeRef,
    total,
    load,
    onFilter: resetAndLoad,
    onSearch: resetAndLoad,
    onSizeChange: resetAndLoad,
  }
}
