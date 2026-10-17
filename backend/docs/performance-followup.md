# B 性能改进与新版耐久验证

日期：2026-10-17。基线是已推送的 `d223b15`（history 分支）；改进保存在独立本地分支 `codex/harborguard-backend-tick-performance`。
范围仅 B 的后端、测试、诊断工具和文档。共享契约、数据坐标、配置参数、frontend/、agent/、ml/ 均未修改。
本次没有实现尚待批准的历史分页接口，没有替换团队模板 Agent，也没有执行远程 Push 或 Merge。

## 结论范围

已降低快照和事务处理开销；**严格“每 tick <20ms”仍 FAIL**，不能用平均值小于 20ms 替代每次都达标。
最新全量回归 92 PASS（58.77s），Ruff PASS。完整 A/B 场景的公开消息、最终 seq 和全部 PNG 字节与 d223b15 完全一致。
旧数据库兼容验证通过；生产代码提交为 `d9a2e89`，新版后端20分钟真实服务耐久通过，详见下节。
这些结果不代表最新 A/C 浏览器联调、三人彩排、真实模型/海况或硬件离线验收。

## 先定位，再修改

基线使用真实 SQLite 文件、`synchronous=FULL`、正常声学/Kalman 路径，10× 无墙钟跑完整 A=1200s、B=600s。
这约 37 秒的离线基准不是 20 分钟耐久，也不证明网络 5Hz。
分别计时外层 `game.step()`、内部算法总耗时、state 发布、checkpoint capture、SQLite commit，以及 classifier（含 PNG）。
另在 A 的 t490–510 做 cProfile：重复 deepcopy/capture、通用 checkpoint 编码和已计算后被丢弃的 tracks 快照为可安全减少的开销；profile 本身有额外开销，不用其时间代替无 profiler 基准。

实际修改：

1. checkpoint 在事务前仍深拷贝，保证失败回滚；事务后同步编码时直接借用字段，避免第二次完整深拷贝。编码器优先处理占多数的普通数字/list/dict，存储格式保持原样。
2. 每次世界变更仍原子写入完整 checkpoint。仅发布 state 时，用单独事务持久化新 seq，不重写未改变的 checkpoint；SQL 比较旧 seq，成功后才广播，不提前预留序列。
3. state 在复制前截取最多 60 个历史点；REST 仍提供完整历史。对快照的修改不会污染引擎。
4. Tracker.update 保留原默认返回行为；引擎使用内部可选参数，跳过紧接着会重新生成的那份航迹快照。关联循环中重复 cue 计数移到每条航迹一次。
5. 首见时间只在新航迹时扫描历史，避免 `setdefault` 默认表达式每个子步都求值。风险公式、关联逻辑、随机数调用和检测结果不变。

代码：`app/checkpoint.py`、`app/storage.py`、`app/engine.py`、`app/perception/tracker.py`、`app/decision/risk.py`。

## 最终基准与改进前对照

环境：本机 Windows、Python 3.11.17、预装依赖；两次基准顺序执行，没有同时运行其他验证服务。
计时均包含同步调用的完整工作，outer tick 包含 checkpoint 和 SQLite 提交；state 发布另列。
P95 使用排序样本的 `floor(0.95*n)` 项。不是跨机器性能保证。

| 指标，10× | d223b15 | 改进后 | 判断 |
| --- | ---: | ---: | --- |
| A 外层 tick 平均 | 23.1807ms | 19.6448ms | 减少 15.25% |
| A 外层 tick P95 | 31.5246ms | 27.0585ms | 改善，仍超限 |
| A 外层 tick 最大 | 76.3968ms | 61.0667ms | 严格20ms仍 FAIL |
| A >20ms 次数 /1200 | 865 | 446 | 减少，未清零 |
| A 纯算法平均 / 最大 | 13.2952 / 52.6367ms | 13.0000 / 47.4786ms | 包含识别；不是单个0.1s子步 |
| A state 发布平均 | 10.5526ms | 1.6111ms | 减少 84.73% |
| A state 发布 P95 | 17.1986ms | 2.0130ms | 改善 |
| A classifier+PNG 最大 | 32.1670ms | 34.1279ms | 没有优化/关闭该流程，仍有峰值 |
| B 外层 tick 平均 / 最大 | 2.6358 / 115.3724ms | 2.2322 / 113.8246ms | 首个集中识别 tick 仍超限 |
| B >20ms 次数 /600 | 1 | 1 | 严格20ms仍 FAIL |
| B state 发布平均 | 1.9430ms | 0.6778ms | 改善 |

