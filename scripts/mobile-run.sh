#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/mobile"

echo "[mobile] Running flutter pub get"
flutter pub get

echo "[mobile] Starting flutter run"
flutter run