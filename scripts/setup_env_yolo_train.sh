#!/usr/bin/env bash
# ============================================================================
# YOLO26 training environment helper (Linux bash).
#
# UNVERIFIED: not executed on Windows; use the PowerShell notes in
# requirements-yolo-train.txt. The validated Lenovo environment was installed
# manually with the recorded versions in that requirements file.
#
# Environment settings:
# PYTHON_VERSION defaults3.12 (Lenovo3.12.10; MacBook runtime3.11).
# YOLO_CUDA_INDEX selects torch cuXX, defaultcu130 recorded on Lenovo;
# choose the correct index for the local driver, not a universal requirement.
#
# Example:
#   PYTHON_VERSION=3.12 YOLO_CUDA_INDEX=cu130 bash scripts/setup_env_yolo_train.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

PY_VER="${PYTHON_VERSION:-3.12}"
CUDA_INDEX="${YOLO_CUDA_INDEX:-cu130}"

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[yolo-train] Detected NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
else
  echo "[yolo-train] No NVIDIA GPU detected."
  echo "  - MacBook: skip training setup; runtime .venv includes CPU inference dependencies."
  echo "  - Colab: run pip install -r requirements-yolo-train.txt."
  echo "  - Windows: follow the PowerShell notes in requirements-yolo-train.txt."
  exit 0
fi

PY="python${PY_VER}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

if [ ! -d .venv-yolo-train ]; then
  "$PY" -m venv .venv-yolo-train
fi
# CUDA torch from a configurable index; defaultcu130 is the recorded Lenovo value.
./.venv-yolo-train/bin/pip install torch torchvision --index-url "https://download.pytorch.org/whl/${CUDA_INDEX}"
./.venv-yolo-train/bin/pip install -r requirements-yolo-train.txt
./.venv-yolo-train/bin/python -c "import torch; print('[yolo-train] CUDA available:', torch.cuda.is_available())"
