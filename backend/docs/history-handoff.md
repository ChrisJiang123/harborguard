# 给 A 的历史恢复交接（冻结契约 v1）

日期：2026-10-17。B 分支：`codex/harborguard-backend-history`，基于官方 `main@5817b9c`。
本次只修改 B 的后端、迁移、测试及本文档/样例；没有合入或改写 A/C 的额外提交。
已阅读 A 的 `frontend/B-HANDOFF.md`；收尾 Fetch 时 A 分支由 `8f4a860` 更新到 `456b808`（3D 等高线/标签改动，交接文档未变）。没有在这个 B 分支运行 A 的浏览器验收。
**请先由负责人把 B 的提交带入团队联调分支；本文不表示远程服务已经部署。**

## 可以直接转发给 A

1. B 已补齐同一份冻结 `decision` 事件的 `action: "reject"`。批准、驳回、建议均先写 SQLite，再返回 `{"ok":true}` 和广播；写入失败返回 503。请先验证 #7 已有 decision handler 是否直接生效，再决定是否需要前端修改。
2. 请以结构化 decision 为审批记录来源，按 `seq` 排序/去重；建议使用 `recommendation.id`，卡片关联 `alert_id`、`option_id`。不要解析 `/api/log` 猜状态，不要只因为 POST 发出就显示成功。503/网络失败时重新查询确认，不自动重复批准。
3. 使用同一数据库重启后，事件序列继续递增，最近 500 个事件、当前状态、详情、PNG 和最近日志可恢复。恢复的仿真处于暂停状态，需要操作员点“恢复”；无需因为普通重连清空历史。保留你已有的序列回退保护，供换库/旧版本兜底。
4. **超过 500 条的分页历史 API 尚未获批，也没有实现。** 请继续保留“历史可能不完整/状态无法确认”，不要移除降级显示，也不要提前接入下文提案地址。刚好 500 条并不等于一定截断；状态快照的 seq 间隔也不能证明漏事件。
5. `Alert` 仍没有审批状态字段；不要从 `options_ready`、详情 HTTP 200 或分区状态反推“已批准/已驳回”。详情可能是最后已知历史对象，当前是否活跃以最新 `/api/state` 为准。驳回不撤销先前已批准的限制，限制按原规则保持至重置/新场景。
6. 场景 A 的 10× 真实后端实测：L1 约 3.8 秒、L2 约 15.1 秒、L3/options 约 48.4 秒。`t=90` 是仿真时间，尚未到二级，请给场景约 50–60 秒墙钟；使用实际返回的警报和方案 ID，不硬编码 `A1/T1`。
7. Recovery 中空 `track_id` 的碎片按 Detection ID 请求详情和 `image_url`，不调用空航迹接口。4 条记录的 PNG 已通过后端验证；本次 `model:"stub"`，不能作为真实模型验收。
8. 请在团队联调分支做批准/驳回后刷新、WS 断线重连、B 重启、500 条窗口外降级的浏览器回归。DEM、潮位、3D 新效果与本次后端交接无关，继续由 A 按原计划处理。本报告不把接口测试当作前后端真实联调通过。

## 启动（仓库根目录）

需要 Python 3.11+，使用团队已经准备的 `.venv`、`requirements-lock.txt` 运行依赖；新增 SQLite 属于 Python 标准库，无需数据库服务或额外 pip 包。

```powershell
# 仅首次安装/更新依赖时执行；不算预装依赖后的启动时间
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .

# 实际启动，默认持久化 backend/runtime/harborguard.sqlite3
$env:DEBUG_TRUTH_TRACKS = '0'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

可在启动前设置 `$env:HARBORGUARD_DB='C:\HarborGuardData\demo.sqlite3'`。
请每次使用同一个绝对路径；相对路径相对于启动目录。不要用 `:memory:` 做真实持久化演示。
只用一个 worker，不使用 `--reload` 验证连续运行；第二个进程使用同一文件会明确拒绝启动。
首次建库自动执行 `backend/migrations/001_history.sql`，版本是内部存储版本，不是 API 版本。
配置、场景数据或 checkpoint 格式不兼容会拒绝恢复，不会静默丢弃历史；需要 B 审查迁移。
不要删库“修复”。备份请停服务后复制数据库及尚存的 `-wal`、`-shm` 文件，或用 SQLite backup。
该启动方式使用仓库 checkout/可编辑安装；未验收独立 wheel 的分发部署。

地址：REST `http://127.0.0.1:8000/api`；WS `ws://127.0.0.1:8000/ws`；OpenAPI `/docs`。
CORS 仍只允许 `http://localhost:5173`、`http://127.0.0.1:5173`。
C Agent 仍独立监听 8001，B 不会在本分支替换模板 Agent，也不启动云路由。

