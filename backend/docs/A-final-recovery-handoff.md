# 给A：最终main恢复问题复现与最小修复建议

当前版本：main `a841bf9a70d8bf8237b9e03763852a34bed10368`，含A #7/#11/#15。当前精确源码R1–R4函数复现均FAIL；R1/R3已在最新main真实浏览器复测，R2在e1候选沿用同一A源码真实复测。下述早期四项完整浏览器证据来自5a68，相关三份恢复源码至a841未变；R4没有重跑最新main完整延迟浏览器测试。B未改frontend或冻结契约，也未将此文自动发到队友PR。

最新补测：a841实时同文日志2条→刷新1条；日志GET503仍无恢复失败提示。e1候选t632的两次reject seq1158/1201分别为Operator A/QA_CURRENT_2，UI仍为前者，B两条持久化且无封区。

**B另有独立问题：main几何未变时指标更新不广播。B已修在e1候选（237 PASS/2 SKIP），不需要A用轮询掩盖；仍需A单独解决旧REST覆盖新WS的R4。B修复尚未推送或合入main。**

## R1：合法同文日志丢失（P1）

在暂停/结束的场景B，连续两次POST `/api/log`：`{"level":"info","source":"operator","text":"QA_FINAL_SAME_TEXT_SAME_TIME"}`。B返回成功，持久化seq1495/1496，两条t均600；GET日志也有2条。页面实时2条，刷新后1条。

修复`frontend/src/store/useHarbor.ts`的`mergeRecoveredLogs`：带身份的log事件按现有seq去重，两个不同seq即使内容相同也保留。无ID REST日志保留重复次数，不能用内容Set或简单max计数假装完全可判重。500窗口以外身份无法唯一确定，继续诚实降级，不新增共享字段。

## R2：新操作员事件被当成重复（P1）

同一暂停时刻t685，A13/opt-1先有reject seq4201、operator=`Operator A`，后有合法reject seq4366、operator=`QA_SECOND_OPERATOR`。B两条均存在，分区无restricted；页面实时仍显示Operator A，刷新才显示QA_SECOND_OPERATOR。

修复`eventIdentity`和decision投影：以事件seq辨识记录，为每alert保存前端内部最后decision seq；旧补偿不能覆盖新结果。同一seq重发只应用一次，不要仅把operator拼到内容key。reset/真正seq回退按已有session/generation清理。reject不表示撤销过去的approve。

## R3：日志GET失败未提示（P1）

隔离QA代理只将现有GET `/api/log?limit=200`返回503，其余B响应和WS保持真实。刷新后页面LIVE、实时数据正常，但无日志恢复失败/partial提示。当前`liveRecovery.ts`只把eventsResult失败传给RecoveryMeta，logsResult失败变成空数组；函数复现得到phase=complete。

在前端内部meta加入日志请求成功信息或单独错误类别；logs失败至少partial并给重试入口，events失败/两类皆失败分别提示。保留实时WS，不把错误当作“原本无历史”。不自动重试审批。

## R4：旧REST方案覆盖新WS方案（P1，已真实复现）

1. Security10×到t655并暂停，A13方案残余风险15%。刷新使恢复读取既有 `/api/options/A13`。
2. QA仅延迟该恢复请求的**原始旧响应6秒**，没有改字段、标签或事件；普通面板详情读取不延迟。
3. 旧响应捕获后resume真实B；3秒后t685，B自然发布`options_ready` seq4178，残余风险20%，opt-2封区/限速集合也变化；随后暂停。
4. 新WS先到；真实C提交“残余风险0.20”的Template建议。旧REST返回后，页面表格却变15%，Agent卡仍20%。截图和原始两版方案保留。

修复`recoverLiveState`末尾options spread，以及`cacheOptions`/详情写入路径：为每alert保留前端内部options事件seq及请求发起时session/generation/序列边界。有请求期间的新事件时保留新完整方案；没有新事件时用REST补缺。不能无条件反转spread，因为新REST也可能比旧缓存新。旧选中option不存在时清理选择，地图预览与表格使用同一集合。共享REST无版本字段，不声称任意时序都可绝对排序。

部分延迟时序会因8秒客户端超时或后续请求读到新版而碰巧通过；这不能覆盖上述失败。补回归必须覆盖“恢复详情已读到旧payload、新WS先到、旧payload成功返回”的顺序。

## 其他交付项

- 最新故障补测B10恢复online后，最近浮标异常建议仍显示故障时“离线3个”的快照；当前state实际8/10在线。建议A/C明确显示建议的时效/历史属性，或由C在恢复后重新生成准确上下文；不新增共享撤回事件、不从日志推当前审批。这是非阻塞快照限制，不属于B方案广播补丁。

- `demo_a.jsonl`、`demo_b.jsonl`、`demo_full.jsonl`的Recommendation.summary超过60字符，B Pydantic拒绝。修短数据并加长度断言；不放宽契约。旧`replay_a/replay_b`合法但stub，不能当最新模型证据。
- 当前内嵌浏览器出现“3D rendering is unavailable in this browser”。请在实际录制/投影电脑查WebGL与试播；本轮不归因为B接口。当前3D chunk 1,003.10kB为非阻塞警告。
- 新录制回放尾时刻60251.812ms，range的step=100导致End停60200ms，少放最后约52ms；点Play后正确结束。P2建议提供“跳到结尾”显式seek(duration)或修正键盘End处理，不改合法JSONL时间戳来掩盖问题。
- 本轮回放出现过Z1…Z10回退，已查明为QA服务器GeoJSON MIME错误，纠正成`application/geo+json`后12分区匹配，**不列为A生产Bug**。
- B已导出本轮实际A/B/C流与原PNG的独立回放包（maina841，yolo26n/template），未写入frontend。A可在审阅manifest后决定如何提供正式静态资源。

修复限frontend，不改shared、B数据库或C路由。保留已通过的seq连接基线、AbortController、session/generation和500窗口提示。补R1–R4边界用例后给新SHA；B只复测受影响联调，不把旧报告自动迁移到新SHA。

证据：[最终机器记录](evidence/final-delivery-20261017.json)；本机原始文件在最终隔离工作区`artifacts/final-delivery/browser-r*.json`及PNG。项目负责人可直接转发本文件。
