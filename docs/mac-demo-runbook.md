# Mac 本机实时演示操作手册

本手册用于 `demo/mac-integration` 分支的无参数 LIVE 页面。正式演示使用后端 8000、Agent 8001、Ollama 11434 和前端生产预览 5173；`?mock=1` 与回放页面只能作为离线演示兜底，不能代替真实后端联调。

## 演示前检查

在仓库根目录执行：

```bash
cd /Users/chrisjiang/Projects/harborguard

for port in 11434 8000 8001 5173; do
  echo "PORT ${port}"
  lsof -nP -iTCP:${port} -sTCP:LISTEN || true
done

curl -fsS http://127.0.0.1:11434/api/tags
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8001/health
```

已占用端口时先核对命令、工作目录和健康检查。确认是本项目且状态正确就复用；未知进程不得直接结束。正式预览必须使用 5173；若它被其他项目占用，先由该进程的负责人正常停止，再启动 HarborGuard。临时改用其他端口只能用于排错，并应记为未完成正式端口验收。

`frontend/.env.local` 只保存在本机，应包含：

```dotenv
VITE_API_BASE=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

根目录 `.env` 含模型凭证，不打印、不复制到日志，也不提交。当前本地模型是未微调的 `qwen3:1.7b`；没有 `harborguard-lora` 或 `ml/lora/metrics.json` 时不得称为 LoRA 已部署。

## 启动顺序

只在对应健康检查失败且端口空闲时启动服务。每个命令放在独立终端前台运行，停止时只在同一终端按 `Ctrl-C`，不要按端口批量 `kill`。

终端一，Ollama：

```bash
ollama serve
```

终端二，后端：

```bash
cd /Users/chrisjiang/Projects/harborguard
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

终端三，Agent：

```bash
cd /Users/chrisjiang/Projects/harborguard
.venv/bin/python -m agent.main
```

终端四，前端生产构建与固定端口预览：

```bash
cd /Users/chrisjiang/Projects/harborguard/frontend
npm run build
npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

打开 `http://localhost:5173/`，不要添加 query 参数。顶栏必须显示 LIVE。页面连接失败时先检查 8000 和 WebSocket，不要切到 mock 后继续声称是真实联调。

## 四分钟演示步骤

### 0:00–0:25 服务与数据来源

展示无参数 LIVE 页面、四个健康端口和指标卡。说明 YOLO 数字来自 600 张合成验证集，`lora=null` 表示尚无 LoRA 评估结果，不表示训练正在运行。

### 0:25–1:45 场景 A

从顶栏启动场景 A，选择 10×。选中水下目标并展示 2D/3D 位置、航迹和警报升级；等待主动 ping 的 detection，打开声呐图，确认记录中的 `model` 是 `yolo26n` 而不是 `stub`。等待 `options_ready` 后展示 Agent 建议；只有事件实际标记 `model=cloud` 时才称为云端建议。

在批准前先指出相关分区仍未因 Agent 建议自动变为 `restricted`。选择当前方案、填写操作员并点击“批准”，等待后端 `decision` 与 `zone_changed` 事件后再展示限制状态。不要由 Agent 调用 `/api/decision`。

### 1:45–2:55 场景 B

从顶栏启动场景 B，选择 10×。展示后端真实 `reopen_plan` 的可复航、待勘测、封闭分区和节省时间；展示灾害建议并核对其 `recommended_option_id` 为空。切换到 3D 查看复航路线，说明前端不自行计算计划。

### 2:55–3:35 仿真断外网降级

通过界面注入“断外网”，再注入一个浮标离线以产生新建议。确认 LIVE 连接仍在、页面和本地声呐/3D 仍可使用，下一条建议如实显示“本地模型”或“模板”。仿真 `network=offline` 只验证 Agent 跳过云端，不等于物理关闭 Wi-Fi。

恢复仿真网络，确认后续事件具备重新走云端的条件；没有出现新的真实 cloud 建议时，只说明“已恢复条件”，不要宣称已验证切回。

### 3:35–4:00 指标与边界

刷新指标卡，核对后端 `/api/metrics`：YOLO 值保持原样，LoRA 为“尚未提供评估结果”。最后说明三项仍需现场人工验收：真正关闭 Wi-Fi 后刷新页面、投影仪 3 米可读性、录屏文件跨设备试播。

## 收尾与停止

先在页面执行重置，使场景回到空闲。保留其他人已运行的服务；只在自己启动服务的终端按 `Ctrl-C`。关闭后用相同的端口检查确认自己的进程已经退出，不结束未知 PID。

真实关闭 Wi-Fi 时，先保证四个本地服务已经运行且页面资源加载完成。该操作、投影效果与系统录屏权限必须由现场操作员手工完成，代码检查不能替代。
