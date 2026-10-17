"""ml.lora —— 蒸馏数据、LoRA 训练、GGUF 导出与评估（C4）。

- gen_contexts.py: 生成与 C3 同构的上下文 JSON（python -m ml.lora.gen_contexts）
- capture_real.py: 从运行中的 B 后端截取真实上下文（python -m ml.lora.capture_real）
- distill.py: OpenRouter 云端蒸馏 -> JSONL（python -m ml.lora.distill）
- train_lora.ipynb: Colab 训练笔记本（Unsloth + TRL SFT）
- Modelfile: ollama create harborguard-lora -f ml/lora/Modelfile
- eval.py: 基座 vs LoRA 对比 -> metrics.json（python -m ml.lora.eval）
- datasets/ 已被 gitignore，全部可由脚本重跑生成
"""
