<template>
  <span v-if="value" class="status-pill" :class="'status-' + value">{{ text }}</span>
  <span v-else class="muted">-</span>
</template>

<script setup>
import { computed } from 'vue'
import {
  labelAlarmLevel,
  labelAlarmStatus,
  labelDeviceStatus,
} from '@/utils/labels'

const props = defineProps({
  value: { type: String, default: '' },
  /** device | alarm | level */
  type: { type: String, default: 'alarm' },
})

const text = computed(() => {
  if (props.type === 'device') return labelDeviceStatus(props.value)
  if (props.type === 'level') return labelAlarmLevel(props.value)
  return labelAlarmStatus(props.value)
})
</script>
