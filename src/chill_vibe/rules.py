import os
from pathlib import Path
from typing import Optional

def get_global_rules() -> Optional[str]:
    """Look for .chillvibe_rules.md in the current directory and return its content."""
    rules_file = Path(".chillvibe_rules.md")
    if rules_file.exists():
        try:
            return rules_file.read_text()
        except Exception as e:
            print(f"[!] Warning: Could not read {rules_file}: {e}")
    return None
