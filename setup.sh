#!/bin/bash
set -e

echo "[*] chill-vibe: Setting up environment..."

# 1. Handle Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "[*] Activating virtual environment..."
source .venv/bin/activate

# 2. Install the package in editable mode
echo "[*] Installing chill-vibe in editable mode..."
pip install --upgrade pip
pip install -e .

echo "[*] Setup complete. Use 'chill-vibe [path]' to start the pipeline."
echo "[*] Note: Remember to activate the virtual environment with 'source .venv/bin/activate' before running."