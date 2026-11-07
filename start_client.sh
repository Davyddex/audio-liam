#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi
exec "$PYTHON" "$SCRIPT_DIR/client.py" "$@"
