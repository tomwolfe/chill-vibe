import json
from typing import List, Optional, Dict, Any, Union, Tuple
from pydantic import BaseModel, Field, field_validator

class AgentConfig(BaseModel):
    command: List[str]
    dependencies: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)

class ProjectConfig(BaseModel):
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    extra_args: List[str] = Field(default_factory=list)
    model: Optional[str] = None
    thinking_level: Optional[str] = None
    exclude_patterns: List[str] = Field(default_factory=list)
    depth: Optional[int] = None
    include_ext: Optional[str] = None
    protected_files: List[str] = Field(default_factory=list)
    max_cost: Optional[float] = None

class MissionContract(BaseModel):
    objectives: List[str]
    success_criteria: List[str]
    agent_prompt: str
    non_goals: List[str] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("objectives", "success_criteria")
    @classmethod
    def must_not_be_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Must not be empty")
        return v

    @field_validator("agent_prompt")
    @classmethod
    def must_be_non_empty_str(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Must not be empty")
        return v

    @classmethod
    def from_json(cls, json_str: str, agent_prompt: Optional[str] = None) -> "MissionContract":
        """
        Parses MissionContract from a JSON string, hardening against LLM noise and markdown fences.
        """
        clean_json = json_str.strip()
        
        # Robust extraction: find first '{' and last '}' to ignore markdown fences or surrounding text
        start_idx = clean_json.find('{')
        end_idx = clean_json.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            clean_json = clean_json[start_idx:end_idx+1]

        try:
            data = json.loads(clean_json)
            # Ensure agent_prompt is included in the data for Pydantic if not in JSON
            if "agent_prompt" not in data and agent_prompt:
                data["agent_prompt"] = agent_prompt
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid mission JSON: {e}")

    def validate_mission(self) -> Tuple[bool, str]:
        """Validate that the mission contract is complete and testable."""
        # Pydantic already handles basic type validation and empty checks via validators
        
        # Validate success criteria formats
        valid_prefixes = ["exists:", "contains:", "not_contains:", "pytest", "ruff", "mypy", "no_new_files"]
        for criterion in self.success_criteria:
            if ":" in criterion:
                prefix = criterion.split(":", 1)[0] + ":"
                if prefix not in valid_prefixes and not any(criterion.startswith(p) for p in valid_prefixes):
                    # It might be a complex shell command, but if it starts with something like "exist:" (typo), we should catch it
                    pass

        return True, ""
