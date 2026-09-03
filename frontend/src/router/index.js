import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { getToken, isLoggedIn } from '@/utils/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
      { path: 'devices', name: 'devices', component: () => import('@/views/DevicesView.vue') },
      {
        path: 'devices/:id',
        name: 'device-detail',
        component: () => import('@/views/DeviceDetailView.vue'),
      },
      { path: 'alarms', name: 'alarms', component: () => import('@/views/AlarmsView.vue') },
      {
        path: 'alarms/:id',
        name: 'alarm-detail',
        component: () => import('@/views/AlarmDetailView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) {
    if (to.name === 'login' && isLoggedIn()) {
      return { path: '/' }
    }
    return true
  }
  if (to.meta.requiresAuth || to.matched.some((r) => r.meta.requiresAuth)) {
    if (!getToken()) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

export default router
