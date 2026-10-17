# B 持久化与恢复验证记录

日期：2026-10-17。基线 `main@5817b9c`；分支 `codex/harborguard-backend-history`。
本报告验证本次 B 修改，不替代 B0–B7 全量验收、PR #6/#7 合并验收或 C 模板 Agent 验收。

## 依据核对

- 原始 B 任务书 B5 写的是“approve 发 decision/zone_changed，reject 只写日志”；原实现与此一致，A 的反馈属实。
- 共享契约 v1 已有 `decision` 事件 `{alert_id, option_id, action, operator}`，decision 请求允许 approve/reject，Python EVENT_DATA 使用同一 DecisionRequest。
- 项目负责人最新指令要求在已有定义允许时补齐结构化 reject。本次沿用原事件/字段/枚举，没有修改共享文件或新增类型。
- 原来 seq、500 条事件、建议、日志、审批限制、详情及 PNG 全在内存，进程重启丢失；原来没有审批详情/建议列表接口。
- `/events` 缓存/过滤语义维持最近 500 个事件中 seq>N 的部分；不是“从最旧记录开始取 500 条”。日志仍是最近 1000 条、新在前，重置/新场景清当前日志。

## 实现与一致性

| 内容 | 实现位置 | 结果 |
| --- | --- | --- |
| SQLite WAL + FULL、单写者文件锁、迁移版本 | app/storage.py、migrations/001_history.sql | 已实现/已测试 |
| 持久化全部已接受事件、建议、每次 decision、最后 decision 投影 | storage.py、engine.py `_history_objects` | 已实现/已测试；窗口外仅内部存档可读 |
| 运行态、RNG、Kalman、计数、分区限制及日志 checkpoint | app/checkpoint.py、engine.py | 已实现/已测试；重启安全暂停 |
| 当前对象优先、已知历史详情/PNG 回退 | api/rest.py、engine.py `detail/image` | 已实现/已测试；历史详情不是活跃对象或审批状态 |
| 提交事务后才广播/返回成功，失败回滚状态/seq/日志/事件 | engine.py `durable`、bus.py、main.py 503 handler | 已实现/真实 SQLite 失败注入通过 |
| reject 发布既有 decision，保留原日志与不改变区域的行为 | decision/__init__.py | 已实现/已测试 |
| 全历史分页查询 | 未实现 | PENDING：冻结契约不允许，需评审新接口 |
| A PR #7 浏览器接入本次 B 版本 | 未执行 | PENDING：A 最新 Fetch 为 456b808，本次没有修改或混入 frontend/ |

持久化内容不采用 pickle，JSON 恢复只允许指定的仿真/跟踪对象；静态几何和分类器按现有代码初始化，PNG 单独存储，避免重复编码图像。
存储故障不静默切回内存；不兼容/损坏数据库拒绝启动。内存写入缓存仅保留当前工作集，不把全部历史对象积累到内存。数据库文件被忽略，不进入 Git。

## 已执行测试

首次原有测试：`python -m pytest backend/tests -q`，73 PASS。
最终全量回归：**88 PASS，61.61s**（原有 73 项 + 新增 15 项）。
静态检查：`python -m ruff check backend/app backend/tools backend/tests`，PASS。
一个 Starlette/httpx TestClient 弃用警告，未为消除警告更换团队依赖。

新增测试位于 `backend/tests/test_history.py`，覆盖：

- approve/reject 各自落库、REST/WS 结构化事件、重启后 state/详情/PNG/日志/建议恢复，序列包含 state 的高水位。
- 526 个持久事件后，REST 精确返回最后 500 条；建议/决策已离开公开窗口但内部记录仍在。
- SQLite trigger 实际中断 decision 事件插入、recommendation 投影写入、runtime checkpoint 更新：HTTP 503，内存和磁盘不留下半次操作，不广播成功事件。
- reset 后保留历史详情，旧警报操作返回 409；alert/detection 计数跨重启递增，旧 PNG 不被新识别覆盖。
- 两个场景 checkpoint 后继续运行，与不中断的真实声学/Kalman 路径比较 state、日志、RNG、PNG，结果一致。
- 损坏数据库、未知 schema、不匹配指纹、第二写者拒绝；21 REST 操作及 state 字段/decision 枚举未扩展。
- 交付给 A 的真实响应 fixture 全部通过冻结模型校验。
- 实时循环遭遇 SQLite 写入失败仍可查询，health=503、仿真暂停；排除故障后 reset 可恢复。可选内部观察者失败不会撤销已提交事务；离线录制器输出失败仍抛出异常，避免假报录制成功。

