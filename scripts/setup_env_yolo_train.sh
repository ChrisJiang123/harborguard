#!/usr/bin/env bash
# ============================================================================
# 环境二：YOLO26 训练环境（Linux bash 脚本）
#
# ⚠️ 未验证：本脚本未在 Windows 上运行（Windows 请用 requirements-yolo-train.txt
#    头部的 PowerShell 说明），也从未实际执行过；Lenovo 的已验证环境是按
#    requirements 文件头部记录的实测版本手工安装的。
#
# 可配置项（环境变量）：
#   PYTHON_VERSION   默认 3.12（Lenovo 实测 3.12.10；MacBook 运行环境仍用 3.11）
#   YOLO_CUDA_INDEX  torch 安装源 cuXX，默认 cu130（Lenovo 实测值；
#                    其他机器按本机驱动修改，不作为强制配置）
#
# 用法示例：
#   PYTHON_VERSION=3.12 YOLO_CUDA_INDEX=cu130 bash scripts/setup_env_yolo_train.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

PY_VER="${PYTHON_VERSION:-3.12}"
CUDA_INDEX="${YOLO_CUDA_INDEX:-cu130}"

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[yolo-train] 检测到 NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
else
  echo "[yolo-train] 未检测到 NVIDIA GPU。"
  echo "  - MacBook：跳过本地训练环境（运行环境 .venv 已含 CPU 推理所需依赖）"
  echo "  - Colab：直接 pip install -r requirements-yolo-train.txt"
  echo "  - Windows：用 requirements-yolo-train.txt 头部的 PowerShell 说明"
  exit 0
fi

PY="python${PY_VER}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

if [ ! -d .venv-yolo-train ]; then
  "$PY" -m venv .venv-yolo-train
fi
# CUDA 版 torch（源可配置，默认 Lenovo 实测 cu130）
./.venv-yolo-train/bin/pip install torch torchvision --index-url "https://download.pytorch.org/whl/${CUDA_INDEX}"
./.venv-yolo-train/bin/pip install -r requirements-yolo-train.txt
./.venv-yolo-train/bin/python -c "import torch; print('[yolo-train] cuda 可用:', torch.cuda.is_available())"
