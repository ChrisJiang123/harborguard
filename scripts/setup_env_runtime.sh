#!/usr/bin/env bash
# ============================================================================
# 环境一：运行环境 .venv（MacBook 开发与演示主机）
# 用途：Agent 服务 + render_ping + SonarDetector CPU 推理
# 优先用 uv（本 MacBook 的 macOS 26 上 brew Python 的 pip/truststore 会崩），
# 其他机器回落到标准 python3.11 + pip。
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

PY_VER="${PYTHON_VERSION:-3.11}"

if command -v uv >/dev/null 2>&1; then
  echo "[runtime] uv venv --python ${PY_VER} .venv"
  uv venv --python "${PY_VER}" .venv
  uv pip install --python .venv/bin/python -r requirements-runtime.txt
else
  PY=python${PY_VER}
  command -v "$PY" >/dev/null 2>&1 || PY=python3
  echo "[runtime] $PY -m venv .venv"
  "$PY" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip
  ./.venv/bin/pip install -r requirements-runtime.txt
fi

./.venv/bin/python -c "import fastapi, ultralytics, anthropic, openai; print('[runtime] 依赖安装完成')"

# 生成 .env（若不存在）
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[runtime] 已从 .env.example 生成 .env，请编辑填写密钥（不会提交）"
fi

echo "[runtime] 自检：./.venv/bin/python scripts/check_c0.py"
