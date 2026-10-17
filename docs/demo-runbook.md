# HarborGuard 五分钟 Demo 操作单

更新：2026-10-17，America/Los_Angeles。基线 main `782d04d`，已包含 A #7/#11、B #10、C #4。本操作单更新旧 #6 的模板交付，保持冻结契约，不覆盖队友代码。

展示范围：LIVE 合成安防/灾害仿真 → 三级警报与方案 → 模板 Agent → 人工审批 → 2D/3D → 明确标记的回放。YOLO 使用交付权重处理合成图；不宣传实海识别或未训练 LoRA。B 参数/船期仍为演示假设。A 的 NOAA 测深与建议浮标部署来源见其说明，不代表 B 的 LIVE 观测位置已通过实地部署验收。

## 提前准备依赖和构建

以下五分钟从服务就绪后开始计时，不包含首次联网安装。已有可用 venv 不要重建；Python 需要 >=3.11，Node 要求 ^20.19 或 >=22.12。

```powershell
# 仓库根目录；首次创建时选一个可用方式
py -3.11 -m venv .venv
# 本机 py 未登记解释器时，可改用 uv venv --seed --python 3.11 .venv
.venv/Scripts/python.exe -m pip install -r requirements-runtime.txt
.venv/Scripts/python.exe -m pip install -e '.[dev]'
.venv/Scripts/python.exe -m pip check
Push-Location frontend
npm.cmd ci --no-audit --no-fund
npm.cmd run build
Pop-Location
```

C 完整运行环境包含 CPU 推理与 Agent SDK；只有 B 锁文件不能保证 C 启动。不要现场下载模型或重新训练。若 CPU 推理依赖/权重不可用，B 明确显示 stub，不能把降级当作真实识别通过。

**保留旧演示库，为新配置指定独立新库。** #10 改变检查点指纹，直接加载旧配置库会拒绝启动；不要删除旧库、改 fingerprint 或在台上临时迁移。固定新库同版本重启会恢复并暂停，需显式 resume 或 reset。

## 三个终端

先检查 8000/8001/5173 是否被既有演示占用；不要杀不明进程或同时启动两套同端口服务。B 单进程、单 worker。

终端一，仓库根目录：

```powershell
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/demo-current.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

等待 application startup complete；YOLO 预热在 ready 之前。上一轮独立候选健康就绪约 5.96 秒，不是本轮全新安装耗时承诺。

终端二，仓库根目录，使用已验证模板降级路径：

```powershell
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
$env:AGENT_HOST = '127.0.0.1'
$env:AGENT_PORT = '8001'
$env:CLOUD_PROVIDER = 'disabled'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:9/v1'
$env:OLLAMA_TIMEOUT_S = '0.2'
.venv/Scripts/python.exe -m agent.main
```

这里本机关闭端口用于让未验收的本地模型快速降级，不需要外网密钥。不要在比赛前自动启用云/Ollama 路由；实际建议须检查 model=template。

终端三，frontend 目录：

```powershell
npm.cmd run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

前端默认 REST `http://localhost:8000/api`、WS `ws://localhost:8000/ws`，CORS 允许 localhost/127.0.0.1:5173。VITE_API_BASE/VITE_WS_URL 是构建时变量，改变后需由 A 重新构建。

## 上台前检查

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8001/health
```

B 返回 ok=true；C 的 phase 当前为 c3-openrouter，尚未处理请求时 model 可以是 idle，不能要求启动即 template。首个真实建议返回后核对来源。浏览器打开 `http://localhost:5173/`，检查 LIVE、2D、日志与浮标；检查 3D 可读性后回到 2D。若旧库恢复为暂停，先显式重置开始一场新演示。

## 展示顺序

| 墙钟 | 操作 | 应看到的核心行为 |
| --- | --- | --- |
| 0:00–0:20 | 介绍 LIVE 与合成业务数据，启动 Security 场景 A，10× | 航迹和一级警报，真实状态推送 |
| 0:20–1:15 | 等待二级/主动 Ping、三级及 options_ready；约 50–60 秒后暂停 | 带来源标签的声呐图、风险、方案、C 模板建议；以当前三级和方案为准，二级早期建议不等于可审批 |
| 1:15–1:45 | 选择当前有效局部方案，填写操作员，先驳回或直接批准 | 结构化 decision；驳回不封区，批准后对应分区 restricted。建议本身不执行限制 |
| 1:45–2:00 | 切 3D、展示同一航迹及海底，回 2D | 地图、航迹、选择状态一致；不宣称是实海目标 |
| 2:00–3:10 | 启动 Recovery 场景 B，10×，观察约一分钟 | 3 个确认阻塞区；燃料泊位因近场不足维持 unsurveyed；最终6 clear/3 blocked/3 unsurveyed，复航估计9小时。B4/B7在仿真60秒故障 |
| 3:10–3:45 | 打开 `?replay=replay_b.jsonl`，跳转时间轴 | 明确 REPLAY/只读；文件属于既有录制或合成基线，不用旧6/4/2结果冒充当前YOLO结果 |
| 3:45–5:00 | 回答问题、说明人工审批和验收边界 | 留出重试余量；不在台上重新编译、安装或 Merge |

上一轮固定 C 权重下三级为仿真505秒，原500秒验收项仍FAIL；10×约50.5秒，可在五分钟流程展示。这里只陈述历史实测和操作预算，不宣称新main浏览器完整彩排已通过。

## 故障兜底

- B 不启动：检查旧库指纹、单写者锁、依赖及端口。保留旧库，使用上面独立新库路径；不要删除历史或停止别人的服务。
- Agent 无建议：检查 C health、B 的 options_ready、当前三级、C 队列及日志；不从自由文本日志伪造审批。B 问答502通常为C未就绪，504为20秒代理超时。
- LIVE 断线/刷新：A 已有恢复机制，但同刻日志/决策身份和旧快照竞态仍有既往问题，最新主线的真实浏览器复测待做。当前能补最近500条事件；窗口外展示历史可能不全，不承诺分页恢复。
- 3D 过慢：回2D完成核心流程。最新3D build有约1,003KB chunk警告，现场投影FPS未由本轮验收。
- Detection.track_id为空：仍可通过Detection ID打开后端PNG；没有航迹不是图片不存在。燃料泊位没有有效新图时保持未确认，不制造一张成功识别。
- 回放兜底：明确展示REPLAY，静态回放不能提交真实审批。A 的回放/部署图片需一起提供，本次不覆盖其文件。
- network_down是仿真事件，不等同真实断Wi-Fi，不代表ESP32或LoRa离线运行。

结束只关闭自己启动的进程。当前已运行的旧演示checkout和数据库保持原样。接口见 [交接文档](frontend-integration.md)，版本与证据见 [集成报告](final-integration-report.md)。
