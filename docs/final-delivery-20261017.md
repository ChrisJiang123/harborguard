# HarborGuard 最终集成与交付检查

验收日期：2026-10-17，洛杉矶。截止：22:00 PDT。本轮最终锁定 **main `a841bf9a70d8bf8237b9e03763852a34bed10368`**；最后Fetch仍为该SHA。

**结论：2D核心流程可录制；完整验收未通过，Devpost尚未提交。** 最新main的实际A/B/C浏览器流程耗时 **286.008秒（4分46秒）**。3D在本浏览器不可用；四处A恢复缺陷仍在；另发现B方案更新广播缺陷，已在独立本地分支修好但不在main。

## 版本与环境

| 模块 | 官方合入版本 | 本轮结论 |
| --- | --- | --- |
| A | #7 merge `f93af2c`；后续#11及#15 merge `a841bf9` | 构建、lint、A1–A6通过，2D可演示；R1–R4恢复FAIL，当前浏览器3D不可用 |
| B | #13 merge **`5a68f1204ec064db474e8b6ac9c35f7f041180e5`** | PR13已合并；新main全量测试及真实Recovery通过。方案指标变化未广播另见本地修复 |
| C | #4 merge `782d04d`；C4 #14 merge `99d7091` | 最新C真实订阅/REST提交已测，运行时来源 **template**；本轮cloud/local/LoRA服务验证SKIP |

GitHub重新确认#4/#7/#13/#14/#15均merged；未采用过时冲突#6。精确main的PR触发Actions查询为空，不等于CI通过。仓库已有C团队的合成LoRA评估记录，本轮没有训练、下载、切换或验收该运行时。

独立工作区：`C:UsersAdministrator.codexworktreesharborguard-final-main-latestmarine`，分支`codex/harborguard-final-main-latest`。新SQLite=`artifacts/final-delivery/final-main.sqlite3`。B8020、C8021、QA同源预览5184；`DEBUG_TRUTH_TRACKS=0`，单worker，未绕过数据库指纹。原5173/8000/8001/8003及旧数据库未切换、删除或终止。

Python3.11.17，torch2.14.1+cpu、ultralytics8.4.181、Pydantic2.14.1；Node24.19/npm11.17。复用预装CPU依赖，新工作区前端npm ci约7秒；三服务准备后就绪10.295秒。首次从零安装耗时PENDING。真实声呐权重SHA256=`2cad3146fa4b98516efa0057367c3c5d53220dc2a3246058f5608094a6568839`。

## 最新main的实际测试

| 项目 | 结果 |
| --- | --- |
| `pytest backend/tests tests agent/tests -q` | **232 PASS、0 FAIL、2 SKIP，130.92秒**。未复用旧211结果；两项SKIP缺另一份COCO冒烟权重，交付声呐权重实际运行 |
| Ruff / compileall / pip check | PASS；Ruff检查backend，compileall覆盖backend/agent/ml，依赖一致 |
| 前端 | build 10.035秒；lint、A1–A6、recovery、sonar、english全部PASS。3D懒加载包1003.10kB警告非阻塞 |
| 真实模型离线 | A完整1200仿真秒×3、B完整600秒×3；各场景事件/状态/PNG语义哈希分别一致；没有静默stub降级 |
| REST/WS+C/持久化 | PASS（API层）；实际Approve/Reject、断线补偿、同库后端重启通过；实际model=template |
| 实时指标 | **4.97718Hz**，295个state，最大间隔490.945ms，P99 346.417ms；最大24264B，RSS峰值431.77MiB；CPU单核等效48.77%，16逻辑核整机3.05% |
| 故障注入浏览器 | 浮标down/up反馈314/316ms；模拟network down/up 298/322ms；noise up/down真实REST→WS→界面日志可见。仅仿真故障，不是Wi-Fi、ESP32或LoRa实测；noise三秒时限PENDING |
| 20分钟耐久 | **当前a841 PENDING**。本轮早期5a68已跑1200.61秒、5961帧、4.965Hz、无错误，不能移作新SHA的通过记录 |
| 20ms目标 | 尽力目标，非Demo阻塞；未进行性能重构、关闭检测或篡改耗时 |
| Replay | 历史`replay_a/replay_b`契约/14+4PNG/HTTP通过，但检测为stub；`demo_a/demo_b/demo_full`摘要超60字符，FAIL。新导出本轮a841实流A/B+8PNG，契约和资源通过 |

