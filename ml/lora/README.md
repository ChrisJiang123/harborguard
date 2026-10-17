# ml/lora —— LoRA 蒸馏与本地小模型（C4，待实现）

断网时由 Ollama 本地模型 `harborguard-lora` 接管 Agent 建议。

## 环境说明（与运行环境、YOLO 训练环境分开）

- **目标机器：Colab 或经验证可用的 Lenovo CUDA 环境；当前尚未验证训练 GPU。**
- Unsloth 在 macOS 上不可用，训练不放在 MacBook。
- 安装：`pip install -r requirements-lora-train.txt`（装完重启 runtime / 激活环境）。
- 基座：Qwen3.5 小尺寸（先 0.8B）；兼容问题换 Qwen3 1.7B（对应本机 Ollama 预拉基座 `qwen3:1.7b`）。
- bf16 LoRA（rank 16 / alpha 16–32 / lr 2e-4 / 2–3 epoch / max_len 4096），不做 4-bit 训练。

## 计划产物（C4）

| 文件 | 说明 |
| --- | --- |
| `gen_contexts.py` | 生成 500 个上下文 JSON（与 C3 格式一致） |
| `distill.py` | 云端模型蒸馏 -> JSONL（450 训练 / 50 测试） |
| `train_lora.ipynb` | Colab 训练笔记本（Unsloth + TRL SFT） |
| `Modelfile` | `FROM ./harborguard.gguf`，temperature 0.2 |
| `eval.py` | 基座 vs LoRA 对比 -> `metrics.json` |

部署：`ollama create harborguard-lora -f ml/lora/Modelfile`。
GGUF / 权重文件已被 .gitignore 忽略，不入库。