```powershell
$api = 'http://127.0.0.1:8000/api'
Invoke-RestMethod "$api/health"
Invoke-RestMethod -Method Post "$api/scenario/a/start" -ContentType application/json -Body '{"speed":10}'
# 等待实际 L3/options 后，用真实 ID 提交；下面 A1/opt-1 仅为本次 fixture
Invoke-RestMethod -Method Post "$api/decision" -ContentType application/json -Body '{"alert_id":"A1","option_id":"opt-1","action":"reject","operator":"demo"}'
Invoke-RestMethod "$api/events?since_seq=0"
Invoke-RestMethod -Method Post "$api/control" -ContentType application/json -Body '{"action":"pause"}'
# 重启恢复会暂停；已有场景未结束时可调用 resume
Invoke-RestMethod -Method Post "$api/control" -ContentType application/json -Body '{"action":"resume"}'
```

## 现有 21 个 REST 操作（未增加接口）

完整字段仍以 `shared/contract.md`、`shared/types.ts`、`backend/app/models.py` 为准。
以下响应类型均可在 `/docs` 展开；完整实际 JSON 见 `backend/fixtures/history/`。

| 方法/路径（统一 `/api` 前缀） | 参数或请求体 | 成功响应/限制 |
| --- | --- | --- |
| GET `/health` | 无 | `{"ok":true}`；运行/存储错误 503 |
| GET `/state` | 无 | 完整 `StateMsg`；不含建议/决策字段 |
| GET `/events` | `since_seq=0`，非负 | `EventMsg[]`，最近 500 个事件中 seq>N 的部分，升序；不是分页 |
| GET `/zones` | 无 | `ZoneCollection` GeoJSON，含当前 state/coverage |
| GET `/assets` | 无 | `Asset[]` |
| GET `/buoys` | 无 | `Buoy[]` |
| GET `/tracks/{track_id}` | ID | `Track`，当前优先、否则最后已知存档；T ID 可跨场景复用 |
| GET `/alerts/{alert_id}` | ID | `Alert`，当前优先、否则最后已知存档；没有审批状态字段 |
| GET `/detections/{det_id}` | ID | `Detection`，包含原 model 和 image_url |
| GET `/options/{alert_id}` | ID | `{"alert_id":...,"options":[...],"ranked":[...]}`，可读最后已知存档 |
| GET `/sonar/{det_id}.png` | ID | `image/png`，当前内存未命中读持久化 PNG |
| GET `/log` | `limit=100`，1–1000 | `LogEntry[]`，新在前，当前场景日志缓存；无审批语义、无分页 |
| GET `/metrics` | 无 | `{"yolo":null,"lora":null}` 或相应指标 |
| POST `/scenario/{id}/start` | id=a/b，`{"speed":10}` 可省略 | `{"ok":true}`，新场景清当前对象但不删历史 |
| POST `/control` | `{"action":"pause"}` / resume / reset；speed 需 value | `{"ok":true}`；无可恢复场景时 resume=409 |
| POST `/mode` | `{"mode":"security"}` / disaster | `{"ok":true}` |
| POST `/inject` | `{"type":"buoy_down","target":"B4"}` | `{"ok":true}`；还有 buoy_up/network_down/network_up/noise_up/noise_down |
| POST `/decision` | alert_id, option_id, action=approve/reject, operator | `{"ok":true}`，成功前原子落库；非活跃 L3/无方案=409 |
| POST `/recommendations` | 完整 `Recommendation` | `{"ok":true}`，结构/当前引用不合法=422 |
| POST `/log` | `{"level":"info","source":"operator","text":"说明"}` | `{"ok":true}` |
| POST `/agent/ask` | `{"question":"目前风险？","track_id":null}` | `{"answer":...,"model":...}`；Agent 不可用=502、20s 超时=504 |

详情未知 ID 仍返回 404。历史详情不等于活跃对象：对已重置/解除的旧警报提交 decision 仍返回 409。
`/log` 的最近 1000 条上限、场景重置清当前日志的行为不变；数据库事件归档保留旧日志事件，但 v1 无法逐页查询。
同一数据库中 alert/detection 计数跨重启递增；`Track.id` 仍按原规则在新场景从 T1 开始，不承诺跨场景全局唯一。
旧版本运行在内存、未写数据库的历史无法事后自动补回。

## WebSocket 与恢复顺序

浏览器可直接 `new WebSocket('ws://127.0.0.1:8000/ws')`。服务端单向推送，连接时立即发送完整 state，之后 state 约 5Hz；事件提交成功后发送。
state 和 event 共享递增 seq，**事件之间的 seq 不保证连续**；仿真 `t` 在新场景会归零，不能用于历史排序。
事件使用现有信封，例如此次真实 HTTP 产生的驳回：

