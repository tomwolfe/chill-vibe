import json
import yaml
from pathlib import Path
from .execution import CodingAgent
from .constants import DEFAULT_CONFIG

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

VALID_CONFIG_KEYS = {"agents", "extra_args", "model", "thinking_level", "exclude_patterns", "depth", "include_ext", "protected_files"}

def load_config(repo_path):
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
                        unknown_keys = set(config.keys()) - VALID_CONFIG_KEYS
                        if unknown_keys:
                            print(f"[!] Warning: Unknown keys in {config_path.name}: {', '.join(unknown_keys)}")
                    return config
            except Exception as e:
                print(f"[!] Warning: Could not parse project config: {e}")
    return {}

def get_agent_registry(repo_path=None):
    """Load and merge agent configurations from defaults, global, and local files."""
    # Start with default agents
    registry = {name: CodingAgent(name, **cfg) for name, cfg in DEFAULT_AGENTS.items()}
    
    # 1. Load global config: ~/.chillvibe/agents.yaml
    global_config_path = Path.home() / ".chillvibe" / "agents.yaml"
    if global_config_path.exists():
        try:
            with open(global_config_path, "r") as f:
                global_data = yaml.safe_load(f)
                if isinstance(global_data, dict):
                    # If there's an 'agents' key, use it. Otherwise, if it's a flat dict of agents, use that.
                    # We check if any of the keys match DEFAULT_AGENTS or have a 'command' key to guess.
                    agents_data = global_data.get("agents")
                    if agents_data is None:
                        # Heuristic: if it looks like a flat dict of agent configs
                        is_flat_agents = any(isinstance(v, dict) and "command" in v for v in global_data.values())
                        if is_flat_agents:
                            agents_data = global_data

                    if isinstance(agents_data, dict):
                        for name, cfg in agents_data.items():
                            if isinstance(cfg, dict) and "command" in cfg:
                                # This completely overrides the default agent if name matches
                                registry[name] = CodingAgent(name, **cfg)
        except Exception as e:
            print(f"[!] Warning: Could not parse global agent config: {e}")

    # 2. Load local config: .chillvibe.yaml (under 'agents' key)
    if repo_path:
        local_config = load_config(repo_path)
        if isinstance(local_config, dict) and "agents" in local_config:
            local_agents = local_config["agents"]
            if isinstance(local_agents, dict):
                for name, cfg in local_agents.items():
                    if isinstance(cfg, dict) and "command" in cfg:
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
    return global_config.get("default_model", DEFAULT_CONFIG["model"])

def init_project(repo_path):
    """Create a default .chillvibe.yaml in the current directory."""
    config_path = Path(repo_path) / ".chillvibe.yaml"
    if config_path.exists():
        print(f"[!] Configuration file already exists at {config_path}")
        return False

    default_config = """# chill-vibe project configuration
# thinking_level: HIGH
# model: gemini-2.0-pro-exp-02-05

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