时间口径：10Hz 外层实时 tick 在10×下推进1仿真秒，包含10个0.1s仿真子步；这里没有把外层耗时除以10后当作达标。
PNG 和纯算法计时是有包含关系的分项，不能相加后再重复计入总耗时。
本轮未单独输出每个0.1s子步的最大值/P95，不能据此宣布子步严格达标。

首轮仅减少复制和 state 重写时，A 平均21.0677ms、state平均1.5618ms；随后调整编码器分派，得到上述最终值。
各轮后执行回归：原有88项全过；新增4项后最终92项全过。没有为减少耗时关闭数据库 FULL 同步、声学定位、主动检测或修改检测频率。
继续移走同步图像生成会涉及任务调度/图像可用时序，当前先保留稳定语义，未实施未经验证的异步图像改造。

原始可审查指标及 PNG 哈希：`evidence/ticks-before.json`、`evidence/ticks-after.json`。
初始基准数据库文件大小在 WAL checkpoint 前取样，不适合比较磁盘大小，因此交付指标中删除该字段，保留原始运行产物供复核。

复现当前版本：

```powershell
.\.venv\Scripts\python.exe -m backend.tools.benchmark_ticks --directory artifacts/ticks-new --speed 10
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tools backend/tests
```

基准工具可在旧版本上使用同一脚本（旧 Store 没有 commit_sequence 时自动略过该分项）。每次必须使用新目录；不会覆盖 Demo 数据库。

## 可复现性与事务边界

完整公开消息 SHA256（包括 state/event 和 seq，按固定 tick 节奏发布）：

| 场景 | 修改前与修改后共同哈希 |
| --- | --- |
| A | `fadb098fa451ae9cbf497d0660a5fa109a2267849d164db43e7587a7bc50d3a0` |
| B | `7192f62a4c60073e77373af0dd10d09504c5e1815e851f9d2ac077e2e6f2085b` |

A 14 张、B 4 张 PNG 的每个 SHA256 均相同。final seq 分别712/334，没有通过减少事件或推送次数节省计算。
模型标签仍为 stub，本轮没有取得真实识别精度证据。

新增 `tests/test_tick_optimizations.py` 4项验证：

- SQLite trigger 禁止重写 checkpoint，20次 state 发布仍成功；重启后的 state 和序列完整恢复。
- seq 写入失败时不广播、不推进游标；排除故障后紧接原序列发布。
- seq 比较不一致时拒绝覆盖，不隐藏第二写者/内部状态不一致。
- 5000点航迹的 state 只含最后60点，REST仍5000点；修改返回快照不改变引擎数据。

原有人工审批/建议失败回滚、重启、超过500条缓存窗口、RNG/Kalman继续运行等88项仍通过。
所有公开世界变更仍通过引擎事务完成；B 调试工具若直接修改内部属性，需显式调用 `game.save()`，不能用 state 发布代替变更提交。

旧版数据库兼容性另用 `d223b15` 真实运行产物的副本验证：604条存档事件、2条决策、4张当前PNG都保持；seq904→906后再重启读取正常。
没有修改配置指纹或内部schema版本；不需要删库或迁移。原库未改动。

## 新版20分钟真实服务耐久

状态：**PASS，限本次B服务、合成场景及已测环境**；严格20ms仍FAIL。

