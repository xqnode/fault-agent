<template>
  <div class="page">
    <div class="panel">
      <div class="panel-hd">
        <h2>设备列表</h2>
        <div class="toolbar">
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索编号 / 名称 / 类型 / 位置"
            style="width: 240px"
            @clear="onSearch"
            @keyup.enter="onSearch"
          >
            <template #prefix>
              <span class="search-ico">⌕</span>
            </template>
          </el-input>
          <el-select v-model="status" clearable placeholder="状态筛选" style="width: 140px" @change="onFilter">
            <el-option label="运行中" value="RUNNING" />
            <el-option label="告警中" value="WARNING" />
            <el-option label="故障" value="FAULT" />
            <el-option label="已停机" value="STOPPED" />
          </el-select>
          <el-button @click="onSearch">搜索</el-button>
        </div>
      </div>
      <div class="panel-bd table-flush">
        <el-table :data="devices" v-loading="loading" stripe empty-text="暂无设备">
          <el-table-column prop="device_code" label="设备编号" width="140" />
          <el-table-column prop="device_name" label="名称" min-width="160" />
          <el-table-column prop="device_type" label="类型" width="120" />
          <el-table-column prop="location" label="位置" min-width="160" />
          <el-table-column label="状态" width="130">
            <template #default="{ row }">
              <span class="status-pill" :class="'status-' + row.status">{{ labelDeviceStatus(row.status) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" @click="$router.push(`/devices/${row.id}`)">详情</el-button>
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
import { labelDeviceStatus } from '@/utils/labels'

const devices = ref([])
const loading = ref(false)
const status = ref()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
let timer
let searchTimer

async function load() {
  loading.value = true
  try {
    const data = await api.getDevices({
      status: status.value || undefined,
      q: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    devices.value = data.items || []
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
