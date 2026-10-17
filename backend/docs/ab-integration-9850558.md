# A/B/C 真实浏览器联调记录（2026-10-17）

结论：核心 Security → 模板建议 → 人工批准/驳回，以及 Recovery → 复航计划 → 碎片 PNG、JSONL 回放均可运行。**尚不能宣布最终集成全部通过**：实际浏览器复现了 A 的恢复竞态；冻结契约仍不能查询 500 条窗口以外的建议/决策。没有修改 frontend/、agent/、ml/ 或 shared/，没有 Push、更新 PR 或 Merge main。

本记录限定为本机集成检查，不替代原始 B0–B7 逐项验收、真实识别验收或三人现场彩排。

## 1. 固定版本与隔离方式

| 模块 | 本次实际测试版本 |
| --- | --- |
| B 后端 | `04de0fe7abb9eb52ba7ae806beb30131d4b04a8e` |
| A，PR #7 分支 | `98505588c643d55174acf399bb597ca8c9260ec0` |
| C，已验证模板基线 | `78d39574266b01a582b0626c17021181749271c8` |
| 本地测试合并提交 | `1269f3eea1c47a19a6c94ab56699322a62282f98` |

主工作区仍是纯 B 分支 `codex/harborguard-backend-tick-performance`。测试位于独立工作区 `C:\Users\Administrator\.codex\worktrees\harborguard-ab-integration\marine`，分支 `codex/harborguard-ab-integration-9850558`。从 B 分别合入上述固定 C/A 提交，没有合并冲突。逐目录 `git diff --exit-code` 确认 frontend 与 A 完全一致，backend/shared 与 B 完全一致，agent/ml/tests 与固定 C 完全一致。新报告只写在 B 主工作区。

启动真实 B（8003）、固定模板 C（8001）、生产构建前端（5173）；测试用透明 HTTP/WS 转发器占用 8000。浏览器连接 8000，C 直接连接 8003。转发器只控制传输故障/延迟，不生成业务数据，不修改消息内容。测试使用单独 SQLite 文件，未读取或覆盖已有演示数据库。

## 2. 已执行及结果

| 检查 | 结果 | 实测证据 |
| --- | --- | --- |
| 前端依赖、构建、lint、A1–A6 | PASS | `npm ci`、`npm run build`、`npm run lint`、六个 `check:a*` 全部成功；3D chunk 988.95 KB 有体积警告 |
| B + C 联合测试 | PASS（有跳过项） | `120 passed, 2 skipped`，66.77 秒；跳过项需 YOLO 权重 |
| Windows 默认跨盘临时目录 | FAIL，工具环境限制 | 首轮 117 通过、3 失败、2 跳过；C 的 `ml/sonar/gen_dataset.py:59` 在 D: 临时目录相对 C: 仓库调用 `relpath` 失败。改用新建同盘 `--basetemp` 后联合测试通过，没有改 C 代码 |
| 真实 Security 升级 | PASS | DEBUG_TRUTH_TRACKS=0，10×；首个三级警报在仿真 t=483.1 秒，约 49 秒墙钟量级；两轮实际 C 建议均产生，Agent processed=2/submitted=2/errors=0 |
| 浏览器 WS 真断开及补偿 | PASS（窗口以内） | 只关闭浏览器 WS，C/B 继续运行；恢复后显示三级警报、4 个方案、唯一一张对应模板建议及 `QA_WS_OFFLINE_MARKER_01` 日志；未把 network_down 当作 WS 断开 |
| 批准及刷新恢复 | PASS（窗口以内） | A1/opt-1 的 approve decision seq=1035；对应 5 个分区 restricted；页面刷新恢复模板建议、操作员及“已批准” |
| 批准后同库重启 | PASS（窗口以内） | seq 1174 → 1255，仿真时刻不变，paused=true，除 seq 外状态一致，事件列表一致；页面确认记录保留 |
| 决策写入失败 | PASS | 仅在可丢弃测试数据库加失败触发器；A11 驳回 HTTP 503，零新 decision、零 restricted 分区；页面显示失败、按钮可重试，没有误报成功；触发器已移除 |
| 驳回、刷新、同库重启 | PASS（窗口以内） | 重试返回 200；A11/opt-1 的 reject decision seq=1887，零 restricted 分区；页面刷新及第二次 B 重启后仍显示“已驳回” |
| 超过 500 条事件的边界 | 公开恢复受限 | 注入 520 条日志后 GET /api/events 返回 500 条，seq=2018..2542，严格排序且唯一；旧 decision 返回 0 条；DB 保留 647 条事件及 approve/reject 两条决策。刷新后无权威旧审批可展示，没有从文本日志伪造结果 |
| REST 恢复与实时消息并发 | **FAIL，A 责任** | 方案 GET 延迟 3 秒，在 log GET 完成后发送新日志；恢复前可见，恢复完成后消失，并误报序列回退；DB 中日志仍在，见下节 |
| 真实 Recovery 展示 | PASS，演示数据 | t=107 秒暂停；B4/B7 离线、8/10 在线；复航计划给出 channel_entrance/channel_main_s、berth_container_1，4 个 blocked、2 个 unsurveyed；9 小时为固定演示假设下的计算值 |
| 无 track_id 的碎片入口 | PASS，stub | det-11..det-14 的 track_id 均为空；四个前端入口逐个打开，全部 PNG 实际解码为 640×640，HTTP 200；页面标明合成示意，未请求空航迹详情 |
| 2D/3D、目标选择与相机 | Smoke PASS | Recovery 和 Security 回放可切换；T60 在 3D 下拉选中、跟随/水下视角可操作，回到 2D 保留目标；截图有实际渲染。Canvas 内的隐藏回退文本也进入 AX 树，但其 isVisible=false，不能据此误判 WebGL 失败 |
| 两份 B 录制 JSONL | PASS，回放冒烟 | replay_a.jsonl 跳到仿真 20:00，replay_b.jsonl 跳到 10:00；业务 POST 按钮禁用；46.16 秒观察区间转发器记录的后端 POST=0；回放碎片图从 /replay_assets/b/det-1.png 加载 |
| Agent 问答代理 | PASS，模板事实回答 | POST /api/agent/ask 返回 model=template；当前固定 C 基线不处理 Recovery 的 reopen_plan 事件，所以灾害模式 Agent 建议卡待命，不能冒充已具备灾害 Agent 建议 |
| WS 短采样 | PASS，范围有限 | 暂停的 Recovery，10.11 秒收到 52 个 state（含连接初始快照），观测 5.07 Hz；平均间隔 197.12 ms、最大 223.73 ms，最大状态包 1845 bytes，seq 严格递增；不是运行中 10× 或耐久测试 |

