import shutil
from pathlib import Path
from typing import List, Tuple

def validate_success_criteria(criteria: List[str], repo_path: str) -> Tuple[bool, List[str]]:
    """
    Validate that success criteria are syntactically valid and tools are available.
    Returns (is_valid, error_messages).
    """
    errors = []
    
    for criterion in criteria:
        criterion = criterion.strip()
        
        # Check for existence criteria
        if criterion.startswith("exists:"):
            path_str = criterion[len("exists:"):].strip()
            full_path = Path(repo_path) / path_str
            parent = full_path.parent
            if not parent.exists():
                errors.append(f"Criterion '{criterion}' is impossible: parent directory '{parent}' does not exist.")
        
        # Check for tool-based criteria
        elif any(tool in criterion for tool in ["pytest", "ruff", "mypy", "npm", "node", "python"]):
            # Extract the tool name (simplified)
            tool = criterion.split()[0]
            if not shutil.which(tool):
                errors.append(f"Criterion '{criterion}' requires tool '{tool}' which is not installed in the environment.")
        
        # Add more specific checks as needed (e.g., 'contains:', 'not_contains:')
        elif criterion.startswith("contains:") or criterion.startswith("not_contains:"):
            parts = criterion.split(" ", 1)
            if len(parts) < 2:
                errors.append(f"Criterion '{criterion}' is malformed. Expected 'contains:path regex'")
            else:
                target_path_str = parts[0].split(":", 1)[1]
                full_path = Path(repo_path) / target_path_str
                # We don't check if the file exists yet (as the agent will create it), 
                # but we check if the path is at least valid.
                try:
                    full_path.parent.resolve()
                except Exception:
                    errors.append(f"Criterion '{criterion}' has an invalid path structure.")

    return len(errors) == 0, errors

def run_preflight_check(criteria: List[str], repo_path: str) -> bool:
    """Run pre-flight validation and print errors if any."""
    print("[*] Running pre-flight verification...")
    is_valid, errors = validate_success_criteria(criteria, repo_path)
    
    if not is_valid:
        print("[!] Pre-flight validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("[✓] Pre-flight verification passed.")
    return True
