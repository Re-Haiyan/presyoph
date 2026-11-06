#!/usr/bin/env bash
# PresyoPH launcher for macOS/Linux: sets up the environment on first run, then starts the app.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 was not found. Install Python 3.10-3.12 from https://www.python.org/downloads/" >&2
    exit 1
fi

if [ ! -x "venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Checking packages (the first run downloads them and can take a few minutes)..."
venv/bin/python -m pip install -q -r requirements.txt

echo "Starting PresyoPH at http://localhost:8501  (press Ctrl+C to stop)"
exec venv/bin/python -m streamlit run app.py
