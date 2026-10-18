"""C4 distillation, LoRA training, GGUF export and evaluation. gen_contexts synthesizes C3-shaped JSON;
capture_real records a running simulation backend; distill generates cloud-teacher JSONL;
train_lora.ipynb trains with Unsloth/TRL; eval compares base/LoRA metrics. Ignored datasets are
reproducible by scripts.
"""
