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
            <el-option v-for="opt in DEVICE_STATUS_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-button @click="onSearch">搜索</el-button>
        </div>
      </div>
      <div class="panel-bd table-flush">
        <el-table :data="items" v-loading="loading" stripe empty-text="暂无设备">
          <el-table-column prop="device_code" label="设备编号" width="140" />
          <el-table-column prop="device_name" label="名称" min-width="160" />
          <el-table-column prop="device_type" label="类型" width="120" />
          <el-table-column prop="location" label="位置" min-width="160" />
          <el-table-column label="状态" width="130">
            <template #default="{ row }">
              <StatusPill :value="row.status" type="device" />
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
import { api } from '@/api/client'
import StatusPill from '@/components/StatusPill.vue'
import { usePagedQuery } from '@/composables/usePagedQuery'
import { DEVICE_STATUS_OPTIONS } from '@/utils/labels'

const {
  items,
  loading,
  status,
  keyword,
  page,
  pageSize,
  total,
  load,
  onFilter,
  onSearch,
  onSizeChange,
} = usePagedQuery((params) => api.getDevices(params))
</script>
