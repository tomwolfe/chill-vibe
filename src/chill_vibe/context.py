import sys
import json
from pathlib import Path
from typing import List, Optional

try:
    import git_dump
except ImportError:
    git_dump = None

class MissionContract:
    """Represents a structured mission for the coding agent."""
    def __init__(
        self, 
        objectives: List[str], 
        success_criteria: List[str], 
        agent_prompt: str,
        non_goals: Optional[List[str]] = None,
        checklist: Optional[List[str]] = None,
        forbidden_actions: Optional[List[str]] = None,
        summary: Optional[str] = None
    ):
        self.objectives = objectives
        self.success_criteria = success_criteria
        self.agent_prompt = agent_prompt
        self.non_goals = non_goals or []
        self.checklist = checklist or []
        self.forbidden_actions = forbidden_actions or []
        self.summary = summary or ""

    @classmethod
    def from_json(cls, json_str: str, agent_prompt: str):
        try:
            data = json.loads(json_str)
            return cls(
                objectives=data.get("objectives", []),
                success_criteria=data.get("success_criteria", []),
                agent_prompt=agent_prompt,
                non_goals=data.get("non_goals", []),
                checklist=data.get("checklist", []),
                forbidden_actions=data.get("forbidden_actions", []),
                summary=data.get("summary", "")
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid mission JSON: {e}")

    def validate(self):
        """Validate that the mission contract is complete and testable."""
        if not isinstance(self.objectives, list) or not self.objectives:
            return False, "Mission must have at least one objective as a list of strings."
        
        if not isinstance(self.success_criteria, list) or not self.success_criteria:
            return False, "Mission must have at least one success criterion as a list of strings."
        
        if not isinstance(self.agent_prompt, str) or not self.agent_prompt.strip():
            return False, "Mission must have a non-empty agent prompt."

        # Validate success criteria formats
        valid_prefixes = ["exists:", "contains:", "not_contains:", "pytest", "ruff", "no_new_files"]
        for criterion in self.success_criteria:
            if not isinstance(criterion, str):
                return False, f"Success criterion must be a string: {criterion}"
            
            # Check if it's one of our known prefixes or just a shell command
            # For shell commands, we don't have a strict format, but we can warn if they look like typos of prefixes
            if ":" in criterion:
                prefix = criterion.split(":", 1)[0] + ":"
                if prefix not in valid_prefixes and not any(criterion.startswith(p) for p in valid_prefixes):
                    # It might be a complex shell command, but if it starts with something like "exist:" (typo), we should catch it
                    pass

        return True, ""

def run_git_dump(repo_path, output_file, exclude_patterns=None, depth=None, include_ext=None):
    """Phase A: Context Extraction"""
    repo_path_obj = Path(repo_path)
    git_dir = repo_path_obj / ".git"
    
    if not git_dir.exists() or not git_dir.is_dir():
        print(f"[!] Warning: {repo_path} is not a valid git repository. Falling back to standard folder processing.")
    
    print(f"[*] Extracting codebase context from {repo_path}...")
    try:
        from git_dump.core import RepoProcessor
        
        include_patterns = None
        if include_ext:
            include_patterns = [f"*.{ext.strip()}" for ext in include_ext.split(",")]
            
        processor = RepoProcessor(
            str(repo_path_obj), 
            output_file, 
            ignore_patterns=exclude_patterns,
            include_patterns=include_patterns
        )
        
        processor.process()
    except Exception as e:
        print(f"Error running git-dump: {e}")
        sys.exit(1)
