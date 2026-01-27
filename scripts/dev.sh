#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[dev] Checking Ollama at http://localhost:11434/api/tags..."
if curl -sSf "http://localhost:11434/api/tags" >/dev/null 2>&1; then
  echo "[dev] Ollama is reachable."
else
  echo "[dev] WARNING: Ollama does not appear to be running at http://localhost:11434."
  echo "[dev] Start it with: ollama serve"
fi

echo "[dev] Starting backend on http://0.0.0.0:8000 ..."
echo "[dev] Health:  http://127.0.0.1:8000/health"
echo "[dev] Docs:    http://127.0.0.1:8000/docs"

exec "${ROOT_DIR}/scripts/backend-dev.sh"