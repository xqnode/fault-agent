<template>
  <div class="page">
    <div class="panel">
      <div class="panel-hd">
        <h2>告警中心</h2>
        <div class="toolbar">
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索设备 / 类型 / 消息"
            style="width: 240px"
            @clear="onSearch"
            @keyup.enter="onSearch"
          >
            <template #prefix>
              <span class="search-ico">⌕</span>
            </template>
          </el-input>
          <el-select v-model="status" clearable placeholder="状态" style="width: 140px" @change="onFilter">
            <el-option label="待处理" value="PENDING" />
            <el-option label="分析中" value="ANALYZING" />
            <el-option label="已分析" value="ANALYZED" />
            <el-option label="分析失败" value="FAILED" />
            <el-option label="已关闭" value="RESOLVED" />
          </el-select>
          <el-button @click="onSearch">搜索</el-button>
        </div>
      </div>
      <div class="panel-bd table-flush">
        <el-table :data="alarms" v-loading="loading" stripe empty-text="暂无报警">
          <el-table-column prop="device_code" label="设备" width="120" />
          <el-table-column label="类型" min-width="140">
            <template #default="{ row }">{{ labelAlarmType(row.alarm_type) }}</template>
          </el-table-column>
          <el-table-column label="等级" width="100">
            <template #default="{ row }">
              <span class="status-pill" :class="'status-' + row.alarm_level">{{ labelAlarmLevel(row.alarm_level) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <span class="status-pill" :class="'status-' + row.status">{{ labelAlarmStatus(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="实测/阈值" min-width="150">
            <template #default="{ row }">
              <span class="mono">{{ row.measured_value }} / {{ row.threshold_value }}</span>
            </template>
          </el-table-column>
          <el-table-column label="时间" min-width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" @click="$router.push(`/alarms/${row.id}`)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :total="total"
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            @current-change="load"
            @size-change="onSizeChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import { labelAlarmLevel, labelAlarmStatus, labelAlarmType } from '@/utils/labels'

const alarms = ref([])
const loading = ref(false)
const status = ref()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
let timer
let searchTimer

function formatTime(v) {
  return v ? new Date(v).toLocaleString() : '-'
}

async function load() {
  loading.value = true
  try {
    const data = await api.getAlarms({
      status: status.value || undefined,
      q: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    alarms.value = data.items || []
    total.value = data.total || 0
    page.value = data.page || page.value
    pageSize.value = data.page_size || pageSize.value
  } finally {
    loading.value = false
  }
}

function onFilter() {
  page.value = 1
  load()
}

function onSearch() {
  page.value = 1
  load()
}

function onSizeChange() {
  page.value = 1
  load()
}

watch(keyword, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(onSearch, 350)
})

onMounted(async () => {
  await load()
  timer = setInterval(load, 8000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  clearTimeout(searchTimer)
})
</script>
