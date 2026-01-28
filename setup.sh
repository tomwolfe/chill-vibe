#!/bin/bash
set -e

echo "[*] chill-vibe: Setting up environment..."

# 1. Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "[*] Installing Python dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "[*] requirements.txt not found. Installing google-genai manually..."
    pip install google-genai
fi

# 2. Make chill-vibe.py executable
chmod +x chill-vibe.py

echo "[*] Setup complete. Use ./chill-vibe.py [path] to start the pipeline."
