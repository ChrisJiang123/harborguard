# PR #7 恢复修复的真实浏览器复测

日期：2026-10-17；自动跟进任务 `harborguard-pr7`。

**结论：原来的日志覆盖和假重启提示已修复；常规单操作员 Demo 闭环可运行。最终恢复验收仍有两项 A 侧去重问题未通过，不能把 PR #7 标成全部通过。** 本轮没有修改 A/C 生产源码、B 算法、冻结接口或数据库迁移，没有 Push、更新 PR 或 Merge main。20ms 继续作为尽力优化目标。

## 固定版本与环境

| 项目 | 本轮精确版本 |
| --- | --- |
| A / PR #7 | `dc69ad28ac37e8d0592d9271f9d61e28c79ff27c` |
| B 生产代码 | `04de0fe7abb9eb52ba7ae806beb30131d4b04a8e` |
| C 模板 | `78d39574266b01a582b0626c17021181749271c8` |
| 本地候选合并提交 | `b48cac76e301a047afa330bced2eae6e388d534c` |

在新建的 managed worktree 中从上轮固定三方基线合入 A 修复，合并无冲突。逐目录核对：frontend 与 dc69ad2 一致，backend/shared 与 B04de0fe 一致，agent/ml/tests 与 C78d3957 一致。没有采用 C 的新模型路由。后续新增的 3 条 B 测试单独在 B 主工作区验证，不冒充候选原有测试。

原演示 `5173 → QA8000 → B8003/C8001` 的 checkout、进程和数据库保留。候选独立使用 QA `5174 → B8004/C8006` 和新 SQLite 文件；生产构建使用已支持的 `VITE_API_BASE=/api`、`VITE_WS_URL=ws://127.0.0.1:5174/ws`。QA 服务负责静态文件及透明 HTTP/WS 转发，并可延迟响应/断开 WS。仅 QA 启动器将 B 的 Agent 路由指向独立 C8006，不修改磁盘源码或消息格式。没有改 B 的 CORS 配置，也不把这个同源代理构型当作新增 5174 跨域许可的验证。

## 已执行的检查

| 用例 | 结果 | 实际证据 |
| --- | --- | --- |
| 前端构建、lint、A1–A6、新增 check:recovery | PASS | npm ci 安装 119 packages，0 vulnerabilities；build/lint/七项检查成功；3D chunk 995.19KB 仍有体积警告 |
| 现有 B+C 联合 pytest | PASS，有跳过项 | 同盘临时目录，120 passed、2 skipped，68.57 秒。权重相关跳过项不算真实模型验收 |
| B 历史专项回归 | PASS | 新增 3 条边界测试，整个 test_history.py 18 passed，5.07 秒；Ruff PASS。fixture 测试不等于浏览器实景 |
| 首次刷新假序列回退 | PASS | 新 origin 的首次连接和多次普通刷新都未误报回退 |
| 恢复期间真正收到 C 新建议 | PASS | 在 A t=479、尚未三级时暂停；延迟已读取的 events 响应 5 秒，再恢复仿真。真正 C 模板产生 rec-d89ea3415187，恢复完成后仍显示对应 A1 的模板卡、4 个方案、唯一的新日志，无假重启提示 |
| 上次竞态精确复现 | PASS | options 的旧响应延迟 3 秒，在 log GET 已结束后新增 QA_PREVIOUS_RACE_EXACT_REPRO_02；恢复后该日志为 1 条，前一个实时标记也保留，已驳回状态正确，无 loading 残留/假重启 |
| 驳回落库失败 | PASS | 在独立 QA DB 上加失败 trigger，真实页面点击驳回返回 503，decision=0、restricted=0，页面显示失败并允许重试；trigger 移除后重试成功 |
| 页面驳回及刷新 | PASS | A1/opt-1，操作员 A，t=484，decision seq=887；刷新后已驳回和模板建议恢复 |
| 真实 WS 断开补偿 | PASS | 代理实际关闭浏览器 WS，页面 DISCONNECTED，B/C 不停；离线期间写三条有序日志，并由另一个 REST 客户端人工批准 A1；重连后 LIVE、QA_REMOTE 审批与 5 个 restricted 分区一致，日志各 1 条、显示顺序 3/2/1（界面最新优先） |
| 同库后端重启 | PASS | seq1421→1519，除 seq 外状态相同、事件列表相同，paused=true，页面保留已批准；不是换库测试 |
| UI 人工批准及刷新 | PASS | 第二次完整真实 A 场景，C 产生 rec-e3714ebee774；页面批准 A11/opt-1，operator=操作员 A、t486、decision seq3064；五个受限分区与页面确认一致，刷新仍确认 |
| 同刻合法重复日志 | **FAIL，A** | B 的两条同 t/text 日志 seq143/144 都存在；页面实时显示 2 条，刷新后只剩 1 条 |
| 同刻另一操作员的新 decision | **FAIL，A** | B 已发布 A1/opt-1 approve，operator=QA_REMOTE_2、seq1520、t484；实时卡片仍显示 QA_REMOTE，而日志已经显示 QA_REMOTE_2；刷新后才恢复 QA_REMOTE_2 |
| 500 条窗口诚实降级 | PASS，能力受限 | 注入 520 条日志后 GET events=500、旧 decision=0，归档当时保留 596 events/3 decisions；页面提示 500 条缓存上限及历史无法确认，无假重启、无伪造已批准。不是完整历史查询通过 |
| Recovery 基本回归 | PASS，合成演示 | t208 暂停，B4/B7 离线，复航计划/4 blocked/2 unsurveyed/9 小时假设值可见，无旧 A 审批串场景 |
| 无 track_id 碎片图 | PASS，stub | det-6..det-9 均 track_id=""，四个入口逐张打开，浏览器实际解码 640×640，src 为既有 /api/sonar/...，合成标签存在 |
| 2D/3D | Smoke PASS | 实际截图可见渲染并可返回 2D；没有正式 FPS/目标投影设备验收，信息层遮挡仍存在 |
| 两份 B JSONL 回放 | Smoke PASS | A 跳到仿真 20:00、批准按钮禁用；B 跳到 10:00、有 4 个碎片；只读状态、不连接后端；本地图 /replay_assets/b/det-1.png 实际 640×640 |
| 真正低 seq 的新会话 | PASS，范围明确 | A11 已批准，旧 options 响应延迟 5 秒时，刻意换到一个全新 QA DB 并重启 B；新 seq 观察为30、t0、scenario=null。UI 正确提示回退，旧 A11/批准均清除，延迟结果没有复活旧审批；旧 DB 的 4 条决策仍在。没有把这种人为换库写成普通重启丢历史 |
| 最后短 WS 健康检查 | PASS，范围有限 | 8.14 秒空闲新库样本，排除初始快照 40 帧、4.991Hz、最大间隔216.63ms、最大包1809bytes、seq递增；候选和原稳定服务健康均200。不是10×全负荷或新耐久测试 |

