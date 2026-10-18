# 最新仓库接入与C4收尾复验

2026-10-17，America/Los_Angeles。按“使用GitHub最新版本”的追加要求，fetch后以
`origin/main=5a68f12`建立独立分支`codex/c4-latest-integration`，接续C4配置切换、
来源修正和指标界面。原目录`demo/mac-integration`与其他终端在途改动保持原样；没有合并到main。

此文补充并更新[c4-handoff-closure](c4-handoff-closure-20261017.md)中的版本结论。
该旧记录和c784081数值结果作为历史证据保留，新版B结论以本次精确基线为准。

## 最新源码与依赖

- 仓库：`https://github.com/ChrisJiang123/harborguard`；上游基线5a68f12，B最新实现97a8c75。
- C4原提交6da0831、来源收尾7c96ae1、指标摘要6b18abb按顺序接续到独立分支。
  最新前端已经英文显示，因此解决指标卡冲突时保留英文界面与新版源码功能。
- 使用仓库当前package.json/package-lock，未升级、重装依赖；复用已有运行环境和
  前端node_modules，构建选择机器已有Node22.23.1。模型、提示词、采样、预算不变，未训练。
- 独立工作区当前在`/tmp/harborguard-b-review-20261017-codex`；环境和冻结数据只通过本机路径复用。
  没有把.env、数据集、模型文件或日志整体提交。Git交付分支可在正常目录重新检出。

## 数据与指标

来源审计在最新工作区20/20 PASS。test50仍是40条contexts500加10条extra80，
与6da0831记录的文件哈希一致，原“实采测试”标签已修正。train501输入与Lenovo训练记录一致，
前493正式训练、末8内部验证。test50/confirm60与训练输入精确重复均为0；采集批次与语义独立的
限制沿用[来源审计](../acceptance_c4/data_provenance_20261017/README.md)，不宣称真实海域性能。

| 合成集 | 结构 | ID+事实 | 方案 | null | 平均生成耗时 |
| --- | --- | --- | --- | --- | --- |
| test50 | 50/50 | 44/50 | 31/33 | 14/14 | 3.75s |
| confirm60 | 60/60 | 39/60 | 35/36 | 18/18 | 4.71s |

保留原指标、schema失败归档、独立分母与配置，没有重新运行整套LoRA评估。
唯一B侧生成物更新为`backend/fixtures/integration/backend.json`中的GET /api/metrics响应：
原快照lora=null与当前正式指标矛盾；只同步此响应，断言、其他接口样例及B算法源码均未改。

## 验证结果

- 最新组合全量：232 PASS、2 SKIP、0 FAIL。跳过的是另一份COCO冒烟权重，正式声呐YOLO已测试。
- C4/B安全等专项122 PASS；指标快照专项4 PASS；前端构建与英文检查PASS。
- 首次全量因本轮指定临时目录的父目录不存在，产生35项setup错误；另有旧指标快照差异。
  创建隔离测试目录、同步上述单条快照后重跑通过。首次失败日志保留，没有改断言掩盖失败。
- 最新B完整600仿真秒×3：四个危险位置全程不clear；最终均为6clear/3blocked/3unsurveyed，
  三轮事件/状态/PNG语义哈希一致，复航列表排除危险区。9h只是按当前clear分区派生的演示值。
  最新代码的原坏帧、近场、错误分类、低置信及多目标真实C投影专项也在本轮测试范围内。
- 离线数值验证显式CLOUD_PROVIDER=disabled，并拦截HTTP发送；调用尝试0。
- 最新A再次复算：L1=1.0、L2=150.7、L3=505.0秒，首次UUV363.9秒。
  **三级500秒要求仍FAIL**，不能因自动测试通过而豁免任务书时序。

最新B使用匿名几何观测，仍是假设的合成传感器输入；没有进入观测流的障碍、完整跟踪链
AIS真值耦合、拥挤交叉接触关联和真实回波端到端感知不在已通过声明内。C公共投影helper仍由
原C终端提交，未把工作区未提交几何代码悄悄带入本次远端基线。

## 最新版本独立本机预览

- 前端 `http://127.0.0.1:5174/`
- 后端 `http://127.0.0.1:8004`，使用独立`artifacts/latest-preview.sqlite3`
- Agent `http://127.0.0.1:8002/health`，本地harborguard-lora、draft_output_format=json、云端disabled且0次调用
- Ollama复用11434；预热探针不计为业务生成耗时。

8004仅在本轮独立进程内增加5174的本机CORS来源和8002 Agent地址；没有修改共享接口或
仓库默认端口配置。没有重启或替换原8000/8001/5173。隔离预览的云端禁用是测试配置；
原演示健康仍为OpenRouter/google/gemini-2.5-flash→本地LoRA→模板。

浏览器实际确认新版英文LIVE页面、harborguard-lora/format=json、两组合成来源、整数分母和
6/50、21/60事实失败说明；原配置/失败历史保留在可展开详情。没有用API 200代替界面验收。
截图与日志在原目录`runs/codex-c4-handoff/`，哈希和完整机器摘要见
[latest-integration.json](../acceptance_c4/data_provenance_20261017/latest-integration.json)。

## 仍待完成与归属

B：505秒时序；最终演示切换时保留旧库并使用新配置指纹对应的独立新库。
A：最终演示端口接入后的浏览器恢复、耐久及现场确认；原问答UI等未提交改动仍归原终端。
C：公共声呐几何helper提交和接入；尚未做qwen3→LoRA实际往返回退演练。
物理Wi-Fi、投影可读性、跨设备试播继续待负责人确认。没有公网/Vercel部署、main合并或强推。