## 真实 Uvicorn 进程验证（不是浏览器联调）

命令：`python -m backend.tools.history_smoke --directory artifacts/history-live-20261017-1 --port 8004`。
工具使用新的独立数据库，真实 HTTP/WS 与进程终止/重启，无 DEBUG_TRUTH_TRACKS，没有调用 C Agent。
recommendation 是工具明确标注的 template fixture；识别输出全部标为 stub。

| 项目 | 实测 | 结论 |
| --- | --- | --- |
| 总耗时 | 63.126s | PASS |
| 三次预装依赖后服务启动 | 1.586 / 1.544 / 1.544s | PASS；不是从零安装或全套 A/B/C 启动 |
| Security L1 | 仿真 t=38.0，墙钟 3.752s | PASS |
| Security L2 | 仿真 t=150.7，墙钟 15.109s | PASS |
| Security L3 / options | 仿真 t=483.1，墙钟 48.385s | PASS；A 的 t=90 观察不足以判定无法升级 |
| state 频率 | 5.004Hz | PASS，本次约 48s Security 区间 |
| 最大实收状态包 | 25,381 bytes | PASS，<50,000；不是所有场景长时上界 |
| 驳回事件 | seq=303, t=485.0, action=reject | PASS，完整 fixture 已提交 |
| 批准事件 | seq=305, t=485.0, action=approve | PASS，限制区域改变 |
| 强制终止后的恢复 | t、alerts、zones、详情及事件一致，seq 不回退，paused=true | PASS |
| 加 520 条日志后内部事件 | 587 条 | PASS，包含先前建议及两次决策 |
| 同时公开 `/events` | 最近 500 条，首条 overflow-20 | PASS，原语义；旧 decision 无法通过 v1 再取到 |
| 第二次终止重启 | 同样 500 条事件恢复 | PASS |
| Recovery 空 track_id PNG | 4 条，逐张 HTTP 200 + PNG 签名 | PASS 后端传输；真实识别 PENDING |

原始完整产物在本机忽略目录 `artifacts/history-live-20261017-1/`：report、数据库、server 日志及前后事件 JSON。
可复核小型样例提交在 `backend/fixtures/history/`；数据库、日志、缓存、密钥均不提交。

## FAIL / PENDING 和实际边界

1. **PENDING，阻塞“全历史刷新恢复”验收**：窗口外数据虽已持久化，现有 v1 没有公开读取方式。不能把这项写为通过，也不能让 A 从自由文本日志反推。最小 v1.1 提案见 history-handoff.md，尚未实现。
2. **FAIL，严格每 tick <20ms**：本次 10× 真实服务日志含 260 次 >20ms 警告，最大已记录 135.0ms，统计包含 checkpoint/SQLite，未关真实检测或更换算法。日志只包含超限样本，不能推导平均值/P95。回归测试同时在运行，不把这当独占性能基准；5Hz 短期已通过，仍须独占环境性能和新版本 20 分钟耐久复验。
3. **PENDING，真实前后端/Agent**：未将本次 B 版本与 PR #7（A 最新分支 456b808）或 PR #6 的 C 模板服务合在一起运行，不能宣布浏览器刷新/断线恢复已验收。没有采用 C 的新云端版本。
4. **PENDING，外部能力**：真实模型、真实声呐、测深/潮位、目标投影电脑和三人现场彩排未在本次验证。stub PNG 和单机后端脚本不替代这些验收。
5. **边界**：v1 没有审批终态/幂等键、全局跨场景 Track ID、换数据库标识。按原限制，reject 不撤销早先 approve；不要引入 UI 自动重试或从历史详情创建当前可审批对象。
6. **部署边界**：必须同一路径、单 worker、可写本地磁盘；演示前保留 DB，不能用换库来掩盖失败。首次安装依赖用时和 wheel 分发未测；本次用已准备依赖从 repo 启动。

## 合入准备

本分支只包含 B 的改动。A/C 不需要被合并进该分支，可由负责人后续把 B 提交 cherry-pick 到独立 A/B/C 集成分支，保留已验证模板 Agent，再跑浏览器联调。
不改 main、不 Force Push、不修改队友远程分支。当前没有 Push 或创建/更新 PR 的动作；需用户看过改动和测试结果后再确认。
