#!/usr/bin/env bash
# ============================================================================
# Runtime .venv for the MacBook development/demo host.
# Agent, render_ping and SonarDetector CPU inference.
# Prefer uv: Homebrew Python pip/truststore failed on the recorded macOS26 host.
# Other machines fall back to standard Python3.11 and pip.
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

./.venv/bin/python -c "import fastapi, ultralytics, anthropic, openai; print('[runtime] Dependencies installed')"

# Create .env only when absent.
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[runtime] Created .env from .env.example; fill credentials locally (never commit it)"
fi

echo "[runtime] Self-check: ./.venv/bin/python scripts/check_c0.py"