## Security与Recovery

Security真实航迹/风险、主动Ping、三级警报、`yolo26n`PNG、C模板建议及人工Approve→restricted均在最新浏览器展示。Reject不自动封区的API测试通过，本地修复候选也做了真实浏览器Reject。重置使用新ID并恢复默认状态，API回归通过。**原任务书500仿真秒三级要求仍FAIL：实测505秒；不为凑时限改风险参数。** 当前main后续运行有方案指标广播不一致，故Security不宣称全面通过。

Recovery最新main实跑结果：**6 clear / 3 blocked / 3 unsurveyed**。北锚地blocked，燃料泊位在100%覆盖率仍unsurveyed；0m没有改成30m。BFS仅走`channel_entrance/channel_main_s`，可用泊位`berth_container_1`；9小时按实际状态及每区1.5小时假设计算，不以匹配参考数字为目标。最多3次实际检测/20仿真秒冷却、错类/漏检/低置信/近场/重试耗尽/覆盖跨阈值/多框关联回归通过，真实B三次一致。

**这验证的是合成仿真下的保守策略和演示。匿名接触仍由仿真几何生成，AIS模拟，真实模型有误差；不构成真实海洋检测、全系统真值无关或实际复航许可验收。** 真实测深/潮位、接收端观测、多目标拥挤现场测试另行验收。

## 尚未解决的缺陷及准确证据范围

| 项目 | 结论与复现范围 | 负责人 |
| --- | --- | --- |
| R1 同刻同文日志 | 最新main实际浏览器：实时2条，刷新后1条；B两条均落库。按seq身份保留合法重复，不能内容Set去重 | A |
| R2 多操作员decision | 最新A源码函数FAIL；e1候选沿用同一A，在t632有seq1158/1201两次reject，B持久化正常、前端仍旧Operator A | A |
| R3 日志GET失败 | 最新main实际浏览器只把GET log置503，WS正常，未显示partial/failed；当前函数也FAIL | A |
| R4 旧REST覆盖新WS方案 | 最新main精确源码函数FAIL；前版5a68真实延迟6秒复现15%表格/20%Agent；相关A源码哈希至a841不变。未冒称此次重跑了最新main完整竞态浏览器测试 | A |
| B 方案指标变化未广播 | main完整离线/实际浏览器暴露REST55%、WS/Agent50%；只按几何去重遗漏指标/排序变化。新增5个回归在main均RED；本地修复全GREEN，详见下节 | B |
| 500事件范围 | 合同仍是500窗口，无分页/总数/截断字段。前版5a68真实510事件测试诚实Incomplete history提示PASS；最新API恢复通过。不可宣称全部历史可恢复 | A/B已知契约限制 |
| 3D | a841真实浏览器显示unavailable，回2D可继续；自动A4通过不能替代目标录制电脑GPU渲染/FPS验收 | A/录制者 |

恢复修复详细建议见[给A交接](../backend/docs/A-final-recovery-handoff.md)。本轮不改frontend/、agent/、ml/或冻结契约，不替队友修代码。

故障补测另见非阻塞快照限制：B10恢复online后，最近一条浮标异常建议仍保留故障时“离线3个”的上下文。它是历史建议，不能当作当前浮标状态；C/A应给旧快照明确时效说明或在恢复后更新，不能由B伪造撤回事件。当前state已为B10 online，截图与原事件均保留。

