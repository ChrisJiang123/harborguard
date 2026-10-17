#!/usr/bin/env bash
# ============================================================================
# 环境二：YOLO26 训练环境 .venv-yolo-train
# 只在有 GPU 的机器上执行（Lenovo / 本地 NVIDIA GPU）。Colab 直接用
# requirements-yolo-train.txt，无需本脚本。
# MacBook 无 NVIDIA GPU：请勿在本机训练，本脚本会拒绝执行。
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[yolo-train] 检测到 NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
else
  echo "[yolo-train] 未检测到 NVIDIA GPU。"
  echo "  - MacBook：跳过本地训练环境（运行环境 .venv 已含 CPU 推理所需依赖）"
  echo "  - Colab：新建 notebook 后直接 pip install -r requirements-yolo-train.txt"
  exit 0
fi

PY=python3.11
command -v "$PY" >/dev/null 2>&1 || PY=python3

if [ ! -d .venv-yolo-train ]; then
  "$PY" -m venv .venv-yolo-train
fi
# CUDA 版 torch（按机器驱动调整 cu121/cu124，见 pytorch.org）
./.venv-yolo-train/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
./.venv-yolo-train/bin/pip install -r requirements-yolo-train.txt
./.venv-yolo-train/bin/python -c "import torch; print('[yolo-train] cuda 可用:', torch.cuda.is_available())"
