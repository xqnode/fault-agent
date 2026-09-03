<template>
  <div class="page" v-loading="loading">
    <div class="panel" v-if="alarm">
      <div class="panel-hd">
        <div>
          <h2>报警 #{{ alarm.id }} · {{ labelAlarmType(alarm.alarm_type) }}</h2>
          <div class="muted">{{ alarm.alarm_message }}</div>
        </div>
        <span class="status-pill" :class="'status-' + alarm.status">{{ labelAlarmStatus(alarm.status) }}</span>
      </div>
      <div class="panel-bd grid">
        <div>
          <div class="muted">设备 ID</div>
          <div class="mono">{{ alarm.device_id }}</div>
        </div>
        <div>
          <div class="muted">等级</div>
          <div>
            <span class="status-pill" :class="'status-' + alarm.alarm_level">{{ labelAlarmLevel(alarm.alarm_level) }}</span>
          </div>
        </div>
        <div>
          <div class="muted">指标</div>
          <div class="mono">{{ alarm.metric_name }}</div>
        </div>
        <div>
          <div class="muted">实测 / 阈值</div>
          <div class="mono">{{ alarm.measured_value }} / {{ alarm.threshold_value }}</div>
        </div>
        <div>
          <div class="muted">产生时间</div>
          <div>{{ formatTime(alarm.created_at) }}</div>
        </div>
        <div>
          <div class="muted">关闭时间</div>
          <div>{{ formatTime(alarm.resolved_at) }}</div>
        </div>
      </div>
    </div>

    <div class="panel" v-if="alarm">
      <div class="panel-hd"><h2>触发快照</h2></div>
      <div class="panel-bd">
        <pre class="snap mono">{{ JSON.stringify(alarm.snapshot_json, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import { labelAlarmLevel, labelAlarmStatus, labelAlarmType } from '@/utils/labels'

const route = useRoute()
const alarm = ref(null)
const loading = ref(false)

function formatTime(v) {
  return v ? new Date(v).toLocaleString() : '-'
}

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
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.snap {
  margin: 0;
  padding: 12px;
  background: #f4f7fb;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: auto;
}

@media (max-width: 800px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
