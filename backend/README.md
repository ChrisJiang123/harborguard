# HarborGuard 后端与算法

面向洛杉矶港水下安防与灾后分区复航的黑客松演示后端。一个 Python 进程完成可复现仿真、被动声学观测、定位跟踪、风险警报、声呐识别适配和方案计算。操作员审批后才改变安防限制状态。

开发依据是任务书 B。对外字段以 [共享契约 v1](../shared/contract.md) 为准；[TypeScript 类型原文](../shared/types.ts)、[状态样例](../shared/sample_state.json) 和 [全部事件样例](../shared/sample_events.json) 可直接交给 A、C 对接。

2026-10-17 持久化更新：见 [给 A 的恢复交接](docs/history-handoff.md) 和 [B 验证记录](docs/history-verification.md)。下文保留初始 MVP 背景；关于重启、驳回和历史范围请以本次交接为准。

声呐安全修复与新 C 候选验证见 [本轮验收及启动说明](docs/sonar-safety-integration.md)。新算法参数改变内部检查点指纹：保留原演示数据库，为新版设置独立的 `HARBORGUARD_DB`（例如 `backend/runtime/sonar-safety.sqlite3`）；不要删除旧库或强行加载旧配置检查点。没有引入 C 的分支仍明确使用 stub，不能按真实识别宣传。

后续本地性能改进与新版耐久结果见 [性能跟进报告](docs/performance-followup.md)。严格每 tick <20ms 尚未通过，不把平均耗时改善算作全部验收通过。

本次新增文件见 [文件清单](../docs/files.md)，逐项验收范围见 [任务书验收范围](../docs/acceptance.md)。

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

若 PowerShell 的脚本执行策略阻止本地脚本，可直接执行 `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`。若安装了 uv，也可用 `uv venv --seed --python 3.11 .venv` 建立环境。

后端健康检查：`http://localhost:8000/api/health`；交互式接口文档：`http://localhost:8000/docs`；WebSocket：`ws://localhost:8000/ws`。首次启动为空闲；同库重启会恢复并暂停已有场景。默认数据库 `backend/runtime/harborguard.sqlite3`，可用 `HARBORGUARD_DB` 指定固定路径。自动迁移，无需外部数据库。使用单个 worker，同文件的第二写者会拒绝启动。

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
2. 将真实返回的 `alert_id`、`option_id` 与 `action: "approve"`、`operator: "demo"` POST 到 `/api/decision`，对应分区才成为 `restricted`。`approve` 和 `reject` 都先持久化并发布原契约的 `decision` 事件，保留 operator 日志；写入失败返回 503。`reject` 不改变分区，批准的限制保持到重置。
3. POST `/api/inject`，例如 `{"type":"buoy_down","target":"B4"}`、`{"type":"network_down"}`、`{"type":"noise_up"}`；分别用 `buoy_up`、`network_up`、`noise_down` 恢复。噪声注入是幂等开关，不会反复叠加。
4. POST `/api/scenario/b/start`，观察灾害覆盖、`blocked`、`clear`、`unsurveyed` 和 `reopen_plan`。B4、B7 在仿真 60 秒失效。
5. POST `/api/control`，内容 `{"action":"reset"}`，清除当前航迹、警报、识别、建议、限制、故障并回到空闲状态；已落库历史保留。消息 seq 和警报/识别 ID 在同一数据库中跨重启递增，避免旧审批误命中新场景。历史详情不是当前活跃对象，不能用于批准旧警报。

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

A 的回放器按 `wall_ms` 依次分发完整 `state` 和 `event`，无需后端。部署时连同 `replay_assets/` 复制。回放格式与实时信封一致；main 已有 A 的回放 UI，与最新 PR #7 和本次 B 持久化的浏览器联合验收仍待执行。

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
| Ollama | C | 不属于本次 B 持久化的启动依赖；本次不接入新模型路由 |

整套演示启动顺序：后端 → 团队已验证的模板 Agent → 前端。此纯 B 分支基于 main，包含 A6 前端与 C0 骨架，不带入 PR #6/#7 的额外 A/C 提交；团队集成分支需保留已验证的 C 模板基线。下列 C0 说明是早期交接背景，不表示已验收最新 C 服务。本次没有运行 Agent 或浏览器联合验收。

