# HarborGuard 后端与算法

面向洛杉矶港水下安防与灾后分区复航的黑客松演示后端。一个 Python 进程完成可复现仿真、被动声学观测、定位跟踪、风险警报、声呐识别适配和方案计算。操作员审批后才改变安防限制状态。

开发依据是任务书 B。对外字段以 [共享契约 v1](../shared/contract.md) 为准；[TypeScript 类型原文](../shared/types.ts)、[状态样例](../shared/sample_state.json) 和 [全部事件样例](../shared/sample_events.json) 可直接交给 A、C 对接。

本次新增文件见 [文件清单](../docs/files.md)，逐项验收范围见 [任务书验收范围](../docs/acceptance.md)。

前端和 AI 队友从 [联调交接](../docs/frontend-integration.md) 开始：含全部 21 个 REST 接口、WebSocket、审批与事件恢复、数据单位、可直接加载的 Mock 和完整 OpenAPI。运行 `python -m backend.tools.integration_bundle` 可重新生成，不修改冻结契约。

最终交付以 [集成检查报告](../docs/final-integration-report.md) 和 [五分钟 Demo 操作单](../docs/demo-runbook.md) 为准。当前真实 A/B/C 模板闭环已验证；A 的刷新恢复和无航迹碎片入口仍由 A 修复。

## 安装与启动

要求 Python 3.11 或更新版本，命令均在仓库根目录运行。

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
make backend
```

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
./dev.ps1 setup
./dev.ps1 backend
```

若 PowerShell 的脚本执行策略阻止本地脚本，可直接执行 `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`。本机 Python 3.11 由 uv 管理，`py -3.11` 无法解析；请用 `uv venv --seed --python 3.11 .venv` 替代创建命令，已有虚拟环境不重复创建。

后端健康检查：`http://localhost:8000/api/health`；交互式接口文档：`http://localhost:8000/docs`；WebSocket：`ws://localhost:8000/ws`。启动时处于空闲状态，先调用场景启动接口。使用单个 worker，避免产生多份仿真世界。

## 演示操作

```bash
curl -X POST http://localhost:8000/api/scenario/a/start -H "Content-Type: application/json" -d '{"speed":10}'
curl http://localhost:8000/api/state
curl -X POST http://localhost:8000/api/control -H "Content-Type: application/json" -d '{"action":"pause"}'
curl -X POST http://localhost:8000/api/control -H "Content-Type: application/json" -d '{"action":"resume"}'
curl -X POST http://localhost:8000/api/control -H "Content-Type: application/json" -d '{"action":"speed","value":4}'
```

PowerShell 可用 `Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/scenario/a/start -ContentType application/json -Body '{"speed":10}'`。

1. 启动场景 A，观察 unknown 航迹、三级警报、自动主动 ping 和带框声呐图。三级时会发 `options_ready`；通过 `GET /api/options/{alert_id}` 取得当前方案。
2. 将真实返回的 `alert_id`、`option_id` 与 `action: "approve"`、`operator: "demo"` POST 到 `/api/decision`，对应分区才成为 `restricted`。`reject` 只记录日志。批准的限制保持到重置。
3. POST `/api/inject`，例如 `{"type":"buoy_down","target":"B4"}`、`{"type":"network_down"}`、`{"type":"noise_up"}`；分别用 `buoy_up`、`network_up`、`noise_down` 恢复。噪声注入是幂等开关，不会反复叠加。
4. POST `/api/scenario/b/start`，观察灾害覆盖、`blocked`、`clear`、`unsurveyed` 和 `reopen_plan`。B4、B7 在仿真 60 秒失效。
5. POST `/api/control`，内容 `{"action":"reset"}`，清除航迹、警报、识别、建议、限制、故障并回到空闲状态；再次启动场景。消息 seq 和警报/识别 ID 在进程内递增，避免旧审批误命中新场景。

`DEBUG_TRUTH_TRACKS=1` 是明确标注的真值演示兜底；正常启动和回放录制均使用声学定位跟踪。没有 C 的模块/权重时自动使用声呐桩，`Detection.model` 始终显示 `stub`，不需要安装 YOLO 才能运行。

## 验证与回放

```bash
make test
make check
make samples
make record
# 等价 PowerShell：./dev.ps1 test、check、samples、record
```

`make record` 在不等待墙钟的情况下生成 `frontend/public/replay_a.jsonl`、`replay_b.jsonl`，每行含 `wall_ms` 与契约消息 `msg`。`wall_ms = 仿真秒 / speed × 1000`。声呐图另存 `frontend/public/replay_assets/{a,b}/`，回放消息里的 `image_url` 指向这些静态文件，使后端关闭后仍可加载图片。模板建议仅在离线录制时生成，并明确标记 `model: "template"`；在线建议由 C 提交。

A 的回放器只需按 `wall_ms` 依次分发完整 `state` 和 `event`，无需后端。部署时连同 `replay_assets/` 复制。回放格式与实时信封一致；目前仓库没有 A 的回放 UI，因此还需在其前端中实际验收。

可运行真实服务耐久检查：

```bash
python -m backend.tools.soak --seconds 1200 --port 8000 --report artifacts/soak.json
```

