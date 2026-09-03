<template>
  <div class="page">
    <section class="stats">
      <article class="stat">
        <div class="label">设备总数</div>
        <div class="value mono">{{ overview.device_total ?? '-' }}</div>
      </article>
      <article class="stat ok">
        <div class="label">正常运行</div>
        <div class="value mono">{{ overview.device_running ?? '-' }}</div>
      </article>
      <article class="stat warn">
        <div class="label">告警设备</div>
        <div class="value mono">{{ overview.device_warning ?? '-' }}</div>
      </article>
      <article class="stat danger">
        <div class="label">故障设备</div>
        <div class="value mono">{{ overview.device_fault ?? '-' }}</div>
      </article>
      <article class="stat steel">
        <div class="label">待处理报警</div>
        <div class="value mono">{{ overview.alarm_pending ?? '-' }}</div>
      </article>
    </section>

    <section class="grid-2">
      <div class="panel">
        <div class="panel-hd">
          <h2>近 7 日报警趋势</h2>
          <span class="muted refresh">自动刷新 {{ refreshedAt }}</span>
        </div>
        <div class="panel-bd chart-box">
          <v-chart class="chart" :option="trendOption" autoresize />
        </div>
      </div>
      <div class="panel">
        <div class="panel-hd">
          <h2>设备状态分布</h2>
        </div>
        <div class="panel-bd chart-box">
          <v-chart class="chart" :option="pieOption" autoresize />
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-hd">
        <h2>最近报警</h2>
        <router-link class="link" to="/alarms">查看全部</router-link>
      </div>
      <div class="panel-bd table-flush">
        <el-table :data="overview.recent_alarms || []" stripe empty-text="暂无报警" style="width: 100%">
          <el-table-column prop="device_code" label="设备" width="110" />
          <el-table-column label="类型" min-width="120">
            <template #default="{ row }">{{ labelAlarmType(row.alarm_type) }}</template>
          </el-table-column>
          <el-table-column label="等级" width="90">
            <template #default="{ row }">
              <span class="status-pill" :class="'status-' + row.alarm_level">
                {{ labelAlarmLevel(row.alarm_level) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <span class="status-pill" :class="'status-' + row.status">
                {{ labelAlarmStatus(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="实测/阈值" min-width="120">
            <template #default="{ row }">
              <span class="mono">{{ row.measured_value }} / {{ row.threshold_value }}</span>
            </template>
          </el-table-column>
          <el-table-column label="时间" min-width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" @click="$router.push(`/alarms/${row.id}`)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { api } from '@/api/client'
import {
  labelAlarmLevel,
  labelAlarmStatus,
  labelAlarmType,
  labelDeviceStatus,
} from '@/utils/labels'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const overview = ref({
  device_total: 0,
  device_running: 0,
  device_warning: 0,
  device_fault: 0,
  alarm_pending: 0,
  recent_alarms: [],
  alarm_trend: [],
  status_distribution: [],
})
const refreshedAt = ref('-')
let timer

const trendOption = computed(() => ({
  color: ['#409eff'],
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 16, top: 28, bottom: 28 },
  xAxis: {
    type: 'category',
    data: (overview.value.alarm_trend || []).map((x) => x.date.slice(5)),
    axisLine: { lineStyle: { color: '#e4e7ed' } },
    axisLabel: { color: '#909399' },
  },
  yAxis: {
    type: 'value',
    minInterval: 1,
    splitLine: { lineStyle: { color: '#f0f2f5' } },
    axisLabel: { color: '#909399' },
  },
  series: [
    {
      name: '报警数',
      type: 'line',
      smooth: true,
      areaStyle: { color: 'rgba(64,158,255,0.12)' },
      data: (overview.value.alarm_trend || []).map((x) => x.count),
    },
  ],
}))

const pieOption = computed(() => {
  const colorMap = {
    RUNNING: '#67c23a',
    WARNING: '#e6a23c',
    FAULT: '#f56c6c',
    STOPPED: '#909399',
  }
  const data = (overview.value.status_distribution || [])
    .filter((item) => Number(item.value) > 0)
    .map((item) => ({
      name: labelDeviceStatus(item.name),
      value: item.value,
      itemStyle: { color: colorMap[item.name] || '#909399' },
    }))
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#606266' } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        label: { color: '#303133' },
        data,
      },
    ],
  }
})

function formatTime(v) {
  if (!v) return '-'
  return new Date(v).toLocaleString()
}

async function load() {
  try {
    overview.value = await api.getOverview()
    refreshedAt.value = new Date().toLocaleTimeString()
  } catch {
    // keep last good snapshot on poll failure
  }
}

onMounted(async () => {
  await load()
  timer = setInterval(load, 8000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.stat {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px 16px;
  border-top: 3px solid var(--steel);
  min-width: 0;
}

.stat.ok {
  border-top-color: var(--ok);
}
.stat.warn {
  border-top-color: var(--amber);
}
.stat.danger {
  border-top-color: var(--danger);
}
.stat.steel {
  border-top-color: var(--steel-deep);
}

.label {
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 8px;
}

.value {
  font-size: 28px;
  font-weight: 600;
}

.grid-2 {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 16px;
  width: 100%;
}

.chart-box {
  height: 280px;
}

.chart {
  height: 100%;
  width: 100%;
}

.refresh {
  font-size: 12px;
}

.link {
  color: var(--steel);
  font-size: 13px;
  font-weight: 600;
}

@media (max-width: 1100px) {
  .stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .grid-2 {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .stats,
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
