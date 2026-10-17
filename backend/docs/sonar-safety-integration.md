# B 声呐与灾害保守判定修复验收

日期：2026-10-17。依据负责人批准的独立本地实施范围，以及后续明确的 Push 指令。仅提交 B 后端、测试、验证工具和文档；不修改 A/C 源码、共享契约或 main，不替换运行中的演示。

**B 修复可以单独审查合并；这不代表新版 C 或整套任务书全部验收通过。** 真实模型的 Security 三级警报仍在仿真 505 秒，超过原任务书 500 秒上限。新组合的浏览器恢复、20 分钟耐久及现场彩排尚待验收。

## 精确基线与改动

- 发布分支基于 main `8613834e7430eee40d2f020e6277dbdec72ca1f5`，B 实现提交 `6353421`。
- 独立候选先组合上述 main 与 C `6389b705bec35b8fc44018d1c14d770f2a82b364`，本地合并提交 `3f237b87866592d43064c76a93083c0f67ac3bd0`，B 实现提交 `8843422`。发布分支只 cherry-pick B 实现，不携带这次 C 合并。
- 候选的 frontend/shared 与 main 一致，agent/ml/tests 与指定 C 一致。当前演示仍运行旧工作区、旧模板和旧数据库；未重启或替换。
- 不增加 REST 路由、事件种类、字段、枚举或分页语义。仍为 21 REST 操作、14 种事件；`/api/events` 仍只返回最近 500 条事件。

修复包括：

1. 灾害候选的空结果、错分类及低置信结果保持 `unsurveyed`，不因覆盖率达到阈值就变 `clear`。只有有效 debris 识别会确认并 `blocked`；人工限制优先。无疑似障碍区仍可正常 clear/BFS 复航。
2. 同一候选每 20 仿真秒最多重试一次，总计最多 3 次，优先选择未尝试过的可用安全浮标。保留海洋哺乳动物保护；原安防每航迹最多 5 次实际发射的预算未改变，没有为“空图”返还次数。
3. C 扇形近场不足 30m 时选择实际距离合适的另一浮标；没有可用浮标则保持不确定。没有把 0m 输入伪造成 30m。B 自有矩形桩的零距离正例保持有效。
4. 检测框匹配按实际渲染布局选择投影；C 扇形与 B 线性桩分开处理。164m 示例的 C 预期 y 为 437.636，原 B 公式为 289.68。内部 `_projection` 不进入公开 Detection/事件。
5. 在 FastAPI lifespan 就绪前以独立种子预热模型；开始/重置复用模型，不再丢掉预热结果。不推进世界时钟/RNG，不生成业务检测、PNG 记录或事件。缺少 C/权重仍明确显示 stub。
6. 重试次数、时间和浮标记录进入内部检查点，与其他状态一同持久化和失败回滚。数据库表和共享数据结构未变。

主要文件：`backend/app/decision/{disaster,pinger,__init__}.py`、`backend/app/perception/classifier.py`、`backend/app/{config,checkpoint,main}.py`；新增 `test_model_safety.py`、`test_real_model.py` 和两个可复现验证工具。

## 实际测试与证据

机器可读证据：[sonar-safety-20261017.json](evidence/sonar-safety-20261017.json)。原始日志、JUnit、模型调用和新数据库保留于候选本地 `artifacts/model-fixes/`，未把缓存/数据库/日志提交到 Git。

| 验证 | 结果与范围 |
| --- | --- |
| 修复前 main+C 全量 | 170 PASS、5 FAIL、2 SKIP，101.82s；2 项为真实模型不满足旧桩识别断言，3 项是 C 数据集生成器 Windows 跨 C/D 盘 relpath 限制 |
| 修复后 main+C 全量 | 191 PASS、2 SKIP，93.07s；使用 C 盘 basetemp，未修改 C 生成器；跳过的 2 项缺少另一份 COCO 预训练冒烟权重，交付 sonar 权重另有真实验证 |
| 单独发布的 main+B | 110 PASS、1 SKIP，66.87s；main 没有新 C 权重，因此真实模型测试明确跳过；另有 2 条 pytest 缓存目录权限警告，不影响断言 |
| 原有桩识别正对照 | 显式选用完整 B 桩，保留原有 4 碎片、6 clear/4 blocked/2 unsurveyed、安防时间窗及完整回放断言；未把原断言放宽成全部未勘测 |
| 新增 B 安全回归 | 16 PASS：空/错/低置信、重试冷却/上限、近场、禁 Ping、人工限制、投影、模型复用/预热、同库重启、写入失败回滚及真实 sonar 权重保守复航 |
| 固定种子真实模型 | A/B 各跑 3 次完整离线场景，未启用 DEBUG_TRUTH_TRACKS；每场景 3 次事件、状态和 PNG 语义哈希一致 |
| 冷启动真实 HTTP/WS+C | PASS：新端口 8004/8006、新数据库；实际模板建议、拒绝/批准、真实 WS 断开后的 API 补偿、PNG 及同库重启验证；不是浏览器验收 |
| 静态检查 | Ruff、git diff --check、pip check 通过；A/C/共享契约的基线比较无额外差异 |

