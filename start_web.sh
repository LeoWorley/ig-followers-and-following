#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$ROOT_DIR/venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "venv Python not found. Run: ./setup.sh" >&2
  exit 1
fi

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8088}"

exec "$PYTHON" -m uvicorn web_app:app --host "$WEB_HOST" --port "$WEB_PORT"
