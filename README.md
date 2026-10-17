# HarborGuard · C（AI 模型与 Agent）

24h 黑客松：洛杉矶港水下安防数字孪生。本 README 只覆盖 **负责人 C** 的部分；
A（前端 5173）与 B（后端 8000）的代码不在本目录，C 不修改。

## C 负责的四个模块

| 目录 | 内容 | 步骤 | 状态 |
| --- | --- | --- | --- |
| `ml/sonar/` | `render_ping` 声呐渲染器 + 合成数据集 | C1 | ⏳ 待实现（C0 已建骨架） |
| `ml/yolo/` | YOLO26 训练、`SonarDetector`、`metrics.json` | C2 | ⏳ 待实现 |
| `agent/` | Agent 服务（端口 8001）：上下文/提示词/路由/问答 | C3 | ⏳ 待实现（`config.py` 已就绪） |
| `ml/lora/` | 蒸馏数据、LoRA、GGUF、Ollama 部署 | C4 | ⏳ 待实现 |

共享接口（`render_ping` / `SonarDetector` / REST / Recommendation）严格按
**`docs/shared-contract-v1.md`**（共享契约 v1，B 维护，H2 冻结），字段名一字不改。

## 三套环境（分开管理）

| 环境 | 位置 | 用途 | 机器 |
| --- | --- | --- | --- |
| 运行环境 | `.venv`（仓库根） | Agent 服务、render_ping、SonarDetector CPU 推理、自检 | MacBook（开发/演示主机） |
| YOLO 训练 | `.venv-yolo-train` / Colab | `yolo detect train`（50 epoch） | Lenovo GPU / Colab |
| LoRA 训练 | Colab / Lenovo（requirements-lora-train.txt） | Unsloth + TRL SFT | Colab 或经验证可用的 Lenovo CUDA 环境；**当前尚未验证训练 GPU** |

```bash
# 运行环境（MacBook）
bash scripts/setup_env_runtime.sh
# YOLO 训练环境（有 NVIDIA GPU 的机器上才真正创建）
bash scripts/setup_env_yolo_train.sh
# LoRA 训练：见 requirements-lora-train.txt 头部注释与 ml/lora/README.md（仅 Colab）
```

> 本 MacBook 注意：macOS 26 上 brew 版 Python 的 `platform.mac_ver()` 返回空串，
> 导致 pip 的 truststore 崩溃。因此 `setup_env_runtime.sh` 优先用 **uv**（`brew install uv`）
> 建环境；其他正常机器仍可用标准 `python3.11 -m venv`。

## 配置（.env）

所有模型名、API 地址、后端地址都走配置，`agent/config.py` 在导入时**显式** `load_dotenv()`：

```bash
cp .env.example .env   # 然后填写密钥；.env 已被 .gitignore 忽略，绝不提交
```

模型 ID 说明：任务书原文写 `claude-sonnet-5-5`；本机已实测可用并作为默认保留的
ID 是 `claude-sonnet-5`（可改 `ANTHROPIC_MODEL`）。`claude-sonnet-5-5` 是否为有效
官方 ID **未做验证**——以真实调用响应的 `model` 字段为准，不反复调 API 试名。

## C0 自检

```bash
.venv/bin/python scripts/check_c0.py
```

逐项打印 PASS / FAIL / PENDING。**无 API key / 无 GPU / 需要拔网线验证的项
标 PENDING（待完成），不假报通过。**

## C0 状态（截至 2026-10-16）

**自动检查通过 ≠ 验收通过。** 下列"手动待验收"项目只有负责人本人明确提供结果后才算勾选，
在此之前一律视为未完成。

- ✅ 自动检查 10/10 PASS（`scripts/check_c0.py`）：Python 3.11、依赖、pydantic v2、
  yolo26n.pt 加载、Ollama CLI/服务、qwen3:1.7b 本地真实对话、云端一次真实调用、.env 显式加载
- ✅ 云端已验证配置（不含凭证）：服务地址 `https://api.z.ai/api/anthropic`（进程环境
  `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`，Token 不入库不外显），响应
  `model=claude-sonnet-5`，回复正常
- ⏸ 手动待验收①：关闭 Wi-Fi 后 Ollama 仍能对话（`ollama run qwen3:1.7b`）——**未验证**
- ⏸ 手动待验收②：训练 GPU（Colab 分到 GPU / Lenovo CUDA 可用）——**未验证**
- ℹ️ 思考型模型注意：Sonnet 5 与 qwen3 默认带推理块，小 `max_tokens` 会被耗尽返回空文本；
  自检脚本已加预算，C3 调用时同样处理

## 不入库的内容（.gitignore）

`.env`、`.venv*/`、`ml/datasets/`（数据集，脚本可重跑）、`runs/`、`*.log`（训练日志）、
`*.pt` / `*.pth` / `*.gguf` 等模型文件。
唯一例外：`ml/yolo/weights/best.pt` 为最终交付的 nano 权重（几 MB），已放行入库。


## B 后端 MVP 已加入

后端源码、场景、测试位于 `backend/`、`data/`；完整启动、演示与对接说明见 [后端说明](backend/README.md)。上方 C 的原有工作说明保留，C 的后续进度由其负责人更新。

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
make backend
# 测试 make test；录制回放 make record
```

Windows 已建好环境时执行 `./dev.ps1 backend`；安装依赖可用 `./dev.ps1 setup`。后端端口 8000，WebSocket 为 `ws://localhost:8000/ws`，接口文档为 `http://localhost:8000/docs`。

共享契约字段维持 v1；B 的模型与样例在 `shared/`，并与 C 原有的 `docs/shared-contract-v1.md` 对照。A 的前端读取后端 REST / WS；C 的声呐与 Agent 实现完成后按冻结接口接入。回放在 `frontend/public/replay_a.jsonl`、`replay_b.jsonl`，配套图片在 `replay_assets/`。
