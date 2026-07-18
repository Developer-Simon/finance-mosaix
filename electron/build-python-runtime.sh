#!/usr/bin/env bash
set -e

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
RUNTIME_DIR="$ROOT_DIR/electron/python-runtime"

rm -rf "$RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"

echo "Creating Python virtual environment in $RUNTIME_DIR"
$PYTHON -m venv "$RUNTIME_DIR"

source "$RUNTIME_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
# Non-editable install: an editable install (`-e`) only writes a path finder
# pointing back at this checkout, which breaks once the runtime is moved to
# another machine. Install a real copy instead so the runtime is relocatable.
python -m pip install --no-cache-dir "$ROOT_DIR"
deactivate

echo "Python runtime bundle created at $RUNTIME_DIR"