新增 B 测试明确证明：两条相同日志是两个不同 seq 的合法事件；同 t 的同动作可以由两个操作员产生两个合法 decision，重启后均保留、latest_decision 指向后一条。B 没有新增接口或幂等规则来迁就前端的去重假设。

## 可直接发给 A 的两项建议

### R1：日志合并丢失合法重复记录

位置：`frontend/src/store/useHarbor.ts:108` 的 logIdentity、113 行 mergeRecoveredLogs。现在用 `t:level:source:text` 放进 Set，把“同一事件重复投递”和“两个事件恰好文本、时刻相同”合为一类。

复现：暂停/空闲时，连续两次 POST `/api/log`，body 均为：

```json
{"level":"info","source":"operator","text":"QA_DUPLICATE_SAME_TEXT_AND_TIME"}
```

B 的 GET events 返回 seq143、144 两条 log，GET log 也返回两条；页面实时有两条，刷新变一条。来源相同的两条业务日志不能因为 t/text 相同被删掉。

建议：结构化 log 事件以既有 event.seq 区分；无 ID 的 REST 日志快照合并时保留重复记录的多重性，不要一律 Set(text tuple)。为“两次合法同文日志保留两条、同一 event 重复补偿只显示一次”同时补测试。现有契约能表达这个窗口内的区别，不需要 B 新增字段。

### R2：decision 身份忽略 seq/operator，实时审批归属落后

位置：同文件 eventIdentity（95 行，decision 分支），以及 reduceMessage 的重复提前返回（176 行）。当前 key 是 alert/option/action/t，未区分不同操作员的新事件。

复现：同一暂停时刻 A1/opt-1，先 approve/operator=QA_REMOTE，再 approve/operator=QA_REMOTE_2；B 接受并持久化两个不同 seq。后一条为 seq1520、t484。前端运行日志出现第二人，但已批准卡仍是第一人，刷新才变第二人。

建议：decision 没有独立业务记录 ID，应使用持久化 event.seq 去重，配合已经实现的 session/generation 处理真实会话回退；不同 seq 不应仅因动作/仿真时刻相同被忽略。增加“同 t 两个操作员先后决策，卡片立即匹配较新 seq；同一 seq 重发不重复”的测试。保留目前已通过的假重启、generation、延迟请求保护，不回退这次修复。

这两项影响完整恢复/审批审计，列为最终一致性验收待修。标准单操作员、一次决策的五分钟流程本轮已通过；不把边界问题写成整个 Demo 无法启动，也不把它们隐藏为全绿。

## 交接、限制与复测状态

- 机器可读证据：`evidence/pr7-recovery-dc69ad2.json`，包括实际事件/操作员/seq、时间门控及浏览器结果。原始 HTTP 日志、独立 DB、截图在忽略目录 `artifacts/pr7-recovery-dc69ad2/`；不会提交 DB、缓存或源码副本。
- B 新增 3 条回归位于 `backend/tests/test_history.py`，生产代码和 shared 无差异。两份 QA DB 的 quick_check=ok，失败 trigger 已清理。
- C 仍固定模板；识别仍 stub；没有验收真实权重/海况、硬件离线、三人现场彩排、正式 GPU/FPS 或任意较早历史分页。C 的 Recovery 自动建议不在模板基线实现范围。
- GitHub 只读检查发现 main 已包含 PR #8 合并提交 `8a911ae`；这不是本轮操作，本轮没有远程写入或切换/合并 main。候选使用上述固定提交，不借此宣称整个 main 验收通过。
- 同一 `dc69ad2` 的本次测试已完成，不应在后续 heartbeat 重复构建/联调。等待 A 修复 R1/R2 后按新 SHA 重测；若 PR 仅更新无关 3D 内容，不重复发通知。
- 收尾只读复查发现 PR #7 已到 `b549515337e0a50889d331ae397e4f381e4694ca`（界面英文翻译）。与 dc69ad2 比较，eventIdentity、logIdentity、mergeRecoveredLogs 的去重逻辑没有变化；没有为这个无关更新重新跑一轮，也没有将它标为完整浏览器验收通过。本报告的实测版本仍是 dc69ad2。
- 本轮 5174/8004/8006 临时服务及候选页已关闭，临时 worktree 已归档，可从候选提交恢复；原 5173/8003/8001 均再次确认 200。原始 QA 数据库/截图保留在主工作区忽略目录。
