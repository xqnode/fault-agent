import axios from 'axios'
import { clearAuth, getToken } from '@/utils/auth'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 15000,
})

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      return Promise.reject(new Error(body.message || '业务错误'))
    }
    return body?.data !== undefined ? body.data : body
  },
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    if (status === 401) {
      clearAuth()
      if (!window.location.pathname.startsWith('/login')) {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?redirect=${redirect}`
      }
    }
    if (typeof detail === 'string') {
      return Promise.reject(new Error(detail))
    }
    return Promise.reject(err)
  },
)

export const api = {
  login: (payload) => client.post('/api/auth/login', payload),
  me: () => client.get('/api/auth/me'),
  getOverview: () => client.get('/api/dashboard/overview'),
  getDevices: (params) => client.get('/api/devices', { params }),
  getDevice: (id) => client.get(`/api/devices/${id}`),
  getSensorData: (id, params) => client.get(`/api/devices/${id}/sensor-data`, { params }),
  getAlarms: (params) => client.get('/api/alarms', { params }),
  getAlarm: (id) => client.get(`/api/alarms/${id}`),
  injectScenario: (scenario_code = 'SMT_TEMP_RISE_001') =>
    client.post('/api/simulator/inject', { scenario_code, sync: true }),
  resetSimulator: () => client.post('/api/simulator/reset'),
  getSimulatorStatus: () => client.get('/api/simulator/status'),
}

export default client
