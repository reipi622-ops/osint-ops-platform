#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt --quiet --no-warn-script-location --break-system-packages 2>&1 | tail -5
export PORT="${PORT:-8080}"
echo "Starting OSINT Platform API on port $PORT..."
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload --log-level info
