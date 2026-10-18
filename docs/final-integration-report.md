# HarborGuard 主线交接资料最终集成检查

后续业务P0补充：[未决观测、投影与真值依赖审计](../backend/docs/survey-p0-audit.md)。本报告的构建/接口/浏览器流程结论不证明实际复航安全；旧12小时结论不得继续展示为可靠结果。

日期：2026-10-17，America/Los_Angeles。基线为官方仓库 main `782d04d61858cca4849f7ff39942394e5b56d1f3`。本次响应负责人“核查旧 #3/#6、整理并重新 Push”的要求，不自动 Merge main、Force Push、关闭旧 PR 或修改 A/C。

**旧的两次 Push 均已在 GitHub，内容并未丢失；但没有进 main，且现在都有 README 冲突。** 后端实现已经由其他 PR 合入，无需重写。需要迁移的是仍缺失的 B 交接工具、OpenAPI、Mock 和操作文档。本分支以当前 main 为基线整理这些内容，避免重合旧候选或沿用过时结论。

## GitHub 实际状态

| PR | 核对结果 | 本次处理 |
| --- | --- | --- |
| [#3](https://github.com/ChrisJiang123/harborguard/pull/3)，head `368df2ede67f2c8e353a628afb1559a95d70cb68` | fork上的Draft，open、未合并，mergeable=false；实际冲突为backend/README.md | 迁移B交接工具/测试/OpenAPI；Mock放B目录，不添加frontend文件 |
| [#6](https://github.com/ChrisJiang123/harborguard/pull/6)，head `5af2ae08d9baf6aa53fe58cacd6552986eed76a2` | fork上的open PR，当前不是Draft，未合并，mergeable=false；实际冲突同为README | 更新集成报告与Demo操作单；旧模板报告/原始JSON完整归档，不重新带入旧C版本 |
| [#10](https://github.com/ChrisJiang123/harborguard/pull/10) | 已由维护者合并，merge `700eb93`，B head `4fb8941` | 声呐保守判定/投影/预热及证据已在main，不重复实现 |
| [#4](https://github.com/ChrisJiang123/harborguard/pull/4) | 已由维护者合并，main顶部merge `782d04d`，C head `6389b705bec35b8fc44018d1c14d770f2a82b364` | 保持C源码和权重原样；新增路由不因合并而自动视为本轮已验收 |
| A #7 / #11 | #7已在历史主线；#11 merge `8ca2eb3`，含NOAA测深和建议浮标布局 | 不修改frontend；运行现有构建和自检，保留现场/浏览器边界 |

本分支为 `codex/harborguard-handoff-refresh`。旧#3/#6未改动、未关闭；负责人审查新PR时可将它作为缺失交接交付物的替代，而不是再把旧#6整套重新合入。最终远程链接及GitHub的mergeable/CI由交付回复报告。

## 旧交付物迁移清单

| 来源 | 当前交付位置 / 更新原因 |
| --- | --- |
| #3 21 REST示例、14事件、数据结构与恢复说明 | [frontend-integration.md](frontend-integration.md)，已修正拒绝事件、持久化序列、旧详情、500窗口和新库说明 |
| #3 OpenAPI | [integration/openapi.json](integration/openapi.json)，由当前真实FastAPI导出，未改API |
| #3 Mock | [backend/fixtures/integration/backend.json](../backend/fixtures/integration/backend.json)，含全部请求/响应、两种决策及相对PNG映射；不写A的frontend/public |
| #3 导出工具与测试 | [integration_bundle.py](../backend/tools/integration_bundle.py)、[测试](../backend/tests/test_integration_bundle.py)，改为内存库/显式模型fixture；回归证明不会触碰配置中的演示库和frontend |
| #6 集成报告与五分钟操作单 | 本报告及[demo-runbook.md](demo-runbook.md)，按当前main重写；不再写C未合入、拒绝只有日志或固定4个真实碎片 |
| #6 原始历史报告和JSON | [归档说明](archive/README.md)，原样保留`5af2ae0`版本，仅用于历史证据 |
| 旧README/acceptance/files/validation | 保留历史数值，追加当前入口和边界，解决README冲突时不覆盖B持久化/声呐安全说明 |

Mock的业务态、Agent回答和PNG均是显式fixture，真实执行的是HTTP路由与Pydantic验证。它不是场景时序、YOLO效果、三人彩排或浏览器验收。固定A1/T1/opt-1不可直接用于新的LIVE审批。

## 本次实际执行

机器记录：[final-integration-results.json](final-integration-results.json)，原始JUnit/构建产物保留在本地忽略目录`artifacts/handoff-refresh/`。

- 新交接专项4项PASS：全部21种REST、状态/事件模型、生成物一致性、PNG解码、结构化reject/approve、有序独立seq、不触碰演示库/frontend。
- 全量B+C初跑：194 PASS、1 FAIL、2 SKIP，92.55s。失败为B旧测试仍要求前端建议部署与LIVE浮标逐字节一致；不是后端算法报错。
- 专项修正后数据/交接10项PASS；最终全量 **196 PASS、2 SKIP，89.03s**。两项跳过缺少另一份COCO预训练冒烟权重，交付sonar权重已在本轮真实执行；未将跳过记通过。
- 前端npm ci、build、lint、check:recovery、check:sonar、check:a1…a6均已执行通过；3D chunk为1,003.10kB，保留构建警告。这些是自动检查，没有宣称真实浏览器/GPU/投影机通过。
- Ruff、compileall、pip check、diff检查通过。B生产算法、迁移、shared、frontend、agent、ml、C测试和data与基线比较均无差异；生成物通过重新导出的一致性断言。

### 本次发现并处理的兼容问题

1. 旧导出工具使用默认持久化数据库，可能碰到实际演示库或指纹失败。当前强制`:memory:`，不运行仿真循环，也不加载真实YOLO；即使HARBORGUARD_DB指向旧库，测试证明其内容和锁文件不变。
2. 原工具把Mock写到frontend/，违反当前A/B责任边界。改到backend/fixtures/integration并生成明确的布局PNG，A可自行导入；没有改公开API或新增静态服务端口。
3. A #11将离线浮标改为明确标注的建议部署，B原测试要求与根data/buoys.json字节一致。保留zones/assets/vessels的原一致性断言，并新增LIVE API检查：启动前后均严格返回B正式坐标；建议文件只校验契约兼容。A自己的check:sonar继续检查其布局和不挪动外部观测。没有放宽B物理几何断言或修改双方坐标。

## A/B/C 完成状态与剩余验收

| 模块 | 已实现/证据 | 未通过或未验证 |
| --- | --- | --- |
| A | main已有2D/3D、NOAA H12617多波束、建议浮标、恢复/审批/回放；本轮构建、自检通过 | 最新浏览器恢复边界、录屏/投影FPS、真实海陆/垂直基准对齐仍需现场；NAVD88与MLLW的datum tie不能只凭画面认为一致 |
| B | main已有REST/WS、持久化、结构化批准/拒绝、跟踪/风险/优化、保守灾害复航、预热；本次补齐未合交接资料 | 新C下三级505s超过500s，燃料泊位近场未确认；500条窗口无全历史分页；最新组合耐久待测 |
| C | main已有交付YOLO和Agent；相同B/C生产源码的独立候选有真实HTTP/WS模板及同库重启记录 | 模型针对合成声呐，不是实海；云/Ollama/LoRA不由本轮启用；英文60/300字符与模型事实仍由C验收 |

相同B/C生产源码的上一轮隔离候选（A不同）实测：A/B各3次离线语义哈希一致；全量191PASS/2SKIP；冷启动5.959s，5.00168Hz，最大间隔393.04ms；真实template建议、批准/拒绝、传输断线补偿、同库重启通过。来源：[声呐安全报告](../backend/docs/sonar-safety-integration.md)。本轮不会把这些历史API结果写成最新A真实浏览器通过。

### 应保留的限制

- 真实YOLO场景A首次UUV363.9s、三级505s，原500s上限仍FAIL；20ms为尽力目标，不能改统计制造达标。
- 当前真实模型场景B为6 clear/3 blocked/3 unsurveyed，节省9小时；燃料泊位唯一近场观测约0m，保留不确定。旧模板回放6/4/2不能覆盖此结论。
- `/api/events`仅最近500事件，无分页/总数/缺口标志；内部落库不等于前端能查全历史。`/api/log`最多1000条缓存。重启序列在同一数据库持续；换库应诚实提示历史不确定。
- 新参数指纹与旧运行库不兼容，保留旧库并给新版本设置独立HARBORGUARD_DB；不要清空旧库、改fingerprint或双写同库。
- A已修复多数恢复入口；同刻合法重复日志/不同操作员decision及旧REST覆盖新状态有既往边界问题。本轮现有自检通过不等于这些浏览器用例已复验；由A继续处理，不解析日志伪造审批。
- 真正断Wi-Fi、ESP32/LoRa、实海声呐、三次现场彩排和新模型20分钟耐久未由本次验证。最新NOAA画面与B示意业务数据不可互相冒充来源。

## 合入与交付

本次不改变B生产算法、数据库schema、REST/WS契约，不修改frontend/agent/ml/shared/data。新分支只提交B工具、测试、Mock、OpenAPI及交付资料；模型、数据库、缓存、日志、原始任务书不作为新文件提交。旧资料中尚未生效的分页提案继续等契约审批。

按新Draft审查后由负责人决定合并；旧#3/#6可以由负责人后续关闭为被替代，本代理不擅自关闭。仓库未配置CI时，无检查记录不等于CI通过。现场按操作单完成受控五分钟演示；录制/Devpost前还应完成目标设备和最新浏览器确认。
