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

# 2. Check for git-dump
GIT_DUMP_PATH="../git_dump/git_dump.py"
if [ -f "$GIT_DUMP_PATH" ]; then
    echo "[*] Found git-dump at $GIT_DUMP_PATH"
else
    echo "[!] Warning: ../git_dump/git_dump.py not found."
    echo "    Make sure it is available for context extraction."
fi

# 3. Make chill-vibe.py executable
chmod +x chill-vibe.py

echo "[*] Setup complete. Use ./chill-vibe.py [path] to start the pipeline."
