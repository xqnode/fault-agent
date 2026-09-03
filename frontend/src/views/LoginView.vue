<template>
  <div class="login-page">
    <aside class="brand-panel" aria-hidden="false">
      <div class="brand-glow"></div>
      <div class="brand-inner">
        <div class="brand-top">
          <div class="hero-mark">FA</div>
          <div class="brand-copy">
            <h1>Fault Agent</h1>
            <p>制造业智能故障分析 · 产线监控台</p>
          </div>
        </div>
        <ul class="feature-list">
          <li v-for="item in features" :key="item">
            <span class="dot"></span>
            <span>{{ item }}</span>
          </li>
        </ul>
      </div>
      <svg class="wave-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path d="M70,0 C82,28 78,62 70,100 L100,100 L100,0 Z" fill="#f5f7fa" />
      </svg>
    </aside>

    <main class="form-panel">
      <div class="login-card">
        <div class="card-head">
          <div class="avatar">FA</div>
          <h2>管理员登录</h2>
          <p class="hint">数据库账号登录 · JWT 轻量权限</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          label-position="top"
          @submit.prevent="onSubmit"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              clearable
              autocomplete="username"
              @keyup.enter="onSubmit"
            >
              <template #prefix>
                <el-icon class="field-ico"><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              autocomplete="current-password"
              @keyup.enter="onSubmit"
            >
              <template #prefix>
                <el-icon class="field-ico"><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-button class="submit" type="primary" :loading="loading" @click="onSubmit">
            登 录
          </el-button>
        </el-form>

        <div class="card-foot">
          <span>演示账号</span>
          <code>admin/admin123</code>
          <span>·</span>
          <code>engineer/engineer123</code>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { api } from '@/api/client'
import { setAuth } from '@/utils/auth'

const router = useRouter()
const route = useRoute()
const formRef = ref()
const loading = ref(false)

const features = ['设备状态总览', '告警闭环追踪', '模拟剧本注入']

const form = reactive({
  username: 'admin',
  password: 'admin123',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  if (loading.value) return
  if (!formRef.value) {
    ElMessage.error('表单未就绪，请刷新页面')
    return
  }
  try {
    const ok = await formRef.value.validate().catch(() => false)
    if (!ok) return
  } catch {
    return
  }
  loading.value = true
  try {
    const data = await api.login({
      username: String(form.username || '').trim(),
      password: String(form.password || ''),
    })
    if (!data?.access_token) {
      throw new Error('登录响应异常')
    }
    setAuth(data.access_token, data.user)
    ElMessage.success(`欢迎，${data.user?.nickname || data.user?.username}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect || '/')
  } catch (e) {
    ElMessage.error(e?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(420px, 1.15fr) minmax(420px, 1fr);
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f5f7fa;
}

.brand-panel {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 72px 48px 64px;
  color: #fff;
  background:
    radial-gradient(720px 420px at 18% 18%, rgb(64 158 255 / 28%), transparent 62%),
    radial-gradient(520px 360px at 70% 86%, rgb(0 33 71 / 45%), transparent 55%),
    linear-gradient(160deg, #001529 0%, #003a70 48%, #1d6fd8 100%);
  overflow: hidden;
}

.brand-glow {
  position: absolute;
  inset: auto -40px -80px auto;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: rgb(255 255 255 / 8%);
  filter: blur(2px);
}

.brand-inner {
  position: relative;
  z-index: 1;
  width: min(440px, 100%);
}

.brand-top {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-bottom: 36px;
}

.hero-mark {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: rgb(255 255 255 / 14%);
  border: 1px solid rgb(255 255 255 / 22%);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 18%);
}

.brand-copy h1 {
  margin: 0;
  font-size: 40px;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.brand-copy p {
  margin: 10px 0 0;
  font-size: 15px;
  line-height: 1.6;
  color: rgb(255 255 255 / 82%);
}

.feature-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgb(255 255 255 / 8%);
  border: 1px solid rgb(255 255 255 / 10%);
  backdrop-filter: blur(6px);
  font-size: 14px;
  color: rgb(255 255 255 / 92%);
}

.feature-list .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #79bbff;
  box-shadow: 0 0 0 4px rgb(121 187 255 / 18%);
}

.wave-svg {
  position: absolute;
  top: 0;
  right: -1px;
  width: 88px;
  height: 100%;
  z-index: 2;
  pointer-events: none;
}

.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  background: #f5f7fa;
}

.login-card {
  width: min(400px, 100%);
  padding: 40px 36px 28px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  box-shadow:
    0 1px 2px rgb(0 21 41 / 4%),
    0 18px 48px rgb(0 21 41 / 8%);
}

.card-head {
  text-align: center;
  margin-bottom: 28px;
}

.avatar {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(145deg, #66b1ff, #337ecc);
  box-shadow: 0 8px 20px rgb(64 158 255 / 28%);
}

.card-head h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 650;
  color: #1f2d3d;
}

.hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: #909399;
}

.field-ico {
  color: #909399;
  font-size: 16px;
}

.login-card :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-card :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  padding-left: 12px;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

.submit {
  width: 100%;
  height: 44px;
  margin-top: 6px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.18em;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px dashed #ebeef5;
  font-size: 12px;
  color: #a8abb2;
}

.card-foot code {
  padding: 1px 6px;
  border-radius: 4px;
  background: #f5f7fa;
  color: #606266;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}

@media (max-width: 960px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .brand-panel {
    display: none;
  }

  .form-panel {
    min-height: 100vh;
  }
}
</style>
