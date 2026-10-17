# HarborGuard 最终集成检查报告

结论：**当前版本适合提交 Draft 并按受控流程演示；完整团队验收仍有待办，不等于可无条件合入 main。** A 的刷新恢复、灾害识别入口按用户决定交 A 处理，本轮未修改前端源码。未开发或启用新的 YOLO、LoRA、LLM 路由或其他产品功能，冻结 v1 保持不变。

操作步骤见 [五分钟 Demo 操作单](demo-runbook.md)，接口清单见 [联调交接](frontend-integration.md)，机器可读结果见 [final-integration-results.json](final-integration-results.json)。

## 分支、仓库与 PR

检查基线为 origin/main `5817b9c`、已验证的 C 模板提交 `78d3957`、B 交接提交 `368df2e`。发布前 C 远程分支新增 `9af08a7`（云端/Ollama/模板路由），本轮按范围限制未纳入或验证，候选保持模板版本。远程仓库：origin 为 ChrisJiang123/harborguard，fork 为 tankewudi/harborguard。本轮在 `codex/harborguard-live-integration` 上整合现有 B/C 提交并增加最终交付文档，不修改本地或远程 main。

| PR / 分支 | 当前作用 | 检查结果 |
| --- | --- | --- |
| PR #2 | B 后端主体 | 已由仓库方合入 main |
| PR #5 | A6 前端 | 已由仓库方合入 main，前端源码基线为 main |
| [PR #3](https://github.com/ChrisJiang123/harborguard/pull/3)，codex/harborguard-backend-mvp | B 的 OpenAPI、Mock、交接导出与测试，head 368df2e | 保持 open / Draft；相对最新 main 合并预检无冲突，本轮不改其状态 |
| [PR #4](https://github.com/ChrisJiang123/harborguard/pull/4)，c/model-agent | C1/C2/C3；远程最新另含三路模型路由 | open；候选只纳入原始模板基线 78d3957，远程新增 9af08a7 留给 C 审查，不替 C 改源码或合并 PR |
| codex/harborguard-live-integration | A+B 主线 + 上述 B/C 提交 + 本次报告/操作单 | 发布为单独 Draft，明确与 #3/#4 的重叠和依赖，不自动 Merge |

建议由 C 先决定 #4 的新路由是否进入最终演示，团队按需合入 #3，再复核集成 Draft。若合入最新 #4，必须重新验证新 Agent 路由与依赖；本报告的模板结果不能外推为 9af08a7 已通过。共有提交会自然从差异中消失，Git 不应回退 C 的新提交。本轮不关闭、不代为批准队友 PR。

已执行 `git merge-tree --write-tree origin/main <branch>`，B 分支与集成分支均无冲突。集成分支包含 #3 和 #4 的已验证模板阶段原始提交，不通过文件复制重写历史。A 的 frontend/src、B 的 backend/app 和 shared 与 main 相同；C 的 agent/ml/tests 与固定提交 78d3957 相同（并非后来新增的 9af08a7）。新提交仅涉及 B 的文档及验证结果。

潜在后续冲突集中在 backend/README.md、docs/files.md、docs/validation.md 等共同说明文件，以及 A/C 后续变更后的集成基线；当前无实际冲突，不能据此保证未来提交也无冲突。发布前需再次 fetch；主线变化后重新预检。原始任务书保持未跟踪，真实 .env、日志、缓存和模型权重不纳入提交。

## 模块完成状态

| 模块 | 已完成且已验证 | 仍未完成 |
| --- | --- | --- |
| A 前端 | LIVE 连接、静态业务图层、2D、真实 3D 渲染、警报与方案、模板建议、人工批准确认、Security/Recovery 文件回放；构建/Lint/A1–A6 检查通过 | 刷新/断线事件补偿；无航迹碎片识别图入口；投影、目标硬件帧率、真实 Wi-Fi 断开刷新与录屏跨设备试播 |
| B 后端 | 21 REST 操作、5Hz WS、事件缓存、匿名感知跟踪、风险分级、主动 ping、方案比较、人工审批、灾害覆盖与复航、故障注入、Agent 代理、回放与契约样例 | 真实港区水陆核验；单 tick <20ms 尚未全量满足，仍有生成图片等峰值 |
| C 已提交版本 | 真实声呐渲染器；模板 Agent 的事件→上下文→建议→回传闭环；事实型问答，预算 18 秒，低于 B 的 20 秒代理预算；Agent 不审批 | 训练后声呐 YOLO 权重、更广的灾害/浮标建议不在本候选实现；C 远程新增云端/Ollama路由不在本轮已验证模板候选中，本轮不新增或启用模型 |

Detection.model=stub 和 Recommendation.model=template 必须保持可见。C 渲染器已接入，不代表训练后的识别模型已提供。Recovery 使用 scenario=b、mode=disaster，不重命名冻结枚举。

## 阻塞性问题与演示条件

| 级别 | 问题、证据与责任 | 对提交 / 演示的影响 |
| --- | --- | --- |
| 完整验收阻塞，A 负责 | 实时 A → 三级 → 暂停 → 批准 → 刷新：B 仍保留 restricted 和 recommendation/decision 事件，A 的建议、审批确认和日志却变空。frontend/src/data/ws.ts 未在连接后调用已有 /api/events 补缓存 | 不阻止 Draft 提交；受控演示期间不刷新。不能声称刷新恢复已验收。修复应使用现有接口，历史事件不得覆盖新快照 |
| 灾害识别图入口验收阻塞，A 负责 | B 的 4 条碎片 Detection.track_id 为空字符串，PNG 均可获取；Timeline.tsx 仅允许有活动 track 的事件点击，四个识别点 disabled | 不阻止展示阻塞分区与复航；不能在场景 B 演示该弹窗入口。按 detection.id 打开已有预览即可，无需改契约 |
| 主线完整启动门槛，维护者/C 负责 | C3 仍在 #4，main 没有 agent/main.py；#4 最新另含未在本候选验证的三路路由 | 候选已有模板闭环；最终 main 合入须由维护者选择 C 版本。若采用 9af08a7，需重验路由、依赖与演示，不以旧模板结论代替 |

受控五分钟演示的条件：提前安装依赖并构建、三个服务健康、LIVE 已连接、A 活动场景中不刷新、场景 B 展示地图/覆盖/复航而非尚未修复的图片入口。若这些条件不成立，改用明确标记 REPLAY 的离线展示，不能冒充实时审批。

## 非阻塞问题与验收边界

- C 数据集生成器用 os.path.relpath，默认临时目录在 D:、仓库在 C: 时，曾有 3 项测试失败。本轮将 pytest 的 basetemp 指向仓库 artifacts 后通过；未修改 C 源码，也不隐藏原失败。Demo 不生成训练数据集。
- 两项预训练权重推理冒烟因 .cache/yolo26n.pt 缺失跳过，不算通过；本轮不下载模型。
- 前端 3D chunk 约 981KB，有构建体积警告；Three.Clock/TestClient 有上游弃用警告，未观察到由此引起的运行错误。
- 现有 20 分钟耐久记录属于此前 B 服务验收，不外推为最新 A/B/C 组合的 20 分钟耐久通过。本轮组合的真实时长和 tick 警告见 JSON。
- 单 tick 20ms 目标仍有超限；当前5Hz输出可用于演示，不把平均频率作为所有性能指标通过的依据。
- 地图与船期为示意/虚构数据，节省 9 小时来自每区 1.5 小时等演示假设；未完成真实海图部署核验。
- 五分钟指系统预备完成后的展示时长，不保证首次联网安装全部依赖、真实投影检查也在五分钟内完成。

## 本轮已通过测试

| 检查 | 命令 / 证据 | 结果 |
| --- | --- | --- |
| B + C 全量回归 | `.venv/Scripts/python.exe -m pytest -q backend/tests tests --basetemp artifacts/final-integration-pytest` | 103 passed、2 skipped，57.16 秒；含 B 的两项交接样例测试 |
| Python 静态与依赖 | Ruff backend；compileall backend/agent/ml；pip check | 通过、依赖无冲突 |
| 前端 | npm run build、lint、check:a1…check:a6 | 全部通过；保留 chunk 大小警告 |
| 冻结字段 | 比较 A 与 shared/types.ts 的全部 12 个 interface 字段/类型；B/C 契约原文测试 | 一致；21 REST 操作，无增改字段 |
| 真实组合服务 | B 8000 + C 8001 + A 5173，按现有契约检查 Security、建议、拒绝/批准、重置、Recovery | 本轮结果见 final-integration-results.json 的 runtime；只在 status=passed 时计通过 |
| 离线资料 | 经真实前端静态服务读取两个 JSONL、逐条校验 Schema/seq/wall_ms、解码所有 PNG | 结果与消息数、图片数见 JSON；不重新录制并覆盖团队回放 |
| 源码归属 | Git 对比 A/main、B/main、C/78d3957 | 生产源码均与相应已提交版本一致 |
| 合并预检 | main + B 分支；main + 集成分支 | 无冲突；发布后再读 GitHub mergeable/CI |

此前同版本生产源码还完成真实浏览器 LIVE/3D/审批确认，以及 B 回放末帧：A 为 120 秒墙钟 / 1,200 仿真秒，B 为 60 秒 / 600 仿真秒，末帧复航 9 小时。本轮文档提交不将既有浏览器验证冒称为重新验证投影仪、Wi-Fi 或新模型。

## 接口和状态一致性

- REST 的完整路径/约束/示例在 frontend-integration.md 和 docs/integration/openapi.json。WS 为 ws://localhost:8000/ws，无 /api 前缀；state 是完整快照，event 与 state 共用递增 seq。
- 三级后产生 options_ready，C 通过已有 GET 获取事实，POST /api/recommendations，B 校验引用再广播。收到建议前后均不自动 restricted。
- 人工 reject 仅写日志，approve 才产生 decision 与受限分区；本轮比对方案 zones_closed 与实际 restricted 集合一致；reset 后旧审批返回 409。
- B 的 /api/events 能补建议与审批事件；A 的消费恢复是上述独立待办，不能通过给 state 私加字段掩盖。
- B 的 /api/agent/ask → C /ask 返回 answer/model；模板服务真实可用，不启用云端或 Ollama。
- Recovery 四条无航迹检测符合 v1；覆盖、浮标失效、6/4/2 分区状态和 9 小时复航数值在 REST/WS/既有回放中保持一致。
- 8000/8001/5173 是本轮已验证端口；Node 24.19.0/npm11.17.0，Python3.11.17。依赖和环境的准确命令在操作单中，不需要提交真实密钥。

## 发布与交付检查

只暂存明确列出的 B 文档与结果。本轮扫描 237 个索引文件及待推送历史的 238 个独立 blob，未发现所检查的常见密钥模式或不应提交的环境/缓存/日志路径；这是模式扫描，不声称绝对排除所有秘密。main 原有约 10.9MB replay_a、约 9.6MB demo_full 和 C 基线原有 samples.png 是有意演示资源，均未由本轮重新生成。最大新增交付文件是文本报告/JSON，没有新权重、日志或缓存。

保留 B/C 原始提交，推送到独立 feature 分支；保持现有 #3/#4 状态，新集成 PR 必须为 Draft。没有 CI 工作流或检查记录时应报告“未配置/无记录”，不能称作 CI 通过。最终 GitHub PR 链接和实时 mergeable/CI 状态在交付回复中给出。

本报告支持“安全提交、可审查、受控演示”，不代替 A 的两项修复、队友代码审查和维护者的 main 合并决定。
