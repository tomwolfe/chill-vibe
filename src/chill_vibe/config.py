import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from .execution import CodingAgent
from .constants import DEFAULT_CONFIG
from .models import ProjectConfig, AgentConfig

DEFAULT_AGENTS: Dict[str, Dict[str, Any]] = {
    "gemini-cli": {
        "command": ["npx", "@google/gemini-cli", "--yolo"],
        "dependencies": ["npx"]
    },
    "qwen": {
        "command": ["qwen"],
        "dependencies": ["qwen"]
    },
    "aider": {
        "command": ["aider", "--architect"],
        "dependencies": ["aider"]
    },
    "mentat": {
        "command": ["mentat"],
        "dependencies": ["mentat"]
    },
    "gpt-me": {
        "command": ["gptme"],
        "dependencies": ["gptme"]
    }
}

VALID_CONFIG_KEYS = set(ProjectConfig.model_fields.keys())

def load_config(repo_path: Union[str, Path]) -> Dict[str, Any]:
    """Load project configuration from .chillvibe.json or .chillvibe.yaml/.yml."""
    for ext in [".json", ".yaml", ".yml"]:
        config_path = Path(repo_path) / f".chillvibe{ext}"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    if ext == ".json":
                        config = json.load(f)
                    else:
                        config = yaml.safe_load(f)
                    
                    if isinstance(config, dict):
                        # Validate with Pydantic
                        validated_config = ProjectConfig(**config)
                        return validated_config.model_dump(exclude_unset=True)
                    return {}
            except Exception as e:
                print(f"[!] Warning: Could not parse project config: {e}")
    return {}

def get_agent_registry(repo_path: Optional[Union[str, Path]] = None) -> Dict[str, CodingAgent]:
    """Load and merge agent configurations from defaults, global, and local files."""
    # Start with default agents
    registry = {name: CodingAgent(name, **cfg) for name, cfg in DEFAULT_AGENTS.items()}
    
    def merge_agents(data: Dict[str, Any], target_registry: Dict[str, CodingAgent]) -> None:
        if not isinstance(data, dict):
            return
            
        agents_data = data.get("agents")
        if agents_data is None:
            # Heuristic: if it looks like a flat dict of agent configs
            is_flat_agents = any(isinstance(v, dict) and "command" in v for v in data.values())
            if is_flat_agents:
                agents_data = data

        if isinstance(agents_data, dict):
            for name, cfg in agents_data.items():
                if isinstance(cfg, dict) and "command" in cfg:
                    # Map 'deps' to 'dependencies' if present
                    if "deps" in cfg and "dependencies" not in cfg:
                        cfg["dependencies"] = cfg.pop("deps")
                    
                    # Create or update agent
                    # We extract only the keys CodingAgent.__init__ expects
                    try:
                        agent_cfg = AgentConfig(**cfg)
                        target_registry[name] = CodingAgent(
                            name, 
                            command=agent_cfg.command, 
                            dependencies=agent_cfg.dependencies,
                            env=agent_cfg.env
                        )
                    except Exception as e:
                        print(f"[!] Warning: Invalid agent config for '{name}': {e}")

    # 1. Load global config: ~/.chillvibe/agents.yaml
    global_config_path = Path.home() / ".chillvibe" / "agents.yaml"
    if global_config_path.exists():
        try:
            with open(global_config_path, "r") as f:
                global_data = yaml.safe_load(f)
                if isinstance(global_data, dict):
                    merge_agents(global_data, registry)
        except Exception as e:
            print(f"[!] Warning: Could not parse global agent config: {e}")

    # 2. Load local config: .chillvibe.yaml (under 'agents' key)
    if repo_path:
        local_config = load_config(repo_path)
        if isinstance(local_config, dict):
            merge_agents(local_config, registry)
                    
    return registry

def get_global_config() -> Dict[str, Any]:
    """Fetch global configuration from ~/.chillvibe/config.yaml or agents.yaml."""
    config: Dict[str, Any] = {}
    
    # Check config.yaml first, then fall back to agents.yaml for backward compatibility
    for filename in ["config.yaml", "agents.yaml"]:
        global_config_path = Path.home() / ".chillvibe" / filename
        if global_config_path.exists():
            try:
                with open(global_config_path, "r") as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        # Merge data into config
                        config.update(data)
            except Exception:
                pass
    return config

def get_default_model() -> str:
    """Fetch default model from global config or return standard default."""
    global_config = get_global_config()
    return str(global_config.get("default_model", DEFAULT_CONFIG["model"]))

def init_project(repo_path: Union[str, Path]) -> bool:
    """Create a default .chillvibe.yaml in the current directory."""
    config_path = Path(repo_path) / ".chillvibe.yaml"
    if config_path.exists():
        print(f"[!] Configuration file already exists at {config_path}")
        return False

    default_config = """# chill-vibe project configuration
# thinking_level: HIGH
# model: gemini-3-flash-preview

# extra_args: 
#   - "--some-flag"

# exclude_patterns:
#   - "**/logs/**"
#   - "temp_*.py"

# agents:
#   custom-agent:
#     command: ["my-agent", "--fast"]
#     dependencies: ["my-agent"]
"""
    try:
        with open(config_path, "w") as f:
            f.write(default_config)
        print(f"[*] Created default configuration at {config_path}")
        return True
    except Exception as e:
        print(f"[!] Failed to create configuration: {e}")
        return False
