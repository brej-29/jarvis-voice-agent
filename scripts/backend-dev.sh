#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/backend"

if [ ! -d ".venv" ]; then
  echo "[backend-dev] Creating virtualenv in backend/.venv"
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  else
    python -m venv .venv
  fi
fi

# shellcheck source=/dev/null
. .venv/bin/activate

if ! python -m pip show fastapi >/dev/null 2>&1; then
  echo "[backend-dev] Installing dependencies from requirements.txt"
  pip install --upgrade pip
  pip install -r requirements.txt
fi

echo "[backend-dev] Starting uvicorn on http://0.0.0.0:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload