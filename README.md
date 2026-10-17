# HarborGuard · C（AI 模型与 Agent）

24h 黑客松：洛杉矶港水下安防数字孪生。本仓库现包含 A（前端 5173）、B（后端 8000）与 C（模型/Agent）三部分；本 README 前半保留 C 的环境说明，前端的完整启动、联调、3D 操作和验收状态见 [frontend/README.md](frontend/README.md)。

## C 负责的四个模块

| 目录 | 内容 | 步骤 | 状态 |
| --- | --- | --- | --- |
| `ml/sonar/` | `render_ping` 声呐渲染器 + 合成数据集 | C1 | ✅ 代码 + 4000 张合成数据 + **后端真实调用联调通过** |
| `ml/yolo/` | YOLO26 训练、`SonarDetector`、`metrics.json` | C2 | ✅ Lenovo 训练交付已通过 **Mac 验收**：mAP50=0.9771、CPU 49.7ms/张（600 张合成 val）；后端 detection.model=yolo26n，/api/metrics 已出数（见 ml/yolo/ACCEPTANCE-MAC.md） |
| `agent/` | Agent 服务（端口 8001）：上下文/三级路由/问答 | C3 | ✅ 云端(OpenRouter)→本地→模板闭环，20/20 实测 `model=cloud` |
| `ml/lora/` | 蒸馏数据、LoRA、GGUF、Ollama 部署 | C4 | 🟨 生成/蒸馏/截取/评估脚本完成，450/50 样本就绪，基座已评；**待 Colab 训练与部署** |

共享接口（`render_ping` / `SonarDetector` / REST / Recommendation）严格按
**`docs/shared-contract-v1.md`**（共享契约 v1，B 维护，H2 冻结），字段名一字不改。

## 三套环境（分开管理）

| 环境 | 位置 | 用途 | 机器与 Python |
| --- | --- | --- | --- |
| 运行环境 | `.venv`（仓库根） | Agent 服务、render_ping、SonarDetector CPU 推理、自检 | MacBook（开发/演示主机）· Python 3.11（实测） |
| YOLO 训练 | `.venv-yolo-train` / Colab | `yolo detect train`（50 epoch） | ✅ Lenovo 已实测：Windows · Python 3.12.10 · cu130；Colab 备选 |
| LoRA 训练 | Colab（暂定） | Unsloth + TRL SFT | 暂定 Colab；Unsloth 在 GPU 上未验证（WSL 方案以后修，不阻塞 C1） |

