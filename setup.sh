#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python"
RUN_LOGIN_ONLY=false
SKIP_INSTALL=false

for arg in "$@"; do
  case "$arg" in
    --login-only) RUN_LOGIN_ONLY=true ;;
    --skip-install) SKIP_INSTALL=true ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: ./setup.sh [--login-only] [--skip-install]"
      exit 1
      ;;
  esac
done

resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  echo "Python not found. Install Python 3.10+ first." >&2
  exit 1
}

echo "Project root: $ROOT_DIR"

if [[ ! -x "$VENV_PY" ]]; then
  PY_CMD="$(resolve_python)"
  echo "Creating virtual environment..."
  "$PY_CMD" -m venv "$VENV_DIR"
fi

if [[ "$SKIP_INSTALL" != "true" ]]; then
  echo "Installing dependencies..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r "$ROOT_DIR/requirements.txt"
fi

if [[ -f "$ROOT_DIR/.env.example" && ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created .env from .env.example. Update credentials before running."
fi

mkdir -p "$ROOT_DIR/reports" "$ROOT_DIR/exports"

if [[ "$RUN_LOGIN_ONLY" == "true" ]]; then
  echo "Running login-only flow (visible browser)..."
  LOGIN_ONLY_MODE=true HEADLESS_MODE=false "$VENV_PY" "$ROOT_DIR/main.py"
fi

echo
echo "Setup complete."
echo "Next steps:"
echo "1) Edit .env with IG_USERNAME / IG_PASSWORD / TARGET_ACCOUNT"
echo "2) First login: ./venv/bin/python main.py (with LOGIN_ONLY_MODE=true, HEADLESS_MODE=false)"
echo "3) Start GUI: ./start_gui.sh"
