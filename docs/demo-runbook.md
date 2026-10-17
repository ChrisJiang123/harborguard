# HarborGuard 五分钟 Demo 操作单

本轮演示范围：A 的真实界面、B 的 Security/Recovery 仿真、C 的模板 Agent、操作员审批。识别来源保留 stub，建议来源保留 template；本流程不要求 YOLO 权重、LoRA、云端密钥或 Ollama。

## 演示前一次性准备

从最终集成 Draft PR 的分支检出完整代码。当前仅检出远程 main 还不包含 C3；不要在缺少 agent/main.py 的版本上演示。本操作单固定使用已验证的 C 模板提交 78d3957；C 后来新增的 9af08a7 三路路由未纳入此次候选，不要临上台切换到该版本并沿用本报告结论。

已验证环境：Windows、Python 3.11.17、Node 24.19.0、npm 11.17.0。先安装依赖和构建，现场五分钟从三个服务就绪开始计时；首次下载依赖的时间不计入展示承诺。

```powershell
# 仓库根目录；若已有 .venv，不重复创建
# 本机 Python 3.11 由 uv 管理，py -3.11 无法找到该解释器
uv venv --seed --python 3.11 .venv
./dev.ps1 setup
./.venv/Scripts/python.exe -m pip check
Set-Location frontend
npm.cmd ci --no-audit --no-fund
npm.cmd run build
Set-Location ..
```

requirements-lock.txt 已覆盖 B、C3 模板服务及 C1 渲染器所需的 NumPy/OpenCV/httpx/websockets/python-dotenv 等。本 Demo 不执行 C 的完整模型训练环境安装命令，不下载模型。

其他电脑若已在 Python Launcher 注册 Python 3.11，可用 `py -3.11 -m venv .venv` 替代 uv 命令；先验证解释器可用。Vite 的 Node 要求为 ^20.19.0 或 >=22.12.0，本轮使用上述已验证的 Node 24。

## 三个终端启动

终端一，仓库根目录：

```powershell
$env:DEBUG_TRUTH_TRACKS='0'
./.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

终端二，仓库根目录：

```powershell
$env:BACKEND_BASE_URL='http://127.0.0.1:8000'
$env:BACKEND_WS_URL='ws://127.0.0.1:8000/ws'
$env:AGENT_HOST='127.0.0.1'
$env:AGENT_PORT='8001'
./.venv/Scripts/python.exe -m agent.main
```

终端三，frontend 目录：

```powershell
npm.cmd run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

后端只运行一个 worker。端口被占用时检查已有服务，不杀死不明进程。跨域仅允许 localhost/127.0.0.1 的 5173；不要临时改预览端口。前端默认 REST 为 http://localhost:8000/api，WS 为 ws://localhost:8000/ws，和上述监听兼容。

配置覆盖只需进程环境变量，不要提交真实 .env。若需修改前端连接地址，A 的 VITE_API_BASE/VITE_WS_URL 是构建时变量，需重新 build；本流程使用其默认地址。

## 上台前检查（约 20 秒）

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8001/health
```

B 返回 ok=true；C 返回 ok=true、model=template、phase=c3-stage1。打开 http://localhost:5173/，确认 LIVE、浮标 10/10、无错误提示，选择 2D 地图。如网络瓦片不可用，点击“切换离线简图”。预先确认 3D 可渲染；本机渲染成功不等于演示电脑帧率已验收。

当前 A 刷新恢复缺口尚未修复：活动场景里不刷新、不另开实时页面。演示前通过“重置”回空闲，再开始场景。

## 五分钟展示顺序

| 墙钟时间 | 操作 | 观众应看到的结果 |
| --- | --- | --- |
| 0:00–0:20 | 介绍 LIVE、港区示意数据、浮标与分区；点“场景 A”，速度 10× | 目标运动、一级警报；强调是仿真态势 |
| 0:20–1:15 | 观察二级与主动 ping；约启动后 48–55 秒出现三级及模板建议时，立即点“暂停” | 风险、声呐证据、4 个方案和 Agent 模板建议；不要等到自然降级后才审批 |
| 1:15–1:45 | 选择局部方案、填写操作员名称，点“批准” | 只有此时出现“已批准”、decision 事件和受限分区；说明 Agent 不代为审批 |
| 1:45–2:00 | 短暂切换“3D 水下”，展示航迹和目标深度，然后回 2D | 同一套实时状态驱动 2D/3D；低性能电脑直接保留 2D |
| 2:00–3:10 | 点“场景 B”，保持 10×，观察一分钟 | 4 个碎片、B4/B7 在仿真 60 秒失效；最终 6 clear / 4 blocked / 2 unsurveyed；入口和南航道、集装箱泊位一可复航，演示假设节省 9 小时 |
| 3:10–3:40 | 打开 http://localhost:5173/?replay=replay_b.jsonl，用进度条定位末帧 | REPLAY、操作按钮禁用、相同 9 小时结果；不依赖后端在线计算 |
| 3:40–4:20 | 可切到 ?replay=replay_a.jsonl，定位三级时段，展示 A 回放；说明后续待办 | 真正 B 录制的 JSONL，不用合成 demo_full 冒充实时录制 |
| 4:20–5:00 | 留作问答和时间余量 | 核心闭环已在前 3 分钟内完整展示 |

场景 A 正常模式第一次三级约在仿真 483.1 秒，10× 约 48.3 秒；模板建议额外耗时通常远小于 1 秒。显示以服务实际状态为准。Recovery 对应 scenario=b、mode=disaster，不更改共享枚举名称。

## 现场故障应对

- LIVE 断线：先检查 B/C health。连接恢复后，A 当前不能补齐遗漏建议/审批/日志；若演示记录必须完整，显式重置并重开场景，不能把旧审批显示成新结果。
- Agent 未启动：B 问答返回 502，其他后端功能继续；启动 C 后重新开始 A。当前演示必须标明 template，不声称云端/本地 LLM 已运行。
- 三级尚未出现：确认 speed=10、未暂停、未注入噪声或浮标故障；不要用 Mock 的 60 秒事件节奏判断真实场景。
- 3D 较慢：切回 2D，保持演示流程；不临时改图形或算法实现。
- 场景 B 碎片声呐入口：A 负责的无航迹检测入口仍未修复。本次展示阻塞分区和复航，不点击当前被禁用的时间轴识别点；不能宣称该入口已经通过。
- 实时链路出现问题：使用明确标记为 REPLAY 的 replay_a/replay_b；回放只读，不能演示真实审批提交。图像资产必须随 frontend/public/replay_assets 一起部署。

结束后 Ctrl+C 依次关闭前端、Agent、后端。不要在现场自动 Merge 或重新下载模型。

完整状态、阻塞项、分支依赖与测试证据见 [最终集成检查报告](final-integration-report.md)。
