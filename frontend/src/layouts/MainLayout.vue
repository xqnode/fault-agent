<template>
  <div class="pure-app" :class="{ 'is-collapsed': collapsed }">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="logo-mark">FA</div>
        <span v-show="!collapsed" class="logo-title">Fault Agent</span>
      </div>
      <nav class="sidebar-menu">
        <router-link
          v-for="item in menus"
          :key="item.path"
          :to="item.path"
          class="menu-item"
          :class="{ 'is-active': isActive(item) }"
        >
          <span class="menu-ico" aria-hidden="true">{{ item.icon }}</span>
          <span v-show="!collapsed" class="menu-text">{{ item.title }}</span>
        </router-link>
      </nav>
    </aside>

    <div class="main-wrap">
      <header class="navbar">
        <div class="navbar-left">
          <button class="collapse-btn" type="button" @click="collapsed = !collapsed" :title="collapsed ? '展开' : '收起'">
            <span>{{ collapsed ? '☰' : '☰' }}</span>
          </button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.name !== 'dashboard'">{{ title }}</el-breadcrumb-item>
            <el-breadcrumb-item v-else>工厂运行总览</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="navbar-right">
          <el-button @click="onReset" :loading="busy">重置模拟</el-button>
          <el-button type="primary" @click="onInject" :loading="busy">注入高温剧本</el-button>
          <el-dropdown trigger="click" @command="onUserCommand">
            <span class="user-entry">
              <span class="user-avatar">管</span>
              <span class="user-name">{{ displayName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>角色：{{ roleLabel }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <section class="app-main">
        <div class="page-body">
          <router-view />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { getUser, logoutAndRedirect } from '@/utils/auth'
import { getErrorMessage } from '@/utils/error'
import { labelRole } from '@/utils/labels'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { api } from '@/api/client'

const route = useRoute()
const router = useRouter()
const busy = ref(false)
const collapsed = ref(false)

const displayName = computed(() => {
  const user = getUser()
  return user?.nickname || user?.username || '用户'
})

const roleLabel = computed(() => labelRole(getUser()?.role))

const menus = [
  { path: '/', title: '总览', icon: '▣', match: ['dashboard'] },
  { path: '/devices', title: '设备', icon: '⚙', match: ['devices', 'device-detail'] },
  { path: '/alarms', title: '告警中心', icon: '⚠', match: ['alarms', 'alarm-detail'] },
]

const title = computed(() => {
  const map = {
    dashboard: '工厂运行总览',
    devices: '设备管理',
    'device-detail': '设备详情',
    alarms: '告警中心',
    'alarm-detail': '报警详情',
  }
  return map[route.name] || '产线监控'
})

function isActive(item) {
  return item.match.includes(route.name)
}

function onUserCommand(cmd) {
  if (cmd === 'logout') {
    logoutAndRedirect(router)
    ElMessage.success('已退出登录')
  }
}

async function onInject() {
  busy.value = true
  try {
    const data = await api.injectScenario()
    ElMessage.success(`已注入剧本，报警 #${data.alarm_id}`)
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '注入失败'))
  } finally {
    busy.value = false
  }
}

async function onReset() {
  busy.value = true
  try {
    await api.resetSimulator()
    ElMessage.success('模拟器已重置')
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '重置失败'))
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.pure-app {
  --sidebar-width: 210px;
  --sidebar-collapsed: 64px;
  --navbar-height: 48px;
  display: flex;
  width: 100%;
  min-height: 100vh;
  background: var(--pure-bg);
}

.sidebar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  height: 100vh;
  flex-shrink: 0;
  background: var(--pure-theme-menu-bg);
  transition: width 0.2s ease;
  overflow: hidden;
}

.is-collapsed .sidebar {
  width: var(--sidebar-collapsed);
}

.sidebar-logo {
  height: var(--navbar-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  background: var(--pure-theme-sidebar-logo);
  border-bottom: 1px solid rgb(255 255 255 / 6%);
}

.logo-mark {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #4091f7, #3375db);
}

.logo-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  padding: 8px 0;
  overflow-y: auto;
}

.menu-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  margin: 2px 8px;
  padding: 0 12px;
  border-radius: 4px;
  color: var(--pure-theme-menu-text);
  transition: background 0.15s, color 0.15s;
}

.menu-item:hover {
  color: var(--pure-theme-menu-title-hover);
  background: var(--pure-theme-menu-hover);
}

.menu-item.is-active {
  color: var(--pure-theme-sub-menu-active-text);
  background: var(--pure-theme-menu-hover);
}

.menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: var(--pure-theme-menu-active-before);
}

.is-collapsed .menu-item {
  justify-content: center;
  padding: 0;
  margin: 2px 6px;
}

.menu-ico {
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  font-size: 14px;
  opacity: 0.9;
}

.menu-text {
  font-size: 14px;
  white-space: nowrap;
}

.main-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.navbar {
  position: sticky;
  top: 0;
  z-index: 15;
  height: var(--navbar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgb(0 21 41 / 8%);
}

.navbar-left,
.navbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.collapse-btn {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #606266;
  cursor: pointer;
  font-size: 16px;
}

.collapse-btn:hover {
  background: #f2f3f5;
  color: var(--el-color-primary);
}

.user-entry {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-left: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  color: #606266;
}

.user-entry:hover {
  background: #f2f3f5;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12px;
  color: #fff;
  background: #409eff;
}

.user-name {
  font-size: 13px;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-main {
  flex: 1;
  padding: 16px;
  background: var(--pure-bg);
}

.page-body {
  width: 100%;
  min-width: 0;
}

@media (max-width: 768px) {
  .pure-app {
    flex-direction: column;
  }

  .sidebar {
    position: relative;
    width: 100% !important;
    height: auto;
  }

  .sidebar-menu {
    display: flex;
    padding: 4px 8px 8px;
    overflow-x: auto;
  }

  .menu-item {
    flex-shrink: 0;
  }

  .menu-item.is-active::before {
    display: none;
  }

  .sidebar-foot {
    display: none;
  }

  .navbar-right {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}
</style>
