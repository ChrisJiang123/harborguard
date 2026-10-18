# C4 接手收尾记录（2026-10-17，America/Los_Angeles）

检查对象是本机 `demo/mac-integration`，接手 HEAD `6da0831`。未找到适用的 AGENTS.md。
首次 fetch 后同名远端为 `46f6b16`，本地领先1；远端 main 为 `c784081`，与接手 HEAD
存在4/26个独有提交，不能按旧报告直接合并。本轮没有合并 main、切换当前分支、重训、
覆盖权重、重建环境、重启服务、修改数据库或部署公网。精确交付 SHA 与 push 状态见本次交付回复。

## 来源结论与可复算链

原“test50 为 capture_real 实采”的说明错误，已经撤回。原始指标数值保留。

1. 当前生成器只读重建 contexts500/seed0、extra80/seed1、confirm60/seed424242，内容逐条一致。
2. 580 条合成源中552条合格蒸馏；按 key 排序、seed0 洗牌，前50条组成test50（40+10），
   后450条组成合成训练部分。逐条同序复现；另52条合格合成未进入这两个划分。
3. capture_real 的51条只在 train 文件尾部出现。train501 SHA256 与 Lenovo training_meta 一致；
   按交付程序原顺序，正式训练493=450合成+43后端截取，内部验证8均为后端截取。
4. test50 和 confirm60 哈希与原交接提交6da0831中的指标记录相同，没有发现测试集被更换。
   confirm60包装版只是 user JSON 空格不同，规范化后与原始60条内容和顺序一致；原冻结文件未改。
5. train501/test50、train501/confirm60、test50/confirm60及real51/test50的精确上下文交集均为0；
   两组测试内部无精确重复。未出现需要新冻结集重评的训练重叠；没有调提示词、参数或检查点。

“后端截取”指本机仿真场景运行上下文，不是物理声呐或真实海域。缺少逐条capture-run ID，
无法从源文件单独重建所报告三次采集的批次边界。精确去重不能证明语义独立；本轮哈希不能
独立证明源文件历史创建时间，冻结前后时间线仅按已有记录保留。不能再声明真实采集独立测试性能。

来源脚本与20项检查、文件哈希、训练交付证据索引见
[来源审计](../acceptance_c4/data_provenance_20261017/README.md) 和
[audit.json](../acceptance_c4/data_provenance_20261017/audit.json)。原数据集、模型与详细运行日志保留本机，不整体纳入 Git。

## 保留的两组结果

| 合成上下文集 | 结构 | ID+确定性事实 | 方案 | null | 平均每条（含重试） |
| --- | --- | --- | --- | --- | --- |
| test50 | 50/50 | 44/50 | 31/33 | 14/14 | 3.75s |
| confirm60 | 60/60 | 39/60 | 35/36 | 18/18 | 4.71s |

整数分子由原三位小数聚合值和已知整数分母唯一还原，原始结果文件不改；两组不混算。
评估格式json，temperature0/seed0/num_predict450/think=false，首试+一次校验重试，
单次30秒超时；预热排除，不是线上9.5秒事件预算性能保证。评估无模板兜底，失败计分母。
未列出的模型继续完整schema。完整schema历史失败、归档和原模型对照均保留，
并修复指标发布脚本重复运行会覆盖原始失败归档的问题；隔离临时夹具连续发布两次验证不覆盖。

## 当前接入与验证范围

- 8000/8001/5173进程工作目录均为本项目，11434为现有Ollama；本轮复用，没有重启或业务POST。
- 8001/health确认service=agent，local.request_model=harborguard-lora，云端openrouter/
  google/gemini-2.5-flash。顶层model是最后路由结果template，不能当作配置模型。
- 当前配置文件为harborguard-lora:json；运行中的旧进程未暴露draft_output_format，
  **在线格式字段核验仍待协调重启**。已接续源码中的健康可观测字段，并测试json/默认schema两条路径。
  [安全配置快照](../acceptance_c4/data_provenance_20261017/runtime-check.json)只含允许公开的配置字段。
- 既有切换前事件证据：本地模型成功3条，事实失败转模板1条，重置零迟到POST，云端disabled。
  本轮读取并保留证据，没有重跑整套LoRA实验，也没有把模板计为模型成功。
- C侧相关离线测试86 PASS；指标归档保护回归1 PASS。子进程显式CLOUD_PROVIDER=disabled。
- 前端构建PASS；现有Node20.18.0有Vite版本兼容警告，未升级或重建环境。
- 在5173无参数LIVE浏览器页面实际展开并查看指标，显示评估模型/格式、两组合成来源、
  50/50与60/60分母、事实44/50与39/60、31/33与35/36、null和耗时，突出6/50与21/60事实失败。
  原始配置/历史失败可展开。证据：`runs/codex-c4-handoff/ui-{test50,confirm60}.png`与`ui-ax.txt`。
- 没有执行qwen3→LoRA实际往返回退；只有默认行为单测、切换前备份与已有正向切换。
  物理Wi-Fi、投影可读性、跨设备试播继续由负责人确认；Agent从不批准决策。

## 远端B修复的隔离复验

发现B实现6353421已推送并进入远端main。另建detached检出c784081，复用现有.venv，
不启动服务、不接演示数据库、不合并到当前工作区、不加载未提交C几何改动。

- 独立目录正式权重与当前工作区一致：SHA256
  `2cad3146fa4b98516efa0057367c3c5d53220dc2a3246058f5608094a6568839`。
- B安全测试16 PASS、0 SKIP。真实权重B场景三轮全程检查四个障碍区不得clear，均通过；
  结果6clear/3blocked/3unsurveyed、9h，三轮事件/状态/PNG语义哈希相同。
  berth_fuel保持unsurveyed；anchorage_north及另两个已确认碎片区blocked，复航列表排除障碍区。
- 云端显式disabled，并拦截httpx发送，实际HTTP调用尝试0。没有调用收费服务或LoRA。
- A场景另一次只读时序复验：L1=1.0、L2=150.7、L3=505.0秒，首次UUV363.9秒；
  **500秒上限FAIL**。没有放宽任何原有断言，也没有豁免交接中的两项历史集成失败。
- 以上仅证明该远端B/已提交C组合在合成图上的数值安全结果，不是当前演示进程已修复，
  也不是完整新版浏览器、耐久、真实海域或全部多目标情形验收。

[摘要与原始证据哈希](../acceptance_c4/data_provenance_20261017/remote-b-check.json)；
原始A/B结果保留`runs/codex-c4-handoff/`。可复跑的三轮B检查器在
[verify_remote_b.py](../acceptance_c4/data_provenance_20261017/verify_remote_b.py)，参数为独立检出路径。

## 改动归属与剩余事项

本轮按C来源/配置可观测性、前端指标展示分别提交；runbook仅暂存本轮修订段落。
其他终端已有的backend/README、frontend/README、AgentCard、index.css、demo.sh、
集成验收报告、C声呐render.py/几何测试与几何文档继续留在工作区，不纳入本轮提交。

B：协调把已推送安全修复接入演示，保留旧库，新配置指纹需独立新库；继续处理505秒时序。
A：接入已推送前端更新后做最终组合浏览器验收；现有问答UI等在途改动由原终端提交。
C：几何辅助改动由其原终端提交；协调Agent重启后核对健康格式字段，后续安排往返回退演练。
最终组合仍需时序、浏览器恢复、耐久及负责人现场确认，不能由本轮C4元数据收尾替代。
