import os
import re
import time
import json
import sys
from pathlib import Path
from .constants import DEFAULT_CONFIG

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

def log_mission(agent_prompt, model_id, agent_name, duration, status="UNKNOWN", exit_code=None):
    """Log the mission details to a hidden file."""
    log_file = Path(".chillvibe_logs.jsonl")
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model_id": model_id,
        "agent_name": agent_name,
        "duration_seconds": round(duration, 2),
        "status": status,
        "exit_code": exit_code,
        "agent_prompt": agent_prompt
    }
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[!] Warning: Could not write to log file: {e}")

def show_history():
    """Read and format the mission history from .chillvibe_logs.jsonl."""
    log_file = Path(".chillvibe_logs.jsonl")
    if not log_file.exists():
        print("No history found.")
        return

    print(f"{ 'Timestamp':<20} | { 'Model':<25} | { 'Agent':<15} | { 'Status':<10} | { 'Exit':<5}")
    print("-" * 90)
    
    try:
        with open(log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    timestamp = entry.get("timestamp", "N/A")
                    model = entry.get("model_id", "N/A")
                    agent = entry.get("agent_name", "N/A")
                    status = entry.get("status", "N/A")
                    exit_code = entry.get("exit_code", "N/A")
                    print(f"{timestamp:<20} | {model:<25} | {agent:<15} | {status:<10} | {exit_code:<5}")
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading history: {e}")

def get_strategic_reasoning(repo_path, context_file, model_id, thinking_level, config_data=None, verbose=False):
    """Phase B: Strategic Reasoning"""
    if not os.path.exists(context_file):
        print(f"Error: {context_file} not found.")
        sys.exit(1)
        
    with open(context_file, "r") as f:
        codebase_context = f.read()

    # The API key should be in the environment variable GEMINI_API_KEY
    if not os.environ.get("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY environment variable not set.")

    if genai is None:
        print("Error: google-genai SDK not found. Please run 'pip install google-genai'.")
        sys.exit(1)

    client = genai.Client()
    
    preamble = (
        "Critically analyze this project (attached), then give it a grade. "
        "I would like a prompt to give a coding agent to have the agent autonomously work on the attached codebase to achieve its goals for the project. "
        "Before you give the prompt, what should the goals be for the agent and how will the agent know it has reached those goals?"
    )
    
    project_constraints = ""
    if config_data:
        project_constraints = f"\n\n--- User-Defined Project Constraints ---\n{json.dumps(config_data, indent=2)}"

    # We add a clear delimiter to extract the agent prompt later
    full_prompt = (
        f"{preamble}\n\n"
        "--- INSTRUCTIONS FOR YOUR RESPONSE ---\n"
        "1. Provide your analysis, grade, and goals first.\n"
        "2. Provide the final prompt for the coding agent in a single block wrapped in <agent_prompt> tags.\n"
        "3. Ensure the agent prompt is comprehensive and self-contained.\n\n"
        f"--- CODEBASE CONTEXT ---\n{codebase_context}"
        f"{project_constraints}"
    )
    
    print(f"[*] Requesting strategic reasoning from {model_id} (Thinking level: {thinking_level})...")
    
    budgets = DEFAULT_CONFIG["budgets"]
    budget = budgets.get(thinking_level.upper(), budgets["HIGH"])

    # Update config with thinking budget
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=budget
        )
    )
    
    max_retries = 3
    retry_delay = 5
    response = None
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=full_prompt,
                config=config
            )
            break
        except Exception as e:
            error_str = str(e).lower()
            is_transient = any(code in error_str for code in ["429", "500", "503", "quota", "internal error"])
            
            if is_transient and attempt < max_retries - 1:
                print(f"[!] API error (attempt {attempt+1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Error calling Gemini API: {e}")
                sys.exit(1)
    
    if not response:
        print("Error: No response from Gemini API.")
        sys.exit(1)
    
    if verbose:
        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.thought:
                        print("\n--- INTERNAL THOUGHTS ---")
                        print(f"\033[2m{part.text}\033[0m")
                        print("-------------------------\n")
        except AttributeError:
            pass 

    full_text = response.text
    
    match = re.search(r"(?:```(?:xml|html)?\s*)?<agent_prompt>(.*?)</agent_prompt>(?:\s*```)?", full_text, re.DOTALL)
    if match:
        agent_prompt = match.group(1).strip()
    else:
        print("[!] Warning: Could not find <agent_prompt> tags in response. Using full response.")
        agent_prompt = full_text
        
    return agent_prompt

def get_recovery_strategy(repo_path, model_id, original_prompt, failure_output, config_data=None):
    """Generate a recovery strategy after an agent fails."""
    if genai is None:
        print("Error: google-genai SDK not found.")
        sys.exit(1)

    client = genai.Client()
    
    prompt = (
        "The coding agent failed with a non-zero exit code. "
        "Review the original prompt and the last 50 lines of output, then provide a 'Recovery Strategy' "
        "in the form of a NEW agent prompt to fix the issues.\n\n"
        "--- ORIGINAL PROMPT ---\n"
        f"{original_prompt}\n\n"
        "--- FAILED OUTPUT (LAST 50 LINES) ---\n"
        f"{failure_output}\n\n"
        "--- INSTRUCTIONS ---\n"
        "Provide your analysis of the failure first, then provide the new agent prompt wrapped in <agent_prompt> tags."
    )
    
    print(f"[*] Requesting recovery strategy from {model_id}...")
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
    except Exception as e:
        print(f"Error calling Gemini API for recovery: {e}")
        return None
        
    full_text = response.text
    match = re.search(r"(?:```(?:xml|html)?\s*)?<agent_prompt>(.*?)</agent_prompt>(?:\s*```)?", full_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return full_text