| 项目 | 实测 |
| --- | --- |
| 真实墙钟时长 | 1200.08s |
| WS 收到状态/事件 | 6001 / 1139 |
| 平均 state 频率 | 5.000Hz |
| 最大实收 state | 26,618 bytes，<50,000 |
| 场景启动/结束事件（数据库核对） | 13 / 13（7次A、6次B） |
| HTTP/WS检查错误、服务ERROR/Traceback | 0 / 0 |
| 单核CPU，39个约30s采样窗口 | 平均15.751%，最大24.0% |
| 服务及Python子进程合计RSS | 94.89–104.14MB，随场景波动，切换后多次回落约96MB，未见持续累积 |
| 落库事件 | 1142，含建连前3条；公开窗口仍500 |
| 数据库 quick_check | ok |
| 结束后重启 | checkpoint时间一致、paused=true、seq7146继续递增、旧det-1 PNG哈希不变 |
| >20ms日志 / 最大记录tick | 3424条 / 120.8ms，FAIL |

CPU是30s窗口占用率，不是瞬时峰值保证；内存结论仅覆盖这20分钟，不能证明无限时无泄漏。
此真实运行启用故障注入，不能把日志条数与无注入的离线基准直接相比。
原始产物在忽略目录，随文可复核指标为 `evidence/soak-history.json`。
本轮数据库约111.5MiB，历史事件和PNG持续存档，不自动清理。若要长期运行，保留/清理策略需另行确认，不能通过删历史来满足资源指标；数据库未纳入Git。

```powershell
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'artifacts/B-soak-history-new/history.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.\.venv\Scripts\python.exe -m backend.tools.soak --seconds 1200 --port 8005 --report artifacts/B-soak-history-new/report.json
```

使用独立新目录和空闲端口；现有 soak 工具读取 HARBORGUARD_DB，必须显式隔离，避免向操作员的 Demo 数据库写入测试数据。
本轮目录为 `artifacts/B-soak-history-20261017/`，工具持续读真实 WS、调用 REST、校验PNG、循环A/B、注入及恢复六类故障，每30秒采样该服务及其 Python 子进程的 CPU/RSS。
本次只启动B，不包含C模板 Agent、前端浏览器、真实Wi-Fi断开或现场三人彩排。

## 优化后真实进程重启与审批回归

独立执行 `python -m backend.tools.history_smoke --directory artifacts/history-live-tick-performance-20261017 --port 8004`，60.157s完成，PASS。
三次已装依赖的启动为1.576/1.551/1.541s；真实L1/L2/L3墙钟3.720/15.069/48.339s，state约5.009Hz。
recommendation为测试工具明确标注的template fixture，不是C Agent输出。
实际reject/approve后终止服务进程，再启动：建议及两个decision事件、详情、限制状态一致，seq不回退；补520条日志后再终止重启，接口仍只返回最后500条，内部587条记录中保留旧建议/决策。
Recovery四条空track_id的PNG逐张HTTP200并验证签名，仍标stub。
小型报告在 `evidence/history-smoke-performance.json`，完整数据库/日志/请求JSON在上述本地忽略目录。

## 合入准备与剩余事项

只读 `git merge-tree` 对固定模板集成分支 `fork/codex/harborguard-live-integration@5af2ae0` 和本地生产提交 `d9a2e89` 预检：后端生产代码没有文本冲突，**backend/README.md 有内容冲突**。
没有实际合入、没有改写工作区A/C源码。后续在团队集成分支由B人工保留双方最新启动/模板说明，不能用整份 ours/theirs 覆盖；文本预检不等于最新版A/C真实联调。

仍待完成：严格20ms、完整历史分页契约审批、最新A/C组合的刷新/重连/重启浏览器回归、三人现场彩排与队友从零启动。
本轮20分钟通过仅补充新版B耐久证据，不把整个B0–B7或项目题目验收改写为全部通过。
