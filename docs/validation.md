# 后端 MVP 验证记录

历史说明：下文73项/桩识别数据来自初始MVP，不代表当前main。2026-10-17主线已包含B #10、C #4和A #11；新版交接与实际执行结果见 [最终集成报告](final-integration-report.md)、[机器记录](final-integration-results.json) 和 [声呐安全验收](../backend/docs/sonar-safety-integration.md)。20ms现为尽力目标；真实YOLO三级505秒的500秒任务指标仍FAIL。

在 Windows、CPython 3.11.17、requirements-lock.txt 所列依赖上验证。正常模式关闭 DEBUG_TRUTH_TRACKS；C 的渲染器、YOLO 权重与 Agent 尚未提供，因此识别使用明确标注的 stub。

## 自动化验证

- pytest：接入远程 C0 骨架后，73 项全量测试通过，最近一次通过 dev.ps1 test 执行，耗时 55.19 秒；包含 C 与 B 契约逐 token 一致性检查，以及模型指标含 NaN 时返回 null 的回归。
- Ruff：所有 backend Python 文件通过。
- compileall：backend 全部 Python 源码编译通过。
- pip check：依赖无冲突；PowerShell setup、check、record 已实际执行成功。
- 全新 Python 3.11.17 虚拟环境按锁定依赖安装并建立 editable 项目，用时 30.41 秒；新环境真实服务烟测通过，状态推送约 5.04 Hz。这是本机后端安装验证，全套 A/C 系统仍需队友验收。
- 将样例 JSON 作为 TypeScript 字面量，分别赋给任务书原文的 StateMsg、EventMsg[]，使用 `tsc --noEmit --strict --skipLibCheck` 编译通过。
- 13 个 GET（包含声呐 PNG）、全部 8 种 POST、14 种事件、WebSocket 状态和事件均有验证。JSON 输出按冻结模型校验；图片实际解码为 640 × 640。
- 实际 Uvicorn 服务上的 Agent 未启动检查返回 502 和明确错误，随后 health 仍返回 ok；20 秒超时路径通过 MockTransport 验证为 504。
- 当前 FastAPI/Starlette TestClient 发出一条上游 httpx 弃用警告，测试仍通过；运行服务不依赖 TestClient。
- 当前 Windows 环境没有 GNU make，验证使用 Makefile 对应的相同 Python 命令及 dev.ps1；Linux/macOS 的 make 命令尚未在本机执行。

## 场景 A

固定 seed 42，仿真 1,200 秒，speed 10，使用匿名声学观测与真实跟踪链路。

| 指标 | 实测 |
| --- | --- |
| 一级首次出现 | 仿真 1.0 秒，约墙钟 0.10 秒 |
| 二级首次出现 | 仿真 150.7 秒，约墙钟 15.07 秒 |
| 三级首次出现 | 仿真 483.1 秒，约墙钟 48.31 秒 |
| 首批方案 | 同一仿真时刻，3 个局部方案与全港关闭基线 |
| 首次检测至抵达资产的主航迹 ID 占比 | 90.53%，965 / 1,066 个每秒样本 |
| 全场景位置 RMSE | 12.24 米 |
| 每 300 秒匿名 confirmed 假航迹 | 0 / 0 / 0 / 0；距全部真值超过 100 米作为评估判据 |
| UUV 误继承 AIS 船舶分类 | 0 |
| state 最大大小 | 26,620 字节，低于 50 KB |
| 0.1 秒数值子步耗时 P99 | 5.26 ms |
| 单次最长子步 | 36.88 ms，声呐图片编码附近 |

任务书三浮标直线目标测试中，30 秒后的定位 RMSE < 30 米、速度误差 < 0.3 m/s，测试通过。完整场景包含航点转弯和停止，速度 RMSE 为 0.454 m/s；不能把直线测试阈值套用到转弯过程。

抵达资产后继续静止的阶段仍会发生航迹换号；若把这段纳入 1,200 秒全程，主 ID 占比约 80.4%。验收要求的首次检测至抵达窗口为 90.53%。数值子步偶有高于任务书 20 ms 目标的峰值，当前尚未保证每一个子步都低于该值；常规数值计算和 10 Hz / 5 Hz 实时节奏已可演示。

原始报告：`perception_metrics_a_600.json` 和 `perception_metrics_a_1200.json`。复核命令：

```bash
python -m backend.app.perception.benchmark --seconds 1200 --out docs/perception_metrics_a_1200.json
```

## 场景 B

固定 seed 7，仿真 600 秒，speed 10。4 个碎片全部检测，均在初始 0.1 秒触发；B4、B7 在仿真 60 秒失效。最终 6 个 clear、4 个 blocked、2 个 unsurveyed。入口和南主航道可通，集装箱泊位一可复航；按任务书每区 1.5 小时的演示假设，计划显示节省 9 小时。碎片不产生安防警报。

## 回放

| 文件 | 消息数 | state 帧数 | 时长 | 最大 state |
| --- | --- | --- | --- | --- |
| replay_a.jsonl | 722 | 601 | 120 秒墙钟 | 26,117 字节 |
| replay_b.jsonl | 335 | 301 | 60 秒墙钟 | 2,032 字节 |

相同种子分别完整录制两次，事件名及仿真时间序列完全一致，JSONL SHA256 完全一致。所有声呐静态 URL 对应实际 PNG，可离线解码；还在独立静态 HTTP 服务上验证了两个 JSONL 和全部 18 张图片。再加实时场景验收，各场景至少运行三次，关键事件时间没有变化。A 的前端回放器尚未提供，因此浏览器中的完整播放仍需 A 验收。

## 实时耐久检查

运行 `python -m backend.tools.soak --seconds 1200 --port 8000 --report artifacts/soak.json`，真实 Uvicorn 进程循环切换 A/B、重置和六种故障。采样包含 Windows 虚拟环境启动器及其 Python 子进程的 RSS 与单核 CPU；端口占用时工具拒绝启动，结束清理它创建的进程树。

20 分钟运行通过，实测 1,200.13 秒；6,001 个 state、1,142 个 event、平均 5.00 Hz、共 14 次场景启动，服务 ERROR 为 0。最大 state 为 26,125 字节。全部 Python 子进程合计 RSS 为 88.18–100.88 MB，暖机后在约 93–101 MB 内随场景切换回落；未观察到持续单向增长。采样单核 CPU 峰值 17.5%，低于 50% 目标。原始采样见 soak_metrics.json。

在 10× 运行时，外层墙钟 tick 一次推进 1 秒仿真，包含多个 0.1 秒子步。记录了 289 条超过 20 ms 的 tick 警告，最大 145.4 ms，主要出现在声呐图片生成和初始批量碎片识别附近。因此“每个 tick < 20 ms”的性能目标仍未完全满足；平均推送频率和服务稳定性通过。

这次耐久检查覆盖 B 独立服务；随后将开发分支接到 origin/main 的 C0 骨架上。再次全量测试 73 项通过，真实服务 15 秒烟测通过、状态约 5.03 Hz。通过 Git 比较确认 C 原有 agent/、ml/、scripts/、依赖文件及 docs/shared-contract-v1.md 未被修改，原 README 全文也保留，仅追加 B 入口。

## 尚需团队验收

真实港区地图与水陆核验；A 的地图、按钮、回放器和重连；C 的 YOLO、Agent 与 Ollama 离线切换；三人全链路彩排和五分钟从零启动。详见 acceptance.md。这些未提供的队友模块不在本地测试通过的声明范围内。
