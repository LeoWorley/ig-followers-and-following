#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "venv Python not found. Run: ./setup.sh" >&2
  exit 1
fi

nohup "$PY" "$ROOT_DIR/gui_app.py" >/dev/null 2>&1 &
echo "GUI started in background."
