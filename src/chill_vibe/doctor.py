import os
import sys
import shutil
import subprocess

try:
    from google import genai
except ImportError:
    genai = None

try:
    import git_dump
except ImportError:
    git_dump = None

def install_package(package_name):
    """Attempt to install a python package using the current interpreter."""
    print(f"[*] Attempting to install {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"[✓] Successfully installed {package_name}")
        return True
    except Exception as e:
        print(f"[✗] Failed to install {package_name}: {e}")
        return False

def run_doctor(registry):
    """Check environment and dependencies."""
    print("--- chill-vibe Doctor Report ---")
    
    # 1. Check GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"[✓] GEMINI_API_KEY: Set ({api_key[:4]}...{api_key[-4:]})")
    else:
        print("[✗] GEMINI_API_KEY: Not set (Phase B reasoning will fail)")

    # 2. Check google-genai
    if genai:
        print("[✓] google-genai: Installed")
    else:
        print("[✗] google-genai: Not installed")
        if input("[?] Would you like to attempt to install google-genai? (y/n): ").lower() == 'y':
            install_package("google-genai")

    # 3. Check git-dump
    if git_dump:
        print("[✓] git-dump: Installed")
    else:
        print("[✗] git-dump: Not installed")
        if input("[?] Would you like to attempt to install git-dump? (y/n): ").lower() == 'y':
            install_package("git+https://github.com/tomwolfe/git_dump.git")

    # 4. Check git
    if shutil.which("git"):
        git_version = subprocess.check_output(["git", "--version"], text=True).strip()
        print(f"[✓] git: Installed ({git_version})")
    else:
        print("[✗] git: Not installed (Context extraction may be limited)")

    # 5. Check Agents
    print("\nAgent Availability:")
    for name, agent in registry.items():
        missing = agent.validate()
        if not missing:
            print(f"  [✓] {name}: Available")
        else:
            print(f"  [✗] {name}: Missing dependencies ({', '.join(missing)})")
            if input(f"  [?] Would you like to attempt to install missing dependencies for {name}? (y/n): ").lower() == 'y':
                for dep in missing:
                    if dep in ["aider", "qwen"]:
                        install_package(dep)
                    else:
                        print(f"  [!] Don't know how to automatically install '{dep}'. Please install it manually.")
    
    print("-" * 32)

def validate_environment(agent_name, registry):
    """Pre-flight check for dependencies"""
    if not genai:
        print("Error: google-genai SDK not found. Please run 'pip install google-genai'.")
        sys.exit(1)
    
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