```bash
# 运行环境（MacBook，Python 3.11）
bash scripts/setup_env_runtime.sh
# YOLO 训练环境（Linux bash；CUDA 源与 Python 版本可配置，脚本本身未实测）
PYTHON_VERSION=3.12 YOLO_CUDA_INDEX=cu130 bash scripts/setup_env_yolo_train.sh
# Windows 训练环境：用 requirements-yolo-train.txt 头部的 PowerShell 说明（Lenovo 实测路径 Scripts\python.exe）
# LoRA 训练：暂定 Colab，见 requirements-lora-train.txt 头部注释与 ml/lora/README.md
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
- ✅ 手动验收②a：YOLO 训练 GPU（Lenovo）——负责人 2026-10-16 实测通过：
  Windows · Python 3.12.10 · RTX 5060 Laptop GPU（8151 MiB，sm_120）·
  torch 2.14.1+cu130 · torchvision 0.29.1+cu130 · ultralytics 8.4.178；
  CUDA 运算、反向传播、YOLO26 `device=0` 推理全部通过。
  以上为实测记录（不代表"当前最新版本"）；Lenovo 已验证环境不再重建
- ⏸ 手动验收②b：LoRA 训练 GPU（Colab / Unsloth）——**未验证**，暂定 Colab
- ℹ️ 思考型模型注意：Sonnet 5 与 qwen3 默认带推理块，小 `max_tokens` 会被耗尽返回空文本；
  自检脚本已加预算，C3 调用时同样处理

## C1 状态（2026-10-16）

- ✅ 渲染器 / 数据生成器 / 预览完成；pytest 13/13 通过
- ✅ **4000 张合成数据**已生成（`--seed 0`，实测 31 s）：train 3400 / val 600，
  负样本 10.9%，类别占比偏差 ≤0.1pp，生成目标 8935 / 有标注 8926
  （9 个 <16px² 被契约下限丢弃，小目标不另删除）。
  **数据全部为合成数据**，指标仅代表仿真分布，不得当作真实声呐性能
- ✅ **与真实后端联调通过（2026-10-17，三层验证）**：
  ① B 的 `SonarClassifier` 直接调用 `render_ping`——640×640 扇形 PNG、同 seed 字节一致、
  标注过 B 侧校验；② 合并后端代码后 73 项后端测试全过；③ 实时服务跑场景 A：
  产生 5 条 detection 事件，`GET /api/sonar/det-5.png` 为渲染器产出的扇形图
  （B 叠加检测框与 "uuv 0.83" 标签）。`model=stub` 为无权重时的契约预期
- ✅ 契约对照：`shared/contract.md`（B 维护）与 `docs/shared-contract-v1.md` 逐行核对，
  表格/类型/签名/ID 完全一致（仅标题编号与列表格式差异），接口无分歧
- 样本预览：`ml/sonar/samples.png`（4×4，取自数据集）；数据集 321 MB 不入库，
  由 `python -m ml.sonar.gen_dataset --n 4000 --seed 0` 一键重跑

## C2 Mac 验收状态（2026-10-17，Lenovo 交付后）

- ✅ `ml/yolo/infer.py::SonarDetector` 按契约实现：构造加载一次权重、强制 CPU、
  灰度图内部转三通道、返回像素 bbox；权重缺失抛明确 `FileNotFoundError`（B 捕获后用桩）
- ✅ `ml/yolo/check_data.py`：用 Ultralytics **实际数据加载器**验证 `sonar.yaml`
  （非仅文本检查）→ train 3400 / val 600，负样本 435，类别 0–3 名称正确
- ✅ `ml/yolo/train.md`（Lenovo PowerShell / Colab 可重跑命令，含数据打包步骤）、
  `ml/yolo/eval.py`（mAP50 / mAP50-95 / 各类召回 / CPU 20 张均耗时 → metrics.json；
  **权重缺失直接报错退出，不写占位数据**）
- ✅ **Lenovo 训练交付已通过 Mac 验收**（`ml/yolo/ACCEPTANCE-MAC.md`）：ZIP 与 best.pt
  SHA256 逐项核对、MANIFEST 全部复算、类别顺序三处（classes.json / portable_data.yaml /
  checkpoint 内部 names）与契约逐字一致；600 张合成 val 实测
  **mAP50=0.9771（≥0.8 ✅）、CPU 49.7 ms/张（首测 52.1，<100ms ✅）**，与 Lenovo 端报告吻合；
  重启后端后 detection `model=yolo26n`（真实识别 det-5 uuv conf=0.72），
  `GET /api/metrics` 的 yolo 字段为 Mac 实测值
- ℹ️ 指标全部来自合成数据；真实声呐泛化与 UATD 迁移增益未做对照，不宣称

## C3 Agent 闭环状态（2026-10-17）

- ✅ `python -m agent.main` 启动 8001 服务，`GET /health` 与 `POST /ask` 可用；
  `/ask` 使用云端→本地→模板路由，硬预算 18 秒
- ✅ 订阅真实后端 `/ws`，首次连接和断线重连均用 `/api/events?since_seq=` 补事件；
  修复 REST `/api` 与 WS `/ws` 地址语义，支持后端重启后的 seq 回退
- ✅ `options_ready` 经确定性 REST 上下文收集（UTF-8 ≤ 3 KB）、pydantic 校验、
  上下文真实 ID 校验后，POST `/api/recommendations` 并由后端实时广播 `recommendation`
- ✅ 去重覆盖实时/补发重叠及已处理的相同方案载荷；方案指标变化时只保留最新任务；
  `alert_cleared`、场景 reset/start 会使排队和处理中旧任务失效
- ✅ `agent/prompts.py` 保存任务书原文系统提示词，云端和本地使用同一份上下文 JSON；
  草案六字段必填，拒绝空 JSON、缺/多字段、错类型、空正文、非 JSON 和任何非法 ID，
  只允许对合法长文本做契约截断；非法输出附错误重试一次
- ✅ 路由为云端→本地 Ollama→模板；事件总预算 9.5 秒并预留 0.5 秒 POST，
  SDK 隐式重试关闭，超时请求由协程取消；提交前继续检查场景代际和任务版本
- ✅ 云端已切到 OpenRouter 结构化路由（`google/gemini-2.5-flash`，json_schema strict +
  `require_parameters`，禁 fallback，SDK 不重试）；2026-10-17 隔离实测 20/20 次真实生成
  与 POST 全部 `model=cloud` 且首次结构/事实双合格（详见 agent/README.md）
- ✅ 本地仅使用已安装的 `qwen3:1.7b`，显式关闭思考并用 JSON Schema；
  `harborguard-lora` 尚未训练或部署。连续 20 次真实 POST：local 20、cloud 0、template 0，
  当时记录的结构与 ID 合格率为 20/20，平均 5.153 秒、最大 8.650 秒，全部低于 10 秒；
  该数字不再表述为自然语言事实合格率
- ✅ 无效云端凭证 + 本地不可达的隔离配置在 398 ms 内返回合法模板；
  不修改或输出真实凭证。不修改警报等级，不调用 `/api/decision`
- ✅ 在结构与 ID 后增加确定性事实检查：浮标离线数量/ID、覆盖数量、置信度、方案风险与
  延误、方案选择和证据不足；合法否定句不会因含“离线”误降级。健康状态分别统计结构
  合格、事实合格、事实失败、重试成功、模型成功和模板兜底
- ✅ 已补齐升到二级的 `alert_changed`、`reopen_plan`、down `buoy_changed`；计划按载荷去重并
  最多每 20 秒仿真时间一次，reset/start 清理去重、节流和过期任务
- ✅ 真实后端：场景 A 二级建议 `model=template`、9007.6 ms；浮标建议 `model=template`、
  9002.6 ms；场景 B 灾害建议 `model=local`、5136.3 ms。灾害/浮标推荐 ID 均为 null，
  evidence 全部为后端真实 ID；生成中 reset 后无迟到建议
- ✅ 明确事实矛盾的脱敏失败样例写入被忽略的 `agent/runtime/`，不自动混入蒸馏集；
  自由文本无法被规则完全验证，README 与 `/health` 均保留这一评估局限
- ⏸ 旧 Z.ai 账户 429 的问题由切换 OpenRouter 解决；本轮未再对旧服务发送付费探测

## C4 LoRA 蒸馏状态（2026-10-17）

- ✅ `ml/lora/gen_contexts.py`：合成上下文 500 条（seed=0 一键重跑，另有 80 条 seed=1 补充）。
  kind 70/20/10；risk = 加权和；ranked 符合「残余风险 ≤ 0.2 按延误升序在前」且与
  `factcheck.security_selection` 零冲突；全部使用真实 B1–B10 / 分区 / 资产 ID；
  每条经 `agent.context._trim` 压缩 ≤ 3 KB，与 C3 collect_* 输出同构；
  浮标失效的 coverage_impact 用真实浮标/分区几何复算；pytest 逐条锁定一致性
- ✅ `ml/lora/capture_real.py`：本机后端实跑场景 A/B 三轮（含一轮 `network_down` /
  `noise_up` / `buoy_down` 故障注入），按 C3 四类触发规则截取 **51 条唯一真实上下文**
  （security 23 / disaster 21 / buoy 7；offline 12 条）；旧会话失效警报计入 dropped 不入库
- ✅ `ml/lora/distill.py`：OpenRouter（gemini-2.5-flash 结构化输出）× C3 同一系统提示词、
  同一套校验（`parse_model_draft` + `check_draft_facts`），8 路并发；不合格附错误重试一次，
  仍失败做一次教师侧格式引导（引导文本只给教师、不入库，训练分布与运行时一致）。
  **合格率 95.2%**，实测总花费 ≈ $0.50；按「与路由器同序列化的 SHA256」幂等缓存，
  补跑/重试绝不重复请求已合格样本。合成精确 450/50 划分（seed=0）；
  51 条真实场景样本经 `--append-train` 只追加进训练集，测试集保持固定可比，
  **最终训练集 501 条 / 测试集 50 条**；AI 抽查（脚本复核）30 条：方案全对、
  无编造 ID、中文简洁（人工复核待负责人确认）
- ✅ `ml/lora/train_lora.ipynb`：Colab Unsloth + TRL SFT，rank 16 / alpha 32 / lr 2e-4 /
  3 epoch / max_len 4096 / bf16（不做 4-bit）；基座候选链 Qwen3.5-0.8B → Qwen3-1.7B → 0.6B
  （模型名以 Unsloth 文档为准，兼容问题自动降级）；只对 assistant 段计损失；
  导出 q4_k_m GGUF。`Modelfile`：`FROM ./harborguard.gguf`，temperature 0.2，
  系统提示词仍由请求携带（与训练一致）
- ✅ `ml/lora/eval.py`：50 条测试集串行评测，分模型分别报告：结构合法率（首次/重试后）、
  ID+事实合格率、有方案 security 的方案一致率（含分母）、disaster/buoy 的 null 推荐正确率、
  耗时；评测无模板兜底，失败计入分母不计成功。**配对原则**：`base` 是与 LoRA 同一基座的
  未微调 GGUF（`train_lora.ipynb` 成对导出，同量化/同模板/同参数），差异才能归因微调；
  qwen3:1.7b 单列为 system_baseline（当前系统兜底，规模不同）。配对两者齐才写
  `ml/lora/metrics.json`（后端 /api/metrics 读取）。
  系统基线实测（qwen3:1.7b，2026-10-17）：结构合法 100%/100%（首/重试后）、
  **ID+事实合格 16%**、方案一致 45.5%（n=33）、≈9.9 s/条 —— 结构满分主要来自
  Ollama schema 约束，事实层面缺口大，正是 LoRA 要补的（详见 ml/lora/README.md）
- ✅ `train_lora.ipynb` 训练前检查：基座只在「模型不存在」时按候选链降级且每次醒目留痕
  （写入 `training_meta.json`，含实际模型 ID/revision/精度/超参/token 审计），其他异常直接
  终止不静默换模型；GPU 支持 bf16 用 bf16、否则兼容 fp16（互斥、不硬编码，Qwen3.5 非 4-bit）；
  训练前审计 token 长度并断言 4096 不截断 assistant 答案；训练集尾部留 8 条验证切片，
  **test.jsonl 不进笔记本**；依赖按当前官方 Unsloth 指南（pip install unsloth）
- ⏸ **Colab 训练未跑**：无 GGUF、`harborguard-lora` 未部署、`metrics.json` 未生成
  （无 LoRA 不写占位数据，与 ml/yolo/eval.py 同约定）。LoRA 验收线：
  json_valid ≥ 0.90、option_agree ≥ 0.80、本地单条 ≤ 10 s、断网 `ollama run` 可用

## 不入库的内容（.gitignore）

`.env`、`.venv*/`、`ml/datasets/`（数据集，脚本可重跑）、`agent/runtime/`（脱敏失败样例）、
`runs/`、`*.log`（训练日志）、
`*.pt` / `*.pth` / `*.gguf` 等模型文件。
唯一例外：`ml/yolo/weights/best.pt` 为最终交付的 nano 权重（几 MB），已放行入库。


## A 前端与 B 后端已加入

前端源码位于 `frontend/`，后端源码、场景、测试位于 `backend/`、`data/`。完整说明分别见 [前端说明](frontend/README.md) 与 [后端说明](backend/README.md)。上方 C 的原有工作说明保留，C 的后续进度由其负责人更新。

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
make backend
# 测试 make test；录制回放 make record
```

Windows 已建好环境时执行 `./dev.ps1 backend`；安装依赖可用 `./dev.ps1 setup`。后端端口 8000，WebSocket 为 `ws://localhost:8000/ws`，接口文档为 `http://localhost:8000/docs`。

另开 PowerShell 启动前端：

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

实时页面为 `http://localhost:5173/`，后端不可用时可用 `?mock=1` 或 `?replay=demo_full.jsonl`。当前 A6 仍未标记完成，真实投影、断网刷新和录屏跨设备试播仍待人工验收。

共享契约字段维持 v1；B 的模型与样例在 `shared/`，并与 C 原有的 `docs/shared-contract-v1.md` 对照。A 的前端读取后端 REST / WS；C 的声呐与 Agent 实现完成后按冻结接口接入。回放在 `frontend/public/replay_a.jsonl`、`replay_b.jsonl`，配套图片在 `replay_assets/`。
