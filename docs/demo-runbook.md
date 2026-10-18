# HarborGuard 五分钟 Demo 操作单

更新：2026-10-17，America/Los_Angeles；截止22:00 PDT。实测main **`a841bf9a70d8bf8237b9e03763852a34bed10368`**，已包含#4/#7/#13/#14/#15，不使用旧#6。详见[最终交付检查](final-delivery-20261017.md)。

最新main实际A/B/C浏览器2D闭环 **286.008秒（4分46秒）**，当前浏览器3D不可用；恢复R1–R4仍FAIL。B方案指标广播补丁仅在本地e1候选，237 PASS/2 SKIP，尚未Push/合入；负责人先审阅并锁定最终SHA。不再为20ms做高风险重构。

展示范围：LIVE合成仿真→三级警报与方案→模板Agent→人工审批→2D（目标电脑3D另验）→标记Replay。YOLO使用交付权重处理合成图。仓库已有C团队LoRA合成评估，本轮运行时仅验template；不默认cloud/local/LoRA服务通过。B参数/船期为演示假设；A的NOAA测深来源不代表B LIVE位置已通过实地部署验收。

P0补充：旧场景B的绿色区/12小时结论已证实不可靠。新版未决保护和投影复验见 [审计报告](../backend/docs/survey-p0-audit.md)；当前按状态计算的9小时也只是仿真假设指标，不是实际复航许可。展示流程成功和浏览器验收均不代替业务安全判定。

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
$env:VITE_API_BASE = 'http://127.0.0.1:8000/api'
$env:VITE_WS_URL = 'ws://127.0.0.1:8000/ws'
npm.cmd run build
Pop-Location
```

C 完整运行环境包含 CPU 推理与 Agent SDK；只有 B 锁文件不能保证 C 启动。不要现场下载模型或重新训练。若 CPU 推理依赖/权重不可用，B 明确显示 stub，不能把降级当作真实识别通过。

**保留旧演示目录和库，在独立checkout用新库。** 新配置指纹与旧库不兼容会拒绝启动；不要删除旧库、改fingerprint或在台上临时迁移。同版本同库重启恢复并暂停，显式Resume或Reset。当前5184使用QA同源构建，不要直接当标准5173部署；先按上述地址为正式checkout构建，不覆盖正在演示的dist。

## 三个终端

先检查 8000/8001/5173 是否被既有演示占用；不要杀不明进程或同时启动两套同端口服务。B 单进程、单 worker。

终端一，仓库根目录：

```powershell
New-Item -ItemType Directory -Force backend/runtime | Out-Null
$env:PYTHONPATH = (Get-Location).Path
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/demo-a841-final-new.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

等待application startup complete；YOLO预热在ready之前。本轮准备好依赖后，三服务就绪10.295秒；首次从零安装耗时PENDING，不是从零五分钟承诺。

终端二，仓库根目录，使用已验证模板降级路径：