```json
{"type":"event","seq":303,"t":485.0,"event":"decision","data":{"alert_id":"A1","option_id":"opt-1","action":"reject","operator":"history-smoke"}}
```

批准同结构，`action:"approve"`；建议为 `{"event":"recommendation","data":{"recommendation":{...}}}`，完整样例在 fixture。
不新增 decision_id、status、session_id、拒绝原因或枚举；EventMsg.seq 是同一数据库内稳定的事件标识。

建议 A 使用以下恢复顺序（可先验证 #7 现有实现，无需重复开发）：

1. 先连 WS，保存初始完整 state，并缓冲随后收到的实时消息。
2. 并行读取 `/api/events?since_seq=最后实际处理的事件seq`（首次刷新=0）和 `/api/log?limit=1000`。不要把快照 seq 直接当成“历史已读取”的游标。
3. 将 REST 和缓冲区事件按 seq 去重、升序处理；事件历史中的旧 alert/zone 变化不能覆盖较新的完整 state。活跃态按最新 state，审批/建议卡片按结构化事件。
4. 场景变化按 scenario_changed 的 seq 分隔；不要把旧场景 `t=500` 的事件排在新场景 `t=0` 之后。日志列表按接口约定展示；日志缺少稳定 ID，不从文本构造决策。
5. 在最近窗口中未找到某条 decision 时继续显示无法确认；不等于待审批。即使详情可读取，也不能恢复其审批结果。窗口恰为 500 时只能提示“可能不完整”，无总数/截断标志时无法证明全量。
6. 较慢客户端仍可能被 1013 关闭；重连后重复上述补偿。普通服务重启同库不回退 seq；若换库/回退备份导致序列倒退，沿用 #7 的清理/提示保护。

v1 还没有审批幂等键/终态流转定义。同一警报多次合法提交会产生多个 decision，按 seq 记录各次操作；reject 不是撤销 approve 的指令。前端应避免自动重试业务操作。

## 可复现样例与后端验证

`backend/fixtures/history/` 来自真实 B 服务的 HTTP 响应：

- `state-before-restart.json`：包含真实声学/Kalman 场景的 T3、L3 警报和批准后区域状态。
- `events-before-overflow.json`：包含 recommendation、reject、approve 及其他事件；每个都通过 v1 Pydantic 校验。
- `recommendation.json`：B 验证工具构造并 POST 的 template fixture，**并非调用 C Agent 的输出**。
- `decision-reject.json` / `decision-approve.json`：请求样例，ID 只对这个 fixture 有效。
- `det-6.json`：Recovery 无被动航迹碎片样例；图片 URL 仅在对应数据存在的后端有效，JSON 不包含 PNG。

重新生成带真实 PNG 的数据及报告（使用一个尚不存在数据库的新目录，端口必须空闲）：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m backend.tools.history_smoke --directory artifacts/history-new-run --port 8004
```

工具只操作自己启动的服务，使用独立 SQLite 文件，约 60–70 秒完成 Security→驳回→批准→强制终止重启→520 条追加→再重启→Recovery PNG。
产出 `report.json`、实际请求/事件/状态 JSON、数据库及服务日志；它不是前端回归，也不是三人现场彩排。

## 待负责人确认：最小契约变更提案（未实现）

原因：现有 `/events` 固定最近 500 条，无分页、截断标志；`/state` 和详情没有建议/审批历史列表，不能通过现有接口读取所有落库记录。
建议在团队同意后以 **v1.1 新增独立 GET `/api/history/events`**，保留所有 v1 路径/字段/缓存语义：

```text
请求：after_seq=0（>=0），limit=200（1..500），through_seq 可省略
首次请求由服务器固定 through_seq=当前全局seq；后续页必须带回同一值。
查询：after_seq < event.seq <= through_seq，按 seq 升序取 limit 条。
响应：{items: EventMsg[], next_seq: number, through_seq: number, has_more: boolean}
has_more=true 时 next_seq=本页末条event.seq；false 时 next_seq=through_seq。
```

只复用原 EventMsg 和既有 action 枚举，无新增审批状态、session 字段或总数要求。稳定高水位防止分页时混入无限增长的实时尾部。
A 的最小改动：分页到 `has_more=false`，按现有 seq/id 去重，随后合并 WS 缓冲中 seq>through_seq 的事件；保留初始 state 作为当前态，历史回放只恢复卡片。
同库持久化 seq 已解决普通重启回退，暂不增加启动标识。换库/恢复旧备份仍需显式重置客户端；未来若要求自动识别任意换库，再单独评审数据集标识。
**当前实现没有这个接口，未改 `shared/contract.md`、`shared/types.ts` 或 models.py。待负责人及团队确认后 B 实施，A 才接入。**