## 已完成但未推送的B修复

独立分支`codex/harborguard-options-publication`，测试源码 **`e1b33055883b6bef8e003fc61a2c9f43178cfac1`**，基于当前a841，原修复提交`fe0681e7be706ba33a39dfc8dd1e8b2589749de1`。生产改动只在`backend/app/decision/__init__.py`，另有5项参数化后端回归。方案完整载荷/排序变化才广播，相同载荷仍去重；不改风险计算、30秒优化周期、人工审批或共享字段。

最新候选 **237 PASS、2 SKIP，152.24秒**；Ruff/compileall/前端build通过。真实B+C+浏览器在t632：REST=options_ready=Agent=UI，风险10%；4.98839Hz，251帧，最大间隔349.02ms，最大25585B。浏览器Reject及第二操作员Reject均持久化、无restricted；A的R2仍FAIL，未被B补丁掩盖。旧fe基线另跑全套真实A/B重复与浏览器Recovery；不能把旧fe的完整浏览器结果自动计到新e1。当前e1没有重新完成全套五分钟浏览器串场。

**未Push、未创建/更新PR、未Merge main。** 建议负责人确认后单独审阅并合入这项B修复，再冻结精确演示SHA；当前main不能被写成已含修复。候选预览`http://127.0.0.1:5182/`，与正式部署隔离。

## Demo及交付决定

最新main的4分46秒是**单机实际A/B/C浏览器2D主流程**：A10×→L3→YOLO PNG→模板→Approve→restricted→3D不可用回2D→B10×600秒→本轮实流Replay。用QA真实REST在t512暂停准备记录；一次PNG语义点击需改用新AX点击、3D降级、Replay End未到最后一帧需点Play。不是三人现场彩排，也不是无重试、完整3D验收。保存截图，**没有录屏成片**。

可以立即准备2D候选录制；正式冻结优先审阅小范围B修复。若视频宣称完整历史一致性，A需先修R1–R4并交新SHA；3D需在录制电脑验证，否则整片用2D并明确范围。Replay标为历史回放；不把旧stub或本轮捕获冒充LIVE，不声称真实复航许可。

| 负责人 | 截止前必须完成 |
| --- | --- |
| B/负责人 | 审阅并决定是否Push/合入已验B修复；锁定最终SHA，新库启动；A若更新仅补受影响联调，不再加功能 |
| A | R1–R4恢复修复和回归；旧demo摘要长度；录制电脑3D不可用则采用2D；不要推断绿色/审批 |
| C | 录制优先保留已验模板；若改cloud/local/LoRA须单独验收，不因合入代码默认服务通过；准确披露合成评估来源 |
| 负责人/录制者 | 录制并试播成片、准备可访问视频URL、核对活动规则/团队/Devpost必填项并在22:00 PDT前亲自提交 |

五分钟操作与准确命令：[demo-runbook](demo-runbook.md)。可供编辑的[Devpost草稿](devpost-submission-draft.md)不等于已满足活动规则或已提交。

本机最新main隔离预览`http://127.0.0.1:5184/`；旧5173仍是旧演示环境。未切换正式部署。最新实流应急回放`http://127.0.0.1:5184/?replay=/final_replays/replay_maina841bf9_b.jsonl`；便携包见`artifacts/final-delivery/HarborGuard-maina841bf9-replays.zip`。不要把QA代理的测试控制接口部署到正式服务。

机器记录：[evidence](../backend/docs/evidence/final-delivery-20261017.json)；实际截图：[Recovery](../backend/docs/evidence/final-maina841bf9-recovery.png)、[YOLO PNG](../backend/docs/evidence/final-maina841bf9-sonar.png)。本机日志/JUnit/原SQLite保留在`artifacts/final-delivery/`，文件哈希在记录内。报告提交不含数据库、模型权重、缓存、日志或凭据。
