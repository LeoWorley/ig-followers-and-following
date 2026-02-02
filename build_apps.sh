#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x "./venv/bin/python" ]]; then
  echo "Virtual environment not found. Run ./setup.sh first."
  exit 1
fi

PYTHON="./venv/bin/python"

if [[ "${1:-}" != "--skip-install" ]]; then
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install pyinstaller
fi

echo "Building GUI app..."
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed --name ig-tracker-gui gui_app.py

echo "Building tray app..."
"$PYTHON" -m PyInstaller --noconfirm --clean --windowed --name ig-tracker-tray tray_app.py

echo "Building tracker CLI..."
"$PYTHON" -m PyInstaller --noconfirm --clean --name ig-tracker-cli main.py

echo "Build complete. Binaries are in ./dist"
