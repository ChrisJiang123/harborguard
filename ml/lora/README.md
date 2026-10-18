# ml/lora —— LoRA 蒸馏与本地小模型（C4）

断网时由 Ollama 本地模型 `harborguard-lora` 接管 Agent 建议。
蒸馏教师使用 C3 同一提示词与同一套校验（结构 + ID + 确定性事实），
本地路由、请求格式与 C3 运行时完全一致。

## 环境说明（与运行环境、YOLO 训练环境分开）

- **正式训练已在 Lenovo/Windows 完成**；Mac 仅做 GGUF/Ollama 接入与评估，本轮不重训。
  可重跑笔记本为 `train_lora.ipynb`，环境依赖见 `requirements-lora-train.txt`。
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
| ③ Colab 训练 | 上传 `train.jsonl` 跑 `train_lora.ipynb` | 配对 GGUF：`harborguard.gguf` + `harborguard-base.gguf`（同量化），`harborguard-lora-adapter/`（适配器+tokenizer）与 `training_meta.json`（实际模型 ID/revision/精度/超参/token 审计） |
| ④ 本地部署 | `cd ml/lora && ollama create harborguard-lora -f Modelfile && ollama create harborguard-base -f Modelfile.base` | Ollama 模型 `harborguard-lora` + 配对 `harborguard-base` |
| ⑤ 对比评估 | `python -m ml.lora.eval`（`--skip-lora` 只评系统基线） | `metrics.json`（后端 `/api/metrics` 的 lora 字段） |

## 当前状态（2026-10-17）

- ✅ 生成器/蒸馏/截取/评估四脚本 + pytest（`tests/test_lora_*.py`）
- ✅ 训练集 **501 条** = 450 合成（精确 450/50 划分，seed=0）+ 51 条真实场景样本
  （`--append-train` 只进训练集）；测试集固定 50 条合成样本，不参与训练与提示词改动
- ✅ Lenovo 实际将这 501 条按文件顺序分为前 493 条正式训练与末 8 条内部验证；
  构成为训练 450 合成 + 43 真实、内部验证 8 真实。独立 test50 与二者均零精确重复。
- ✅ 蒸馏：OpenRouter（gemini-2.5-flash 结构化输出），合成 552/580 = 95.2% 合格，
  真实 51/51 = 100% 合格；实测总花费 ≈ $0.55
- ✅ 真实上下文 51 条（security 23 / disaster 21 / buoy 7；network offline 12 条，
  来自真实故障注入），来源：本机后端场景 A/B 三轮实跑 + inject 故障
- ✅ 系统基线（qwen3:1.7b + 提示词，50 条测试集，串行含一次重试，2026-10-17 复测）：
  **结构合法 100%/100%（首/重试后），ID+事实合格 16%/16%，方案一致 45.5%（n=33），
  null 推荐正确 100%（n=14），≈9.9 s/条**。
  结构 100% 主要来自 Ollama json_schema 约束（与 C3 运行时同构）；但通过 C3 全套
  确定性事实校验（离线数量/ID、覆盖、置信度、方案规则等）的只有 16% ——
  旧口径 `json_valid=0.96` 只含结构+ID，事实缺口此前不可见。
  注意：这是「当前系统基线」，与 0.8B 级 LoRA 的对比必须经过
  **配对基座**（同一基座的未微调 GGUF，同量化/同模板/同参数），规模差异不能归因微调
- ✅ **AI 抽查**（脚本复核）30 条蒸馏样本：方案全部与 ranked[0]（或 null）一致、
  无编造 ID、中文简洁（摘要 ≤60 字、说明 ≤300 字）；**人工复核待负责人确认**
- ✅ `metrics.json` 已生成：format=json 下 test50 结构 50/50、事实 44/50、
  方案 31/33、null 14/14、平均 3.75 s；confirm60 另列为结构 60/60、事实 39/60、
  方案 35/36、null 18/18、平均 4.71 s。两组均是合成上下文，不代表真实海域效果。

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

## 线上切换与回退（2026-10-17，C4 format=json 候选）

当前 .env：`OLLAMA_MODEL=harborguard-lora` + `OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json`。
完整 schema 约束下该 LoRA 在 Mac/Ollama grammar 解码中循环不终止（见 ml/lora/metrics.json
的 `history_schema_mode`），故本模型以 `format=json` 运行；qwen3:1.7b 等未列入覆盖表的模型
仍走完整 schema。回退：`OLLAMA_MODEL=qwen3:1.7b`、清空 `OLLAMA_FORMAT_OVERRIDES`，
重启 Agent（`python -m agent.main`）并检查 `GET :8001/health`。这一回退路径有单测与配置备份，
但尚未实际演练“切回 qwen3 后再切回 LoRA”，不得记为已验证回退。
部署注意：若未来改用原生 llama.cpp 运行 LoRA，schema 必须保持 pydantic 声明序（勿排序键）。

## 来源审计补充（2026-10-17）

可重跑脚本与逐文件 SHA256 见 [来源审计](../../acceptance_c4/data_provenance_20261017/README.md)。
test50 可由合成蒸馏记录同序重建，原“capture_real 真实采集 test”仅为标签错误；
没有发现测试集更换或与训练输入的精确上下文重叠。confirm60 也与训练输入和 test50 零精确重复。
`capture_real` 是本机仿真后端运行截取，不是物理声呐实采；缺少逐条 capture-run ID，
无法从该文件单独证明三次采集的批次边界。精确去重不能证明语义独立。
原两组指标和完整 schema 失败归档保留；没有重新训练、调参或重跑整套模型评估。
