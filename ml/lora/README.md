# ml/lora —— LoRA 蒸馏与本地小模型（C4）

断网时由 Ollama 本地模型 `harborguard-lora` 接管 Agent 建议。
蒸馏教师使用 C3 同一提示词与同一套校验（结构 + ID + 确定性事实），
本地路由、请求格式与 C3 运行时完全一致。

## 环境说明（与运行环境、YOLO 训练环境分开）

- **训练在 Colab**（Unsloth 在 macOS 不可用；Windows WSL 方案以后再修，不阻塞）。
  安装见 `requirements-lora-train.txt`；笔记本 `train_lora.ipynb` 自带安装 cell。
- 基座：Qwen3.5 小尺寸（先 0.8B，模型名以 Unsloth 文档为准）；笔记本内置候选链，
  兼容问题自动落到 Qwen3 1.7B / 0.6B（对应本机已拉基座 `qwen3:1.7b`）。
- bf16 LoRA（rank 16 / alpha 32 / lr 2e-4 / 3 epoch / max_len 4096），不做 4-bit 训练。

## 管线（全部可重跑；datasets/ 不入库）

| 步骤 | 命令 | 产物 |
| --- | --- | --- |
| ① 合成上下文 | `python -m ml.lora.gen_contexts --n 500 --seed 0` | `datasets/contexts.jsonl`（500 条，kind 70/20/10，≤3 KB，risk=加权和，ranked 符合任务书规则，真实 B1–B10/分区/资产 ID） |
| ①b 真实上下文 | 后端跑场景时 `python -m ml.lora.capture_real --seconds 235` | `datasets/real_contexts.jsonl`（C3 触发规则截取，key 去重追加） |
| ② 云端蒸馏 | `python -m ml.lora.distill`（8 路并发；`--limit` 冒烟、`--retry-failed` 重试失败） | `datasets/distilled.jsonl`（合格样本+元数据）、`distill_failures.jsonl` |
| ②b 补充蒸馏 | `python -m ml.lora.distill --contexts datasets/real_contexts.jsonl --append-train` | 只蒸馏新增；新样本**只追加进训练集**，测试集保持合成基准 |
| ③ Colab 训练 | 上传 `train.jsonl` 跑 `train_lora.ipynb` | `harborguard.gguf`（q4_k_m） |
| ④ 本地部署 | `cd ml/lora && ollama create harborguard-lora -f Modelfile` | Ollama 模型 `harborguard-lora` |
| ⑤ 对比评估 | `python -m ml.lora.eval`（`--skip-lora` 只评基座） | `metrics.json`（后端 `/api/metrics` 的 lora 字段） |

## 当前状态（2026-10-17）

- ✅ 生成器/蒸馏/截取/评估四脚本 + pytest（`tests/test_lora_*.py`）
- ✅ 训练集 **501 条** = 450 合成（精确 450/50 划分，seed=0）+ 51 条真实场景样本
  （`--append-train` 只进训练集）；测试集固定 50 条合成样本
- ✅ 蒸馏：OpenRouter（gemini-2.5-flash 结构化输出），合成 552/580 = 95.2% 合格，
  真实 51/51 = 100% 合格；实测总花费 ≈ $0.55
- ✅ 真实上下文 51 条（security 23 / disaster 21 / buoy 7；network offline 12 条，
  来自真实故障注入），来源：本机后端场景 A/B 三轮实跑 + inject 故障
- ✅ 基座评测（qwen3:1.7b + 提示词，50 条测试集，串行含一次重试）：
  **json_valid=0.96，option_agree=0.455，latency≈4.9 s**
- ✅ 人工抽查 30 条蒸馏样本：方案全部与 ranked[0]（或 null）一致、无编造 ID、
  中文简洁（摘要 ≤60 字、说明 ≤300 字）
- ⏸ `metrics.json` 未生成：等 `harborguard-lora` 部署后跑 `python -m ml.lora.eval`
  一次性写入（无 LoRA 不写占位数据，与 ml/yolo/eval.py 同约定）
- ⏸ Colab 训练待跑（LoRA 验收线：json_valid ≥ 0.90、option_agree ≥ 0.80、单条 ≤ 10 s）

## 设计要点

- **训练分布 = 运行分布**：入库样本恒为标准三段 messages（system/user/assistant），
  user 消息与 `agent.router.generate` 逐字节同序列化（sort_keys + 紧凑分隔符）；
  引导重试（GUIDED_HINT）只出现在给教师的重试消息里，不入库。
- **幂等**：上下文以「与路由器一致的序列化」的 SHA256 为键；已合格样本与已记录失败
  都跳过，绝不重复请求（补充蒸馏/重跑零浪费）。
- **校验 = C3 全套**：`parse_model_draft`（结构 + ID 存在性）+
  `check_draft_facts`（浮标离线/覆盖/置信度/方案规则等确定性事实），不合格重试至多
  两次（第二次附格式引导），三次全失败才记失败。
- **测试集固定**：450/50 由 `split_records`（seed=0）确定性划分；真实场景补充样本
  经 `--append-train` 只进训练集，保证基座/LoRA 对比始终在同一测试集上可比。

## 真实上下文（2026-10-17 本机后端实测）

场景 A（speed 10）+ 场景 B 三轮实跑，其中一轮注入 `network_down/up`、`noise_up`、
`buoy_down B2`：`capture_real` 收到 options_ready / alert_changed / reopen_plan /
buoy_changed 全部四类事件，截取 **51 条唯一真实上下文**（security 23 / disaster 21 /
buoy 7；offline 12 条），走 C3 同一 collect_* 代码路径（UTF-8 ≤ 3 KB）。
固定种子的场景重复跑会产生重复事件，脚本按 key 去重、跳过已有；
事件缓存里旧会话的失效警报计入 dropped（HTTPStatusError 39/36/36），不入库。
