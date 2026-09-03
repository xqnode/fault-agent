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
            <el-option v-for="opt in ALARM_STATUS_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-button @click="onSearch">搜索</el-button>
        </div>
      </div>
      <div class="panel-bd table-flush">
        <el-table :data="items" v-loading="loading" stripe empty-text="暂无报警">
          <el-table-column prop="device_code" label="设备" width="120" />
          <el-table-column label="类型" min-width="140">
            <template #default="{ row }">{{ labelAlarmType(row.alarm_type) }}</template>
          </el-table-column>
          <el-table-column label="等级" width="100">
            <template #default="{ row }">
              <StatusPill :value="row.alarm_level" type="level" />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <StatusPill :value="row.status" type="alarm" />
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
import { api } from '@/api/client'
import StatusPill from '@/components/StatusPill.vue'
import { usePagedQuery } from '@/composables/usePagedQuery'
import { formatTime } from '@/utils/datetime'
import { ALARM_STATUS_OPTIONS, labelAlarmType } from '@/utils/labels'

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
} = usePagedQuery((params) => api.getAlarms(params))
</script>