真实模型仅指交付的 YOLO 权重对**合成声呐图**推理，不代表实海声呐或硬件验收。云路由 disabled，Ollama 指向本机关闭端口，实际建议 model=template；没有把 LoRA 当成已训练。

| 实测项目 | 修复前 | 修复后 |
| --- | --- | --- |
| B 最终分区 | 8 clear、2 blocked、2 unsurveyed；燃料泊位/北锚地误绿 | 6 clear、3 blocked、3 unsurveyed；4 个障碍所在区无误绿 |
| B 节省小时 | 12（错误包含未确认区） | 9 |
| B 燃料泊位 | clear | unsurveyed；唯一范围内浮标与目标约 0m，没有物理可用的替代观测位置 |
| B 正常复航 | 入口/南主航道及集装箱泊位1 | 继续可复航，未以全黄规避检测 |
| A 首次 UUV / 三级 | 363.9s / 505s | 363.9s / 505s，时序没有改善；500s 要求 FAIL |

冷启动到健康检查 5.959s，同库重启到健康检查 5.824s。连续连接段共 294 帧，平均 5.00168Hz，最大间隔 393.04ms，P99 间隔 315.10ms，最大状态包 24,264B。进程树 RSS 峰值 431.59MiB，单核 CPU 均值 46.13%，16 逻辑核机器占用约 2.88%。这些是约一分钟样本，不是新版 20 分钟耐久。

离线工具没有调用 lifespan 预热，首轮 B 外层 tick 峰值仍为 2382.94ms，其中首次 classify 2216.57ms；后续 B 整体 tick 峰值约 380–385ms。不能拿预热移出实时路径当作消除了计算成本。20ms 继续为尽力目标；实时平均 5Hz 也不代表每帧严格 200ms。

## 合并与启动注意

**新参数改变内部检查点指纹，旧配置数据库不会被自动迁移或清空。** 直接用旧库启动会明确失败；这比静默丢历史更安全。合并前保留旧版本/旧库，为新版指定独立新库。不要删除或覆盖当前演示库，也不要修改 fingerprint 强行加载旧状态。

已准备好依赖时，在仓库根目录运行（Windows）：

```powershell
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/sonar-safety.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

仅 B 分支没有引入 C 的新权重，缺少模型时按契约显式 stub。要复现指定 C 的真实权重结果，先在独立测试分支组合精确 C 提交，按 `requirements-runtime.txt` 准备 CPU 推理依赖；不得把未验收云路由自动用于比赛。候选安装使用独立 venv，未更改原演示依赖。

```powershell
.venv/Scripts/python.exe -m pytest backend/tests tests -q --basetemp=artifacts/pytest-model
.venv/Scripts/python.exe -m backend.tools.model_acceptance --out artifacts/model-results.json --repeat 3
.venv/Scripts/python.exe -m backend.tools.live_model_smoke --out artifacts/live-model-new
```

最后一个命令要求 8004/8006 空闲、输出目录不存在，会使用新库并清理自己启动的进程。它临时覆盖 B 内部 Agent 目标到 8006，不改生产配置；8000/8001/5173 原演示保持不动。

## 未通过、未验证与队友下一步

- **FAIL：** 新 C 权重下 A 三级警报 505s，原要求 400–500s。本次不调风险阈值或消耗更多 Ping 来制造达标。B/C 后续应检查可用视距、前几次真实检测和有限发射窗口。
- **限制：** 燃料泊位仍未确认，不能宣称 4 个真实碎片均完成识别。若需补测需合理的新观测位置/场景数据评审；本次不改共享场景坐标或 C 渲染器。
- **PENDING：** 此新组合浏览器刷新/重连竞态、目标投影电脑、真实测深/潮位/声呐、真实断 Wi-Fi、20 分钟耐久、三次现场彩排、录制/Devpost。不得复用旧模板的已通过记录为新版全部背书。
- **A：** 使用既有 unsurveyed/blocked/clear 展示；不要让覆盖率 100% 覆盖服务端的未勘测状态。继续处理同刻重复日志、不同操作员 decision 去重及旧 REST 覆盖新实时状态的既有问题，不解析日志伪造审批。新分支不提供分页历史；500 窗口以外诚实降级。
- **C：** 原提交保持原样；独立验收新路由和模型，提供近场/远距失败样例，保持 model 标签真实。英文建议遵守 summary≤60、explanation≤300 **字符**，不能按单词放宽。
- **B：** 这次修复和证据先独立提交审查；不将 C 合并提交或旧 #6 整体混入 main。新版回放需在隔离目录重录后交 A 审查，本次不覆盖 frontend 的旧回放。

该报告补充已有 B0–B7 历史验收，不能把原有 37 项历史结论直接套用到新 C 候选。
