#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m venv "$PROJECT_ROOT/.venv" --system-site-packages
source "$PROJECT_ROOT/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$PROJECT_ROOT/requirements.txt"

case "$(uname -m)" in
  aarch64|arm64)
    echo "ARM64 detected. Keep the torch package supplied by the matching JetPack installation."
    ;;
  *)
    echo "Environment ready in $PROJECT_ROOT/.venv"
    ;;
esac

echo "Run with: source .venv/bin/activate && python upgrade.py"
