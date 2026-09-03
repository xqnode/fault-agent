<template>
  <div class="page" v-loading="loading">
    <div class="panel" v-if="device">
      <div class="panel-hd">
        <div>
          <h2>{{ device.device_code }} · {{ device.device_name }}</h2>
          <div class="muted">{{ device.location }} · {{ device.device_type }}</div>
        </div>
        <span class="status-pill" :class="'status-' + device.status">{{ labelDeviceStatus(device.status) }}</span>
      </div>
      <div class="panel-bd meta">
        <div><span class="muted">设备 ID</span><div class="mono">{{ device.id }}</div></div>
        <div><span class="muted">更新时间</span><div>{{ formatTime(device.updated_at) }}</div></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-hd"><h2>阈值配置</h2></div>
        <div class="panel-bd">
          <el-table :data="device?.thresholds || []" size="small" empty-text="无阈值">
            <el-table-column prop="metric_name" label="指标" />
            <el-table-column prop="warning_max" label="预警" />
            <el-table-column prop="alarm_max" label="报警" />
            <el-table-column prop="unit" label="单位" width="80" />
          </el-table>
        </div>
      </div>
      <div class="panel">
        <div class="panel-hd"><h2>近时序曲线</h2></div>
        <div class="panel-bd chart-box">
          <v-chart class="chart" :option="chartOption" autoresize />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { api } from '@/api/client'
import { labelDeviceStatus } from '@/utils/labels'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const device = ref(null)
const points = ref([])
const loading = ref(false)
let timer

const chartOption = computed(() => ({
  color: ['#c47b16', '#2f5d8a', '#2f7d4a', '#7a5af8'],
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { left: 45, right: 20, top: 40, bottom: 30 },
  xAxis: {
    type: 'category',
    data: points.value.map((p) => new Date(p.record_time).toLocaleTimeString()),
  },
  yAxis: { type: 'value', scale: true },
  series: [
    { name: '温度', type: 'line', showSymbol: false, data: points.value.map((p) => p.temperature) },
    { name: '功率', type: 'line', showSymbol: false, data: points.value.map((p) => p.power) },
    { name: '压力', type: 'line', showSymbol: false, data: points.value.map((p) => p.pressure) },
    { name: '振动', type: 'line', showSymbol: false, data: points.value.map((p) => p.vibration) },
  ],
}))

function formatTime(v) {
  return v ? new Date(v).toLocaleString() : '-'
}

async function load() {
  loading.value = true
  try {
    const id = route.params.id
    device.value = await api.getDevice(id)
    const sensor = await api.getSensorData(id, { limit: 60 })
    points.value = sensor.points || []
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, load)

onMounted(async () => {
  await load()
  timer = setInterval(load, 8000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.grid-2 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
  gap: 16px;
  width: 100%;
}

.chart-box {
  height: 320px;
}

.chart {
  width: 100%;
  height: 100%;
}

@media (max-width: 1000px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
