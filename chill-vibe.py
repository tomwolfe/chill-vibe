#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import threading
import time

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai SDK not found. Please run 'pip install google-genai'.")
    sys.exit(1)

def run_git_dump(repo_path, output_file):
    """Phase A: Context Extraction"""
    # Resolve the path to the local git_dump tool
    git_dump_script = os.path.abspath(os.path.join("..", "git_dump", "git_dump.py"))
    
    # Try to find git-dump in PATH, then fallback to the local script
    git_dump_cmd = "git-dump"
    try:
        subprocess.run([git_dump_cmd, "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        if os.path.exists(git_dump_script):
            # If it's a python script, use the current python interpreter
            git_dump_cmd = git_dump_script
        else:
            print(f"Error: git-dump not found in PATH and {git_dump_script} does not exist.")
            sys.exit(1)
            
    cmd = [git_dump_cmd, repo_path, "-o", output_file]
    
    # If using the script directly and it's python, it might need 'python' prefix if not executable
    if git_dump_cmd == git_dump_script:
        cmd = [sys.executable, git_dump_script, repo_path, "-o", output_file]

    print(f"[*] Extracting codebase context from {repo_path}...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running git-dump: {e}")
        sys.exit(1)

def get_strategic_reasoning(context_file, model_id, thinking_level):
    """Phase B: Strategic Reasoning"""
    if not os.path.exists(context_file):
        print(f"Error: {context_file} not found.")
        sys.exit(1)
        
    with open(context_file, "r") as f:
        codebase_context = f.read()

    # The API key should be in the environment variable GEMINI_API_KEY
    if not os.environ.get("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY environment variable not set.")

    client = genai.Client()
    
    preamble = (
        "Critically analyze this project (attached), then give it a grade. "
        "I would like a prompt to give a coding agent to have the agent autonomously work on the attached codebase to achieve its goals for the project. "
        "Before you give the prompt, what should the goals be for the agent and how will the agent know it has reached those goals?"
    )
    
    # We add a clear delimiter to extract the agent prompt later
    full_prompt = (
        f"{preamble}\n\n"
        "--- INSTRUCTIONS FOR YOUR RESPONSE ---\n"
        "1. Provide your analysis, grade, and goals first.\n"
        "2. Provide the final prompt for the coding agent in a single block wrapped in <agent_prompt> tags.\n"
        "3. Ensure the agent prompt is comprehensive and self-contained.\n\n"
        f"--- CODEBASE CONTEXT ---\n{codebase_context}"
    )
    
    print(f"[*] Requesting strategic reasoning from {model_id} (Thinking level: {thinking_level})...")
    
    # Mapping thinking level to budget if applicable, 
    # though currently include_thoughts is the main switch.
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    )
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=full_prompt,
            config=config
        )
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)
    
    full_text = response.text
    
    # Extract the portion intended for the agent
    if "<agent_prompt>" in full_text and "</agent_prompt>" in full_text:
        agent_prompt = full_text.split("<agent_prompt>")[1].split("</agent_prompt>")[0].strip()
    else:
        # Fallback if tags are missing: look for common delimiters or just use the last portion
        print("[!] Warning: Could not find <agent_prompt> tags in response. Using full response.")
        agent_prompt = full_text
        
    return agent_prompt

def forward_stdin(process):
    """Thread function to forward system stdin to the subprocess stdin."""
    try:
        while True:
            # Read one character at a time to remain responsive
            char = sys.stdin.read(1)
            if not char:
                break
            process.stdin.write(char)
            process.stdin.flush()
    except Exception:
        pass
    finally:
        try:
            process.stdin.close()
        except:
            pass

def run_coding_agent(agent_name, agent_prompt):
    """Phase C: Autonomous Execution"""
    if agent_name == "gemini-cli":
        # Using npx to run the gemini-cli
        cmd = ["npx", "@google/gemini-cli", "--yolo"]
    elif agent_name == "qwen":
        cmd = ["qwen"]
    else:
        print(f"Unknown agent: {agent_name}")
        sys.exit(1)
    
    print(f"[*] Launching {agent_name} in autonomous mode...")
    
    # Launch with a pipe for stdin so we can inject the prompt,
    # then hand over to the user.
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
        bufsize=1
    )
    
    # 1. Pipe the initial agent prompt
    process.stdin.write(agent_prompt + "\n")
    process.stdin.flush()
    
    # 2. Start a background thread to forward user input to the agent
    # This allows the user to interact (e.g., "keep trying", Ctrl+C, etc.)
    threading.Thread(target=forward_stdin, args=(process,), daemon=True).start()
    
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n[*] chill-vibe: Terminating agent...")
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

def main():
    parser = argparse.ArgumentParser(description="chill-vibe: A Reasoning-to-Code CLI pipeline")
    parser.add_argument("path", help="The directory of the repo to analyze")
    parser.add_argument("--agent", choices=["gemini-cli", "qwen"], default="gemini-cli", 
                        help="Choice of coding agent (default: gemini-cli)")
    parser.add_argument("--thinking", default="HIGH", 
                        help="Thinking level (default: HIGH)")
    parser.add_argument("--model", default="gemini-3-flash-preview", 
                        help="Model ID (default: gemini-3-flash-preview)")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Output the context and the reasoning prompt without invoking the coding agent")
    
    args = parser.parse_args()
    
    # Phase A: Context Extraction
    context_file = "codebase_context.txt"
    run_git_dump(args.path, context_file)
    
    if args.dry_run:
        print("\n[*] Dry-run mode: Context extracted.")
        # We still run Phase B to show what the prompt WOULD be
    
    # Phase B: Strategic Reasoning
    agent_prompt = get_strategic_reasoning(context_file, args.model, args.thinking)
    
    if args.dry_run:
        print("\n--- GENERATED AGENT PROMPT ---")
        print(agent_prompt)
        print("------------------------------")
        return

    # Phase C: Autonomous Execution
    run_coding_agent(args.agent, agent_prompt)

if __name__ == "__main__":
    main()
