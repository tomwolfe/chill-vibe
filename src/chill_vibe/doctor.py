import os
import sys
import shutil
import subprocess
from typing import Dict, Optional, Tuple, Any, Protocol, runtime_checkable
from .execution import CodingAgent

@runtime_checkable
class GenAIClient(Protocol):
    def models(self) -> Any: ...

@runtime_checkable
class GitDumpModule(Protocol):
    def dump(self) -> Any: ...

genai: Optional[Any] = None
try:
    from google import genai as _genai
    genai = _genai
except ImportError:
    pass

git_dump: Optional[Any] = None
try:
    import git_dump as _git_dump
    git_dump = _git_dump
except ImportError:
    pass

def install_package(package_name: str) -> bool:
    """Attempt to install a python package using the current interpreter."""
    print(f"[*] Attempting to install {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"[✓] Successfully installed {package_name}")
        return True
    except Exception as e:
        print(f"[✗] Failed to install {package_name}: {e}")
        return False

def check_api_connectivity(api_key: str) -> Tuple[bool, str]:
    """Verify that the Gemini API key is functional."""
    if not genai:
        return False, "google-genai not installed"
    
    try:
        client = genai.Client(api_key=api_key)
        # Using a very simple model and prompt to minimize latency/cost
        # We use flash here as it is fast and cheap for connectivity check
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say 'connected'",
            config={"max_output_tokens": 5}
        )
        if response.text:
            return True, "Connected successfully"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"
    return False, "Unknown error"

def check_api_quota(api_key: str) -> Tuple[bool, str]:
    """Verify API health and model availability."""
    if not genai:
        return False, "google-genai not installed"
    try:
        client = genai.Client(api_key=api_key)
        # Check if we can get model details (does not consume generation quota but verifies health)
        client.models.get(model="gemini-1.5-flash")
        return True, "API Quota/Health: Healthy"
    except Exception as e:
        return False, f"API Quota/Health: {str(e)}"

def check_thinking_capability(api_key: str) -> Tuple[bool, str]:
    """Verify if the model and API key support Gemini 3 Thinking features."""
    if not genai:
        return False, "google-genai not installed"
    
    try:
        from google.genai import types
        client = genai.Client(api_key=api_key)
        
        # 1. Check if gemini-3-flash-preview is available
        try:
            client.models.get(model="gemini-3-flash-preview")
            model_status = "Available"
        except Exception:
            model_status = "Not Found/No Access"
            
        # 2. Check ThinkingConfig support (Dry run)
        # We don't actually call generate_content here to save cost, 
        # but we check if we can construct the config.
        try:
            _ = types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)
            config_status = "Supported by SDK"
        except Exception as e:
            config_status = f"SDK Error: {e}"
            
        if model_status == "Available":
            return True, f"Gemini 3 Thinking: {model_status} ({config_status})"
        else:
            return False, f"Gemini 3 Thinking: {model_status} (Needed for 'high' thinking levels)"
            
    except Exception as e:
        return False, f"Thinking Check Failed: {str(e)}"