它启动独立 Uvicorn，循环 A/B、模拟故障、校验 WebSocket 和声呐 PNG，记录 RSS、单核 CPU 百分比、推送频率和消息大小；结束时关闭它启动的进程。端口必须空闲。检查结果见 [验证记录](../docs/validation.md)。

## 与 A 和 C 集成

| 进程 | 负责人 | 地址 / 启动约定 |
| --- | --- | --- |
| 后端 | B | `make backend`，8000 |
| 前端 | A | 在 A 的 `frontend/` 执行其 README 命令，开发端口 5173；生产构建由 A 提供 |
| Agent | C | C 的 ASGI 服务监听 8001，必须实现 `POST /ask` |
| Ollama | C | 模板 Demo 不启动；未来路由使用 11434，由 C 负责 |

当前模板演示启动顺序：后端 → `python -m agent.main` → 前端生产预览（5173）。A6 已在 main，C3 来自 c/model-agent 并已纳入本地集成候选；本演示不依赖 Ollama、云端密钥或训练权重。前端在 frontend/ 运行 `npm ci`、`npm run build`，然后 `npm run preview -- --host 127.0.0.1 --port 5173 --strictPort`。

- A：订阅 `/ws`。`state` 是 5 Hz 完整快照，`event` 实时发送。CORS 允许 localhost 和 127.0.0.1 的 5173。重连后读取初始快照并用 `/api/events?since_seq=N` 补事件，缓存仅最近 500 条；若新快照 seq 小于旧值，表示进程重启，应重置事件游标并重新建立视图。若断线过久也需重新建立本地视图。后端主动断开过慢客户端，避免堵塞仿真。
- C 声呐：提供 `ml/sonar/render.py:render_ping` 和 `ml/yolo/infer.py:SonarDetector`，返回任务书约定的灰度图和像素角点框，权重 `ml/yolo/weights/best.pt`。从仓库根目录启动，模块可直接导入。
- 灾害碎片本身不发声，没有被动航迹时，其 Detection 的 `track_id` 为契约允许的空字符串；前端按 Detection ID 展示声呐图，不查询空航迹 ID。
- 实时 Detection 的 image_url 是后端相对路径，前端按 `http://localhost:8000` 解析；离线回放里的静态图片路径按前端自身站点解析。
- C Agent：订阅警报和方案；从 REST 获取细节，将完整 Recommendation POST 到 `/api/recommendations`。结构或引用 ID 非法返回 422。后端校验、保存最新建议并广播，不代为审批。
- BACKEND_BASE_URL 为后端根地址，C3 客户端为 REST 补 `/api`，WS 使用 `/ws`。C3 模板问答总预算为 18 秒，低于 B 代理的 20 秒；配置中未启用的 Ollama 30 秒预算不代表当前问答会调用本地 LLM。
- 当前锁文件覆盖 B 运行测试，以及 C1 渲染器/C3 模板所需依赖；本轮组合已按此环境运行。它不含 ultralytics、matplotlib、anthropic、openai；只有另行启用相应模型或绘图工具时才需要 C 的扩展环境，本次不安装或新增模型功能。
- C 的环境脚本会创建 `.venv`；整合时先执行 C 的环境准备，再在同一环境安装 B 的依赖，确保 Shapely/Pillow 等后端依赖保留。
- `/api/agent/ask` 转发到 `http://localhost:8001/ask`，Agent 不可达返回 502，20 秒超时返回 504，后端继续运行。
- C 指标：读取 `ml/yolo/metrics.json`、`ml/lora/metrics.json`；缺失或无效时对应返回 null。

## 实现范围与假设

`backend/app/config.py` 集中维护仿真、声学、风险、迟滞、主动 ping 和优化参数。10 Hz 墙钟循环按 speed 推进仿真，内部固定 0.1 秒子步；所有随机数来自场景 Generator 及其派生种子。测量不带目标真值 ID。跟踪采用正向方位交会、聚类、三维匀速 Kalman 和马氏距离最近邻关联；船舶 AIS 仅用于合作识别。方案按预测路径缓冲、泊位保留率、延误船时和残余风险排序。灾害覆盖按浮标扫描圆与分区交叠面积累积，通过 clear 航道图 BFS 计算可复航路线。

数据是人工构造的洛杉矶港区域示意几何和虚构船期，尚未按实际海图核验水陆、码头和浮标位置；详见 [数据说明](../data/README.md)。算法、声学参数和“节省小时”都是任务书指定的演示假设。A 与 C 模板服务的基础闭环已验证；训练模型效果、A 的两项缺口和现场验收仍以最终报告为准。

## Git 合入

后端实现已通过 PR #2 由仓库方合入 main；`codex/harborguard-backend-mvp` 的 PR #3 保留交接材料。最终候选分支为 `codex/harborguard-live-integration`，基于 main（5817b9c）纳入 B 交接提交和 C 分支（78d3957）的原始提交。A/C 源码及冻结契约不由本轮改写，main 不直接开发或自动合并。

队友检查顺序：契约和样例 → 全量 B/C 测试（同盘临时目录）→ 操作单启动与五分钟彩排 → A 两处缺口修复 → C/维护者审查合入路径。集成分支按授权通过 tankewudi/harborguard 的 Fork 创建面向 main 的 Draft，说明与既有 PR #3/#4 的依赖；不自动合并。
