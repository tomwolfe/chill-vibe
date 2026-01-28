#!/usr/bin/env python3
import argparse
import os
import re
import shutil
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

try:
    import git_dump
except ImportError:
    print("Error: git-dump not found. Please run './setup.sh' to install dependencies.")
    sys.exit(1)

def validate_environment(agent_name):
    """Pre-flight check for dependencies"""
    dependencies = ["git"]
    if agent_name == "gemini-cli":
        dependencies.append("npx")
    elif agent_name == "qwen":
        dependencies.append("qwen")
    
    # Also check for the chill-vibe script dependencies implicitly by being here, 
    # but let's check for git-dump's underlying tool if it has one? 
    # git-dump is a python module, but we can check if git is present.
    
    missing = []
    for dep in dependencies:
        if not shutil.which(dep):
            missing.append(dep)
            
    if missing:
        print(f"Error: Missing required dependencies: {', '.join(missing)}")
        print("Please install them and try again.")
        sys.exit(1)

def run_git_dump(repo_path, output_file):
    """Phase A: Context Extraction"""
    print(f"[*] Extracting codebase context from {repo_path}...")
    try:
        from git_dump.core import RepoProcessor
        processor = RepoProcessor(repo_path, output_file)
        processor.process()
    except Exception as e:
        print(f"Error running git-dump: {e}")
        sys.exit(1)

def get_strategic_reasoning(context_file, model_id, thinking_level, verbose=False):
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
    
    # Task 1: Map thinking level to budget
    budgets = {
        "LOW": 2048,
        "MEDIUM": 8192,
        "HIGH": 16384
    }
    budget = budgets.get(thinking_level.upper(), 16384)

    # Update config with thinking budget
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=budget
        )
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
    
    # Task 2: Verbose Reasoning Output
    if verbose:
        # According to google-genai SDK, thoughts are in the candidate's parts
        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.thought:
                        print("\n--- INTERNAL THOUGHTS ---")
                        # Using ANSI dimmed style if possible, or just a header
                        print(f"\033[2m{part.text}\033[0m")
                        print("-------------------------\n")
        except AttributeError:
            pass # No thoughts found or different SDK version structure

    full_text = response.text
    
    # Extract the portion intended for the agent using regex to be more flexible
    match = re.search(r"<agent_prompt>(.*?)</agent_prompt>", full_text, re.DOTALL)
    if match:
        agent_prompt = match.group(1).strip()
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

def get_parser():
    parser = argparse.ArgumentParser(description="chill-vibe: A Reasoning-to-Code CLI pipeline")
    parser.add_argument("path", nargs="?", help="The directory of the repo to analyze")
    parser.add_argument("--agent", choices=["gemini-cli", "qwen"], default="gemini-cli", 
                        help="Choice of coding agent (default: gemini-cli)")
    parser.add_argument("--thinking", default="HIGH", 
                        help="Thinking level (default: HIGH)")
    parser.add_argument("--model", default="gemini-3-flash-preview", 
                        help="Model ID (default: gemini-3-flash-preview)")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Output the context and the reasoning prompt without invoking the coding agent")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print the model's internal thinking/reasoning")
    parser.add_argument("--context-file", default="codebase_context.txt",
                        help="The file to store the extracted codebase context (default: codebase_context.txt)")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete the context file after execution")
    parser.add_argument("--version", action="version", version="chill-vibe v0.1.0")
    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()

    if not args.path:
        parser.print_help()
        sys.exit(0)
    
    # Pre-flight checks
    validate_environment(args.agent)
    
    # Phase A: Context Extraction
    run_git_dump(args.path, args.context_file)
    
    try:
        if args.dry_run:
            print("\n[*] Dry-run mode: Context extracted.")
            # We still run Phase B to show what the prompt WOULD be
        
        # Phase B: Strategic Reasoning
        agent_prompt = get_strategic_reasoning(args.context_file, args.model, args.thinking, args.verbose)
        
        if args.dry_run:
            print("\n--- GENERATED AGENT PROMPT ---")
            print(agent_prompt)
            print("------------------------------")
        else:
            # Phase C: Autonomous Execution
            run_coding_agent(args.agent, agent_prompt)
    finally:
        if args.cleanup and os.path.exists(args.context_file):
            print(f"[*] Cleaning up context file: {args.context_file}")
            os.remove(args.context_file)

if __name__ == "__main__":
    main()