上述浏览器操作是真实本地单机集成；没有 A/C 操作员在场，不能称为三人现场验收。页面帧率提示没有作为正式 FPS 基准；本次视口约 893×759，不能沿用 A 先前 1920×1080 的 FPS 数据。

### 六类故障反馈

| 操作 | 页面实际可见反馈 | 从操作开始到确认可见的上界 |
| --- | --- | --- |
| buoy_down B1 | 离线标识、7/10、恢复按钮 | 383 ms |
| buoy_up B1 | 8/10、在线状态 | 382 ms |
| network_down | 外网离线，同时仍为 LIVE；本地岸线降级 | 383 ms |
| network_up | 断外网开关复位 | 378 ms |
| noise_down | 结构化 log 事件对应的故障注入日志 | 214 ms |
| noise_up | 结构化 log 事件对应的故障注入日志 | 192 ms |

前四项从真实 UI 操作开始计时；噪声没有前端注入按钮，使用既有 REST 注入后观察真实页面日志，未添加前端控件。测量包含命令/观察开销，均小于 3 秒。噪声检查只证明日志反馈及时，不证明 UI 有噪声数值展示或本次已重新评估定位精度。没有断开电脑 Wi-Fi，没有验证 LoRa/ESP32。

## 3. 可直接转给 A 的修复建议

**P1：保持当前契约，修复异步恢复覆盖实时消息和错误重启提示。**

位置：`frontend/src/store/useHarbor.ts:108` 的 `recoverLiveState`，以及 `frontend/src/data/ws.ts:39`、`frontend/src/data/liveRecovery.ts:6`。

复现步骤：真实场景 A 到三级警报后暂停；让 `/api/options/{alert_id}` 响应延迟 3 秒；刷新页面；在 `/api/log` GET 返回后、options GET 完成前，通过正常 POST /api/log 写一条唯一标记。当前页面先出现该日志，恢复结束后日志消失，同时出现“后端事件序列回退”。本次 log GET 完成于 wall=1792233734.488，标记注入于 1792233734.639，首个 options GET 完成于 1792233737.483。归档中仍有 `QA_RESTORE_RACE_MARKER_02`，证明后端没有丢掉该事件。

原因：首次连接时传入的 previousSnapshotSeq 为 undefined，函数内 `?? state.latest?.seq` 会改用**等待 REST 期间已经前进的**实时 seq，再与最初 snapshot 比较，误判重启。误判后丢弃 state.events；最后的 `logs: logs.length ? [...logs].reverse() ...` 还会直接用较早 REST 结果覆盖刚收到的日志。即使仅修复 seq 判断，日志覆盖点仍需单独修复。

建议：显式区分“连接前没有旧快照”与“有旧快照”，只用连接前捕获的序列判断回退；恢复提交时保留等待期间已经收到的较新状态/事件。按事件 seq/稳定业务 ID 合并、排序、去重，日志快照不得覆盖更新的结构化 log 事件。不要解析日志文字推断批准/驳回，也不要为解决 UI 竞态新增共享字段。

补两个 A 回归用例：① 初次连接后延迟详情，同时收到较新 state，不误报重启；② REST log 已返回、详情未返回期间收到新 log，恢复后仍保留该日志且不重复。另保留真正 seq 回退、重置场景、断线重复补偿的现有测试。普通路径测试全绿不足以覆盖此并发窗口。

