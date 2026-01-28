import json
import yaml
from pathlib import Path
from .execution import CodingAgent

DEFAULT_AGENTS = {
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
    }
}

def load_config(repo_path):
    """Load project configuration from .chillvibe.json or .chillvibe.yaml/.yml."""
    for ext in [".json", ".yaml", ".yml"]:
        config_path = Path(repo_path) / f".chillvibe{ext}"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    if ext == ".json":
                        return json.load(f)
                    else:
                        return yaml.safe_load(f)
            except Exception as e:
                print(f"[!] Warning: Could not parse project config: {e}")
    return {}

def get_agent_registry(repo_path=None):
    """Load and merge agent configurations from defaults, global, and local files."""
    registry = {name: CodingAgent(name, **cfg) for name, cfg in DEFAULT_AGENTS.items()}
    
    # 1. Load global config: ~/.chillvibe/agents.yaml
    global_config_path = Path.home() / ".chillvibe" / "agents.yaml"
    if global_config_path.exists():
        try:
            with open(global_config_path, "r") as f:
                global_agents = yaml.safe_load(f)
                if global_agents and isinstance(global_agents, dict):
                    for name, cfg in global_agents.items():
                        registry[name] = CodingAgent(name, **cfg)
        except Exception as e:
            print(f"[!] Warning: Could not parse global agent config: {e}")

    # 2. Load local config: .chillvibe.yaml (under 'agents' key)
    if repo_path:
        local_config = load_config(repo_path)
        if local_config and "agents" in local_config:
            local_agents = local_config["agents"]
            if isinstance(local_agents, dict):
                for name, cfg in local_agents.items():
                    registry[name] = CodingAgent(name, **cfg)
                    
    return registry
