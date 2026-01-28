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

# 2. Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "[*] Installing Python dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "[*] requirements.txt not found. Installing google-genai manually..."
    pip install google-genai
fi

# 3. Make chill-vibe.py executable
chmod +x chill-vibe.py

echo "[*] Setup complete. Use './chill-vibe.py [path]' to start the pipeline."
echo "[*] Note: Remember to activate the virtual environment with 'source .venv/bin/activate' before running the script if you're not using the full path."
