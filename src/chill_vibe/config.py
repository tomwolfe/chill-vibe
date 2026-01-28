import json
import yaml
from pathlib import Path
from .execution import CodingAgent
from .constants import DEFAULT_MODEL

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
                global_data = yaml.safe_load(f)
                if global_data and isinstance(global_data, dict):
                    # Check for agents key or assume top-level is agents if it doesn't look like a config with keys
                    agents_data = global_data.get("agents", global_data)
                    if isinstance(agents_data, dict):
                        for name, cfg in agents_data.items():
                            if name != "default_model": # Skip the special key if at top level
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

def get_global_config():
    """Fetch global configuration from ~/.chillvibe/config.yaml or agents.yaml."""
    config = {}
    
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

def get_default_model():
    """Fetch default model from global config or return standard default."""
    global_config = get_global_config()
    return global_config.get("default_model", DEFAULT_MODEL)
