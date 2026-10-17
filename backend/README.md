# HarborGuard 后端与算法

面向洛杉矶港水下安防与灾后分区复航的黑客松演示后端。一个 Python 进程完成可复现仿真、被动声学观测、定位跟踪、风险警报、声呐识别适配和方案计算。操作员审批后才改变安防限制状态。

开发依据是任务书 B。对外字段以 [共享契约 v1](../shared/contract.md) 为准；[TypeScript 类型原文](../shared/types.ts)、[状态样例](../shared/sample_state.json) 和 [全部事件样例](../shared/sample_events.json) 可直接交给 A、C 对接。

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
| Ollama | C | `ollama serve`，11434；模型名由 C 确定 |

整套演示启动顺序：Ollama → 后端 → Agent → 前端。当前已有 C0 初始化骨架；A 前端以及 C 的渲染器、检测器和 Agent 服务实现尚未就绪。其实现完成后补齐准确入口与构建命令，再进行全员彩排。

- A：订阅 `/ws`。`state` 是 5 Hz 完整快照，`event` 实时发送。CORS 允许 localhost 和 127.0.0.1 的 5173。重连后读取初始快照并用 `/api/events?since_seq=N` 补事件，缓存仅最近 500 条；若断线过久需重新建立本地视图。后端主动断开过慢客户端，避免堵塞仿真。
- C 声呐：提供 `ml/sonar/render.py:render_ping` 和 `ml/yolo/infer.py:SonarDetector`，返回任务书约定的灰度图和像素角点框，权重 `ml/yolo/weights/best.pt`。从仓库根目录启动，模块可直接导入。
- 灾害碎片本身不发声，没有被动航迹时，其 Detection 的 `track_id` 为契约允许的空字符串；前端按 Detection ID 展示声呐图，不查询空航迹 ID。
- C Agent：订阅警报和方案；从 REST 获取细节，将完整 Recommendation POST 到 `/api/recommendations`。结构或引用 ID 非法返回 422。后端校验、保存最新建议并广播，不代为审批。
- `/api/agent/ask` 转发到 `http://localhost:8001/ask`，Agent 不可达返回 502，20 秒超时返回 504，后端继续运行。
- C 指标：读取 `ml/yolo/metrics.json`、`ml/lora/metrics.json`；缺失或无效时对应返回 null。

## 实现范围与假设

`backend/app/config.py` 集中维护仿真、声学、风险、迟滞、主动 ping 和优化参数。10 Hz 墙钟循环按 speed 推进仿真，内部固定 0.1 秒子步；所有随机数来自场景 Generator 及其派生种子。测量不带目标真值 ID。跟踪采用正向方位交会、聚类、三维匀速 Kalman 和马氏距离最近邻关联；船舶 AIS 仅用于合作识别。方案按预测路径缓冲、泊位保留率、延误船时和残余风险排序。灾害覆盖按浮标扫描圆与分区交叠面积累积，通过 clear 航道图 BFS 计算可复航路线。

数据是人工构造的洛杉矶港区域示意几何和虚构船期，尚未按实际海图核验水陆、码头和浮标位置；详见 [数据说明](../data/README.md)。算法、声学参数和“节省小时”都是任务书指定的演示假设。C 模型效果和 A 界面联调需在队友代码合入后验证。

## Git 合入

当前开发分支为 `codex/harborguard-backend-mvp`，不直接修改 main。分支现已基于 GitHub 仓库 ChrisJiang123/harborguard 的 origin/main（b8d418d）整合，C 原有源码、依赖文件、脚本及共享契约均保留。尚未执行 push 或创建 PR。

队友检查顺序：契约和样例 → `make test` → 启动后端接前端 → 接入 C 声呐和 Agent → 播放两份回放 → 实际地图核验 → 三人演示彩排。当前分支已与 origin/main 具有共同历史。获得你的确认后，可推送此分支并创建面向 main 的 PR；合并前再次获取远程更新，保留 A、C 的后续实现。