def run_doctor(registry: Dict[str, CodingAgent], fix: bool = False) -> None:
    """Check environment and dependencies."""
    print("--- chill-vibe Doctor Report ---")
    
    # 1. Check GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        if api_key.startswith("AIza"):
            print(f"[✓] GEMINI_API_KEY: Set and valid format ({api_key[:4]}...{api_key[-4:]})")
            print("[*] Verifying API connectivity...")
            success, msg = check_api_connectivity(api_key)
            if success:
                print(f"[✓] API Connectivity: {msg}")
                # Also check quota/health
                q_success, q_msg = check_api_quota(api_key)
                if q_success:
                    print(f"[✓] {q_msg}")
                else:
                    print(f"[✗] {q_msg}")
                
                # Check Gemini 3 Thinking capabilities
                t_success, t_msg = check_thinking_capability(api_key)
                if t_success:
                    print(f"[✓] {t_msg}")
                else:
                    print(f"[!] {t_msg}")
            else:
                print(f"[✗] API Connectivity: {msg}")
        else:
            print("[✗] GEMINI_API_KEY: Set but invalid format (should start with 'AIza')")
    else:
        print("[✗] GEMINI_API_KEY: Not set (Phase B reasoning will fail)")

    # 2. Check google-genai
    if genai:
        try:
            import importlib.metadata
            version = importlib.metadata.version("google-genai")
        except Exception:
            version = "unknown"
        
        if version != "unknown" and version < "0.3.0":
            print(f"[✗] google-genai: Version {version} is too old (min 0.3.0 required for thinking)")
        else:
            print(f"[✓] google-genai: Installed ({version})")
    else:
        print("[✗] google-genai: Not installed")
        if fix or input("[?] Would you like to attempt to install google-genai? (y/n): ").lower() == 'y':
            install_package("google-genai")

    # 2b. Check Static Analysis Tools
    for tool in ["mypy", "ruff"]:
        if shutil.which(tool):
            print(f"[✓] {tool}: Installed")
        else:
            print(f"[✗] {tool}: Not installed (Recommended for type safety and linting)")
            if fix or input(f"[?] Would you like to attempt to install {tool}? (y/n): ").lower() == 'y':
                install_package(tool)

    # 2c. Check Node.js and NPM
    if shutil.which("npx"):
        print("[✓] npx: Installed")
        try:
            node_v = subprocess.check_output(["node", "--version"], text=True).strip()
            print(f"[✓] node: Installed ({node_v})")
        except Exception:
            print("[✗] node: Not found")
            
        try:
            npm_v = subprocess.check_output(["npm", "--version"], text=True).strip()
            print(f"[✓] npm: Installed ({npm_v})")
        except Exception:
            print("[✗] npm: Not found")
    else:
        print("[✗] npx: Not installed (Required for gemini-cli agent)")

    # 3. Check git-dump
    if git_dump:
        print("[✓] git-dump: Installed")
    else:
        print("[✗] git-dump: Not installed")
        if fix or input("[?] Would you like to attempt to install git-dump? (y/n): ").lower() == 'y':
            install_package("git+https://github.com/tomwolfe/git_dump.git")

    # 4. Check git
    if shutil.which("git"):
        git_version = subprocess.check_output(["git", "--version"], text=True).strip()
        print(f"[✓] git: Installed ({git_version})")
    else:
        print("[✗] git: Not installed (Context extraction may be limited)")

    # 4b. Check log file size
    log_file = os.path.join(os.getcwd(), ".chillvibe_logs.jsonl")
    if os.path.exists(log_file):
        size_bytes = os.path.getsize(log_file)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > 1.0:
            print(f"[!] Log file is getting large ({size_mb:.2f} MB). Consider rotating it: mv .chillvibe_logs.jsonl .chillvibe_logs.jsonl.bak")
        else:
            print(f"[✓] Log file size: {size_mb:.2f} MB")

    # 4c. Self-Healing: Check for missing agent-specific configs
    print("\nSelf-Healing Config Checks:")
    agent_configs = {
        "aider": ".aider.conf.yml",
        "gptme": "gptme.toml",
    }
    for agent_name, config_file in agent_configs.items():
        if not os.path.exists(config_file):
            print(f"  [!] {agent_name}: Config '{config_file}' is missing (Recommended for best performance)")
            if fix or input(f"  [?] Would you like to create a default '{config_file}'? (y/n): ").lower() == 'y':
                if agent_name == "aider":
                    with open(config_file, "w") as f:
                        f.write("auto-test: true\nread: [codebase_context.txt]\n")
                    print(f"  [✓] Created default {config_file}")
                elif agent_name == "gptme":
                    with open(config_file, "w") as f:
                        f.write("[tool.gptme]\nmodel = \"gpt-4\"\n")
                    print(f"  [✓] Created default {config_file}")

    # 5. Check Agents
    print("\nAgent Availability:")
    for name, agent in registry.items():
        missing = agent.validate()
        if not missing:
            print(f"  [✓] {name}: Available")
        else:
            print(f"  [✗] {name}: Missing dependencies ({', '.join(missing)})")
            if fix or input(f"  [?] Would you like to attempt to install missing dependencies for {name}? (y/n): ").lower() == 'y':
                for dep in missing:
                    if dep in ["aider", "qwen", "mentat", "gptme"]:
                        install_package(dep)
                    else:
                        print(f"  [!] Don't know how to automatically install '{dep}'. Please install it manually.")
    
    print("-" * 32)

def validate_environment(agent_name: str, registry: Dict[str, CodingAgent]) -> None:
    """Pre-flight check for dependencies"""
    if not genai:
        print("Error: google-genai SDK not found. Please run 'pip install google-genai'.")
        sys.exit(1)
    
    try:
        import importlib.metadata
        version = importlib.metadata.version("google-genai")
        if version < "0.3.0":
            print(f"Error: google-genai version {version} is too old. Please upgrade: pip install -U google-genai")
            sys.exit(1)
    except Exception:
        pass # If we can't determine version, hope for the best
    
    if not git_dump:
        print("Error: git-dump not found. Please run './setup.sh' to install dependencies.")
        sys.exit(1)

    if agent_name not in registry:
        print(f"Error: Unknown agent '{agent_name}'. Available: {', '.join(registry.keys())}")
        sys.exit(1)
        
    agent = registry[agent_name]
    missing = agent.validate()
            
    if not shutil.which("git"):
        missing.append("git")

    if missing:
        print(f"Error: Missing required dependencies: {', '.join(set(missing))}")
        print("Please install them and try again.")
        sys.exit(1)