**P2：窄屏 3D 信息层拥挤。** 当前 893×759 视口里 DEM 来源长文本与图层控件覆盖大量场景。建议折叠详细元数据并约束信息层高度/滚动；在目标 1920×1080 投影设备复测，保持来源和演示水位标注。3D chunk 体积及 THREE.Clock 弃用警告可后续处理。

**A 暂时无需新增分页或日志解析。** 继续消费既有 decision 的 approve/reject；窗口内已能真实恢复。历史超过 500 条时保留不完整/无法确认提示。分页接口仍待负责人批准后由 B 实施，不能先做成已可用。

## 4. B/C 与负责人待办

- B：现有持久化、结构化拒绝、重启恢复、失败回滚在本次浏览器路径没有发现需要修改后端源码的新问题。严格每 tick <20ms 仍沿用性能报告的 FAIL，不能用本次短 WS 样本推翻；继续见 `performance-followup.md`。
- 负责人：如要求恢复任意较早建议/审批，需要批准已有历史查询契约变更提案，详见 `history-handoff.md`。当前 DB 有归档，但既有 events 语义明确是最近 500 条，没有分页/total/截断字段，也没有建议/决策详情接口。本次没有新增任何接口、字段或枚举。
- C：当前模板仅处理 Security options_ready；如需 Recovery Agent 建议，需在独立 C 版本实现并验收既有 recommendation 契约的灾害分支，不直接替换本次模板基线。跨盘数据集工具应修复或文档明确同盘临时目录；真实识别权重/输出仍待验证。
- A：按上节修复竞态后提供新 SHA，再重复真实浏览器测试。目标投影设备、真实断网及现场联合彩排仍待做。

## 5. 标准三服务启动与演示

以下命令在**已包含上述 A/B/C 版本的集成 checkout**运行，纯 B 分支本身不包含 A/C 源码。需要 Python 3.11+、Node/npm；模板基线不要求模型密钥、Ollama 或 GPU。已准备的环境用三个终端：

```powershell
# 终端一，仓库根目录；单 worker，固定数据库路径，重启不删除 DB
$env:DEBUG_TRUTH_TRACKS = '0'
$env:HARBORGUARD_DB = Join-Path $PWD 'backend/runtime/demo.sqlite3'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# 终端二，仓库根目录；固定 C 模板提交
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
$env:AGENT_HOST = '127.0.0.1'
$env:AGENT_PORT = '8001'
.\.venv\Scripts\python.exe -m agent.main
```

```powershell
# 终端三；dist 已经构建时直接 preview，修改前端后重新 build
Set-Location frontend
npm.cmd run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

首次安装/构建另算：仓库根目录 `./dev.ps1 setup`，然后 frontend 下 `npm.cmd ci`、`npm.cmd run build`。本次复用了已准备的 Python 环境，没有重新进行从零安装或严格五分钟启动计时验收。端口 8000/8001/5173 必须空闲；CORS 允许 localhost/127.0.0.1 的 5173。测试转发器不是 Demo 必需依赖，正常展示直接运行以上三服务。

五分钟内可展示：

1. 0:00–1:15：打开 http://127.0.0.1:5173/，确认 LIVE；点击场景 A、10×。观察一级→二级→三级，约 49 秒墙钟量级出现模板建议。
2. 1:15–2:00：暂停，解释证据/方案对比，批准；核对受限分区。刷新查看权威记录；A 修复竞态前，若出现错误重启提示，应说明缺陷，不把它当作真实数据库丢失。
3. 2:00–2:40：切 3D，选择目标，展示水上/水下和跟随；明确区域 DEM 非港池精测、水面非实时潮位。
4. 2:40–3:50：点击场景 B、10×，展示 4 个碎片入口、PNG 合成标签、勘测/可复航/封闭状态和浮标故障。固定 C 没有灾害 Agent 建议，不承诺该卡出现自动建议。
5. 3:50–4:40：进入 `?replay=replay_b.jsonl` 或 `?replay=replay_a.jsonl`，跳转回放、展示只读和本地图片。网络不好时保留本地岸线简图与回放，不宣传已验证真实 Wi-Fi 离线能力。
6. 4:40–5:00：说明人工审批、合成识别、500 条窗口与待验收项目。

## 6. 证据与合并判断

可提交的摘要证据：`backend/docs/evidence/ab-integration-9850558.json`。本机原始 HTTP/服务日志、独立数据库、截图、故障控制文件在主工作区忽略目录 `artifacts/ab-integration-9850558/`，不是部署依赖，不提交数据库或缓存。注入数据库失败的 QA 触发器已移除，PRAGMA quick_check=ok，服务健康检查 200，仿真最终暂停、网络/噪声恢复正常。

**B 代码可供团队评审和整合；测试分支无合并冲突不等于整个项目已验收。** 建议 A 修复恢复竞态并复测后再决定最终合并。没有自动 Merge main，没有替换 C 模板，也没有修改 A 的远程分支。本次仅增加 B 的报告和证据摘要。
