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
        if not self.objectives:
            return False, "Mission must have at least one objective."
        if not self.success_criteria:
            return False, "Mission must have at least one success criterion."
        if not self.agent_prompt:
            return False, "Mission must have an agent prompt."
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
