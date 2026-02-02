#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x "./venv/bin/python" ]]; then
  echo "Virtual environment not found. Run ./setup.sh first."
  exit 1
fi

echo "Starting login-only flow (visible browser)..."
LOGIN_ONLY_MODE=true HEADLESS_MODE=false ./venv/bin/python ./main.py
echo "Done. Cookie should be stored in instagram_cookies.json."