```powershell
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
$env:AGENT_HOST = '127.0.0.1'
$env:AGENT_PORT = '8001'
$env:CLOUD_PROVIDER = 'disabled'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:9/v1'
$env:OLLAMA_MODEL = 'qwen3:1.7b'
$env:OLLAMA_FORMAT_OVERRIDES = ''
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
| 1:45–2:00 | 仅在实际录制电脑已验3D时展示，否则保持2D | 当前内嵌浏览器不可用，不现场调GPU或安装 |
| 2:00–3:10 | 启动 Recovery 场景 B，10×，观察约一分钟 | 3 个确认阻塞区；燃料泊位因近场不足维持 unsurveyed；最终6 clear/3 blocked/3 unsurveyed，复航估计9小时。B4/B7在仿真60秒故障 |
| 3:10–4:20 | 展示未决状态/路线，打开下述本轮实流Replay | 明确REPLAY/只读及source SHA；End停尾帧前可点Play；旧stub不冒充本轮YOLO |
| 3:45–5:00 | 回答问题、说明人工审批和验收边界 | 留出重试余量；不在台上重新编译、安装或 Merge |

本轮真实权重三级为505仿真秒，原500秒要求仍FAIL；10×约50.5秒。Recovery参考6/3/3与9小时由实际状态和假设计算，按现场返回展示，不凑数字。单机实际2D浏览器4分46秒含3D降级，不是三人现场彩排或所有恢复边界通过；保存截图但没有录屏成片。

## 故障兜底

- B 不启动：检查旧库指纹、单写者锁、依赖及端口。保留旧库，使用上面独立新库路径；不要删除历史或停止别人的服务。
- Agent 无建议：检查 C health、B 的 options_ready、当前三级、C 队列及日志；不从自由文本日志伪造审批。B 问答502通常为C未就绪，504为20秒代理超时。
- LIVE断线/刷新：最新main同刻同文实时2条→刷新1条，日志GET503无失败提示；最新A多操作员及旧REST竞态函数复现仍FAIL，详见[给A交接](../backend/docs/A-final-recovery-handoff.md)。演示减少不必要刷新，但不把回避当已修复。只能补500事件窗口，不承诺分页或完整早期历史。
- 3D 过慢：回2D完成核心流程。最新3D build有约1,003KB chunk警告，现场投影FPS未由本轮验收。
- Detection.track_id为空：仍可通过Detection ID打开后端PNG；没有航迹不是图片不存在。燃料泊位没有有效新图时保持未确认，不制造一张成功识别。
- 回放兜底：明确展示REPLAY，静态回放不能提交真实审批。A 的回放/部署图片需一起提供，本次不覆盖其文件。
- network_down是仿真事件，不等同真实断Wi-Fi，不代表ESP32或LoRa离线运行。

结束只关闭自己启动的进程。当前已运行的旧演示checkout和数据库保持原样。接口见 [交接文档](frontend-integration.md)，版本与证据见 [集成报告](final-integration-report.md)。

## 本轮隔离预览与应急回放

- 最新main预览：`http://127.0.0.1:5184/`，B8020/C8021、新SQLite；旧5173仍为旧演示环境，未切换。
- Recovery：`http://127.0.0.1:5184/?replay=/final_replays/replay_maina841bf9_b.jsonl`
- Security：`http://127.0.0.1:5184/?replay=/final_replays/replay_maina841bf9_a.jsonl`
- 便携包：`artifacts/final-delivery/HarborGuard-maina841bf9-replays.zip`，含manifest与8张PNG；正式部署由A提供相同`final_replays/`静态目录，B未改frontend。
- 旧`replay_a/replay_b`可作明确标记的历史stub兜底；`demo_a/demo_b/demo_full`摘要超60字符，修正前不作为契约通过证据。

5184为本机QA同源代理，不能把故障注入测试接口部署为生产服务。正式切换仅在负责人许可、旧演示结束后，检查端口并在独立checkout新库按上述命令启动。不要自动终止5173/8000/8001或覆盖旧库。

## 复验与最终提交

```powershell
.venv/Scripts/python.exe -m pytest backend/tests tests agent/tests -q
.venv/Scripts/python.exe -m ruff check backend
.venv/Scripts/python.exe -m compileall -q backend agent ml
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m backend.tools.model_acceptance --scenario b --repeat 3 --out artifacts/final-real-b.json
Push-Location frontend
npm.cmd run build
npm.cmd run lint
npm.cmd run check:a1
npm.cmd run check:a2
npm.cmd run check:a3
npm.cmd run check:a4
npm.cmd run check:a5
npm.cmd run check:a6
npm.cmd run check:recovery
npm.cmd run check:sonar
npm.cmd run check:english
Pop-Location
```

最新main232 PASS/2 SKIP；缺少另一份COCO冒烟权重的两项SKIP不能算通过，未现场下载。当前main20分钟耐久PENDING，5a68的20分钟通过不得移算。本轮未Push、未Merge、未切换正式部署、未提交Devpost。

负责人最后录制并试播成片、提供可访问视频URL、核对活动规则/成员/必填项并在22:00 PDT前提交，保留回执。可以采用已验证的2D范围，不为理论100%错过截止，也不省略局限。草稿见[Devpost](devpost-submission-draft.md)。