- A：订阅 `/ws`。`state` 是 5 Hz 完整快照，`event` 实时发送。CORS 允许 localhost 和 127.0.0.1 的 5173。重连先缓冲实时消息，再用 `/api/events?since_seq=N` 补事件并按 seq 去重；接口仍只查最近 500 条，不能全历史分页。同库重启序列继续增长且仿真安全暂停；若换库/回退导致 seq 小于旧值，应清理游标并提示历史不确定。详细恢复顺序及尚未批准的分页提案见本次交接。后端主动断开过慢客户端，避免堵塞仿真。
- C 声呐：提供 `ml/sonar/render.py:render_ping` 和 `ml/yolo/infer.py:SonarDetector`，返回任务书约定的灰度图和像素角点框，权重 `ml/yolo/weights/best.pt`。从仓库根目录启动，模块可直接导入。
- 灾害碎片本身不发声，没有被动航迹时，其 Detection 的 `track_id` 为契约允许的空字符串；前端按 Detection ID 展示声呐图，不查询空航迹 ID。
- 实时 Detection 的 image_url 是后端相对路径，前端按 `http://localhost:8000` 解析；离线回放里的静态图片路径按前端自身站点解析。
- C Agent：订阅警报和方案；从 REST 获取细节，将完整 Recommendation POST 到 `/api/recommendations`。结构或引用 ID 非法返回 422。后端校验、保存最新建议并广播，不代为审批。
- C0 的 BACKEND_BASE_URL 为后端根地址，REST 客户端需补 `/api`，WS 使用 `/ws`。C 当前本地模型超时预算为 30 秒，而本契约代理超时为 20 秒；C3 实现问答时应把响应总预算控制在 20 秒以内，或自行快速降级，避免代理先返回 504。
- C 与 B 的依赖声明范围兼容；当前锁文件覆盖 B 运行与测试，不含 C 的 ultralytics、matplotlib、anthropic、openai。完整联调时还需安装 C 的 requirements-runtime.txt，并重新检查依赖和模型加载。B 所需 Shapely/Pillow 已在 B 的依赖中。
- C 的环境脚本会创建 `.venv`；整合时先执行 C 的环境准备，再在同一环境安装 B 的依赖，确保 Shapely/Pillow 等后端依赖保留。
- `/api/agent/ask` 转发到 `http://localhost:8001/ask`，Agent 不可达返回 502，20 秒超时返回 504，后端继续运行。
- C 指标：读取 `ml/yolo/metrics.json`、`ml/lora/metrics.json`；缺失或无效时对应返回 null。

## 实现范围与假设

`backend/app/config.py` 集中维护仿真、声学、风险、迟滞、主动 ping 和优化参数。10 Hz 墙钟循环按 speed 推进仿真，内部固定 0.1 秒子步；所有随机数来自场景 Generator 及其派生种子。测量不带目标真值 ID。跟踪采用正向方位交会、聚类、三维匀速 Kalman 和马氏距离最近邻关联；船舶 AIS 仅用于合作识别。方案按预测路径缓冲、泊位保留率、延误船时和残余风险排序。灾害覆盖按浮标扫描圆与分区交叠面积累积，通过 clear 航道图 BFS 计算可复航路线。

数据是人工构造的洛杉矶港区域示意几何和虚构船期，尚未按实际海图核验水陆、码头和浮标位置；详见 [数据说明](../data/README.md)。算法、声学参数和“节省小时”都是任务书指定的演示假设。C 模型效果和 A 界面联调需在队友代码合入后验证。

## Git 合入

当前持久化开发分支为 `codex/harborguard-backend-history`，从官方 `origin/main@5817b9c` 创建；只增加 B 的后端/迁移/测试/交接文件，不混入队友分支提交。共享契约与 A/C 源码保留。此次没有 Push 或创建/更新 PR。

队友检查顺序：恢复交接和样例 → `make test` → 将 B 提交带入独立集成分支（保留已验证模板 Agent）→ 最新 PR #7 浏览器回归 → 回放和现场彩排。新分页接口需先确认契约提案；Push 新修复分支和更新 PR 也需负责人确认，不能直接 Merge main。
