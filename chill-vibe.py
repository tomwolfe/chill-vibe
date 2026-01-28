#!/usr/bin/env python3
import sys
import os

# Add src to sys.path to allow imports from chill_vibe package without installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from chill_vibe.cli import main
except ImportError as e:
    print(f"Error: Could not import chill_vibe package: {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()