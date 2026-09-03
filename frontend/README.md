# Frontend (Phase 3)

Vue3 + Vite + Element Plus + ECharts 产线监控台。

## 启动

先启动后端 `http://127.0.0.1:8000`，再：

```powershell
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`。

开发服务器已将 `/api` 代理到后端；后端同时开启了 CORS。

## 页面

- `/` 总览 Dashboard（8s 轮询）
- `/devices` 设备列表
- `/devices/:id` 设备详情 + 时序曲线
- `/alarms` 告警中心
- `/alarms/:id` 报警详情（含 snapshot）

顶栏可「注入高温剧本 / 重置模拟」。
