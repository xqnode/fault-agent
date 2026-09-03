<template>
  <div class="page" v-loading="loading">
    <template v-if="alarm">
      <div class="panel hero">
        <div class="panel-hd hero-hd">
          <div class="hero-left">
            <el-button link type="primary" @click="$router.push('/alarms')">← 返回告警中心</el-button>
            <h2>{{ labelAlarmType(alarm.alarm_type) }}</h2>
            <p class="hero-sub">{{ alarm.alarm_message || '暂无报警描述' }}</p>
          </div>
          <div class="hero-right">
            <StatusPill :value="alarm.status" type="alarm" />
            <StatusPill :value="alarm.alarm_level" type="level" />
          </div>
        </div>

        <div class="panel-bd">
          <div class="measure-row">
            <div class="measure-card danger">
              <div class="measure-label">实测值</div>
              <div class="measure-value mono">
                {{ formatNumber(alarm.measured_value) }}
                <span class="unit">{{ metricUnit(alarm.metric_name) }}</span>
              </div>
            </div>
            <div class="measure-vs">/</div>
            <div class="measure-card">
              <div class="measure-label">阈值</div>
              <div class="measure-value mono">
                {{ formatNumber(alarm.threshold_value) }}
                <span class="unit">{{ metricUnit(alarm.metric_name) }}</span>
              </div>
            </div>
            <div class="measure-delta" :class="{ up: overThreshold }">
              <div class="measure-label">偏差</div>
              <div class="measure-value mono">{{ deltaText }}</div>
            </div>
          </div>

          <div class="info-grid">
            <div class="info-item">
              <div class="muted">设备</div>
              <div>
                <router-link v-if="alarm.device_id" class="link" :to="`/devices/${alarm.device_id}`">
                  {{ alarm.device_code || `设备 #${alarm.device_id}` }}
                </router-link>
                <span v-else>-</span>
              </div>
            </div>
            <div class="info-item">
              <div class="muted">指标</div>
              <div>{{ labelMetric(alarm.metric_name) }} <span class="muted mono">({{ alarm.metric_name }})</span></div>
            </div>
            <div class="info-item">
              <div class="muted">报警编号</div>
              <div class="mono">#{{ alarm.id }}</div>
            </div>
            <div class="info-item">
              <div class="muted">产生时间</div>
              <div>{{ formatTime(alarm.created_at) }}</div>
            </div>
            <div class="info-item">
              <div class="muted">关闭时间</div>
              <div>{{ alarm.resolved_at ? formatTime(alarm.resolved_at) : '未关闭' }}</div>
            </div>
            <div class="info-item">
              <div class="muted">当前状态</div>
              <div><StatusPill :value="alarm.status" type="alarm" /></div>
            </div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-hd">
          <h2>触发快照</h2>
          <span class="muted">报警触发瞬间的传感器读数</span>
        </div>
        <div class="panel-bd">
          <div v-if="snapshotItems.length" class="snap-grid">
            <div
              v-for="item in snapshotItems"
              :key="item.key"
              class="snap-card"
              :class="{ highlight: item.key === alarm.metric_name }"
            >
              <div class="snap-name">{{ item.label }}</div>
              <div class="snap-value mono">
                {{ item.display }}
                <span class="unit">{{ item.unit }}</span>
              </div>
              <div class="snap-key muted mono">{{ item.key }}</div>
            </div>
          </div>
          <div v-else class="empty muted">暂无快照数据</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import StatusPill from '@/components/StatusPill.vue'
import { formatTime } from '@/utils/datetime'
import { labelAlarmType, labelMetric, metricUnit } from '@/utils/labels'
import { formatNumber } from '@/utils/number'

const route = useRoute()
const alarm = ref(null)
const loading = ref(false)

const overThreshold = computed(() => {
  if (!alarm.value) return false
  return Number(alarm.value.measured_value) > Number(alarm.value.threshold_value)
})

const deltaText = computed(() => {
  if (!alarm.value) return '-'
  const delta = Number(alarm.value.measured_value) - Number(alarm.value.threshold_value)
  if (Number.isNaN(delta)) return '-'
  const sign = delta > 0 ? '+' : ''
  return `${sign}${formatNumber(delta)}${metricUnit(alarm.value.metric_name)}`
})

const snapshotItems = computed(() => {
  const snap = alarm.value?.snapshot_json
  if (!snap || typeof snap !== 'object') return []
  return Object.entries(snap).map(([key, value]) => ({
    key,
    label: labelMetric(key),
    unit: metricUnit(key),
    display: formatNumber(value),
  }))
})

async function load() {
  loading.value = true
  try {
    alarm.value = await api.getAlarm(route.params.id)
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.hero-hd {
  align-items: flex-start;
}

.hero-left h2 {
  margin: 6px 0 6px;
  font-size: 20px;
}

.hero-sub {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
  max-width: 720px;
}

.hero-right {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.measure-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr 1fr;
  gap: 12px;
  align-items: stretch;
  margin-bottom: 18px;
}

.measure-card,
.measure-delta {
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafbfc;
}

.measure-card.danger {
  background: #fff5f5;
  border-color: #fde2e2;
}

.measure-delta.up {
  background: #fdf6ec;
  border-color: #faecd8;
}

.measure-vs {
  display: grid;
  place-items: center;
  color: #c0c4cc;
  font-size: 22px;
  font-weight: 600;
}

.measure-label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.measure-value {
  font-size: 28px;
  font-weight: 650;
  color: #303133;
  line-height: 1.2;
}

.unit {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #909399;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.info-item {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

.info-item .muted {
  margin-bottom: 6px;
  font-size: 12px;
}

.link {
  color: var(--el-color-primary);
  font-weight: 600;
}

.snap-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.snap-card {
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafbfc;
}

.snap-card.highlight {
  border-color: #f56c6c;
  background: #fff5f5;
  box-shadow: inset 3px 0 0 #f56c6c;
}

.snap-name {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.snap-value {
  font-size: 22px;
  font-weight: 650;
  color: #303133;
}

.snap-key {
  margin-top: 8px;
  font-size: 12px;
}

.empty {
  padding: 24px;
  text-align: center;
}

@media (max-width: 1000px) {
  .measure-row {
    grid-template-columns: 1fr;
  }

  .measure-vs {
    display: none;
  }

  .info-grid,
  .snap-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .info-grid,
  .snap-grid {
    grid-template-columns: 1fr;
  }
}
</style>
