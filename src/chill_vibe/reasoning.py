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

def log_mission(agent_prompt, model_id, agent_name, duration, status="UNKNOWN", exit_code=None, classification=None, success_criteria=None, verification_results=None):
    """Log the mission details to a hidden file."""
    log_file = Path(".chillvibe_logs.jsonl")
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model_id": model_id,
        "agent_name": agent_name,
        "duration_seconds": round(duration, 2),
        "status": status,
        "exit_code": exit_code,
        "classification": classification,
        "success_criteria": success_criteria,
        "verification_results": verification_results,
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

    print(f"{ 'Timestamp':<20} | { 'Model':<25} | { 'Agent':<15} | { 'Status':<10} | { 'Class':<12} | { 'Exit':<5}")
    print("-" * 105)
    
    try:
        with open(log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    timestamp = entry.get("timestamp", "N/A")
                    model = entry.get("model_id", "N/A")
                    agent = entry.get("agent_name", "N/A")
                    status = entry.get("status", "N/A")
                    classification = entry.get("classification") or ""
                    exit_code = entry.get("exit_code", "N/A")
                    print(f"{timestamp:<20} | {model:<25} | {agent:<15} | {status:<10} | {classification:<12} | {exit_code:<5}")
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
        "\n\n--- MISSION SPECIFICATION ---\n"
        "1. Define clear, objective GOALS for the agent.\n"
        "2. Define machine-verifiable SUCCESS CRITERIA (shell commands, file checks, or invariants) that MUST pass for the mission to be considered successful.\n"
        "3. Generate a checklist-driven, deterministic AGENT PROMPT that avoids vague instructions.\n"
    )
    
    project_constraints = ""
    if config_data:
        project_constraints = f"\n\n--- User-Defined Project Constraints ---\n{json.dumps(config_data, indent=2)}"

    # We add a clear delimiter to extract the agent prompt later
    full_prompt = (
        f"{preamble}\n\n"
        "--- INSTRUCTIONS FOR YOUR RESPONSE ---\n"
        "1. Provide your analysis, grade, and goals first.\n"
        "2. Provide the machine-verifiable SUCCESS CRITERIA in a block wrapped in <success_criteria> tags. Each line should be a single shell command that returns exit code 0 on success.\n"
        "3. Provide the final AGENT PROMPT in a block wrapped in <agent_prompt> tags.\n"
        "4. Ensure the agent prompt is checklist-driven, explicit, and self-contained.\n\n"
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
    
    agent_prompt_match = re.search(r"(?:```(?:xml|html)?\s*)?<agent_prompt>(.*?)</agent_prompt>(?:\s*```)?", full_text, re.DOTALL)
    if agent_prompt_match:
        agent_prompt = agent_prompt_match.group(1).strip()
    else:
        print("[!] Warning: Could not find <agent_prompt> tags in response. Using full response.")
        agent_prompt = full_text

    success_criteria_match = re.search(r"(?:```(?:xml|html)?\s*)?<success_criteria>(.*?)</success_criteria>(?:\s*```)?", full_text, re.DOTALL)
    success_criteria = []
    if success_criteria_match:
        success_criteria = [line.strip() for line in success_criteria_match.group(1).strip().split("\n") if line.strip()]
        
    return agent_prompt, success_criteria

def classify_failure_signals(exit_code, last_output):
    """Extract grounded execution signals from failure output."""
    signals = []
    
    if exit_code == 127:
        signals.append("COMMAND_NOT_FOUND")
    elif exit_code == 130:
        signals.append("SIGINT_INTERRUPTED")
    elif exit_code == 137:
        signals.append("SIGKILL_OOM")
    
    # Common error patterns
    error_patterns = {
        "PERMISSION_DENIED": [r"Permission denied", r"EACCES"],
        "DEPENDENCY_MISSING": [r"ModuleNotFoundError", r"ImportError", r"npm ERR! missing"],
        "TIMEOUT": [r"timed out", r"TimeoutExpired"],
        "SYNTAX_ERROR": [r"SyntaxError"],
        "TEST_FAILURE": [r"FAIL:", r"FAILED \(failures=", r"AssertionError"],
        "DISK_FULL": [r"No space left on device", r"ENOSPC"]
    }
    
    output_text = "".join(last_output)
    for signal, patterns in error_patterns.items():
        if any(re.search(p, output_text, re.IGNORECASE) for p in patterns):
            signals.append(signal)
            
    return signals

def get_recovery_strategy(repo_path, model_id, original_prompt, failure_output, exit_code=None, config_data=None):
    """Generate a recovery strategy after an agent fails, with grounded classification."""
    if genai is None:
        print("Error: google-genai SDK not found.")
        sys.exit(1)

    client = genai.Client()
    
    signals = classify_failure_signals(exit_code, failure_output) if exit_code is not None else []
    signals_str = ", ".join(signals) if signals else "NONE"
    
    prompt = (
        "The coding agent failed. Analyze the failure and provide a targeted recovery strategy.\n\n"
        "--- EXECUTION SIGNALS ---\n"
        f"Exit Code: {exit_code}\n"
        f"Detected Signals: {signals_str}\n\n"
        "--- FAILURE CLASSIFICATION ---\n"
        "Classify the failure into one of these categories:\n"
        "- TOOLING: Command not found, permissions, or tool-specific errors.\n"
        "- LOGIC: Code compiled but logical checks or tests failed.\n"
        "- ENVIRONMENT: Missing dependencies, environment variables, or infrastructure issues.\n"
        "- AMBIGUITY: Original instructions were unclear or contradictory.\n"
        "- UNKNOWN: Failure reason is not apparent from the output.\n\n"
        "--- ORIGINAL PROMPT ---\n"
        f"{original_prompt}\n\n"
        "--- FAILED OUTPUT (LAST 50 LINES) ---\n"
        f"{failure_output}\n\n"
        "--- INSTRUCTIONS ---\n"
        "1. Provide your analysis and classification first, incorporating the detected execution signals.\n"
        "2. Provide the failure classification wrapped in <classification> tags.\n"
        "3. Provide a NEW, targeted agent prompt wrapped in <agent_prompt> tags to fix the issue. "
        "Explicitly address why the previous attempt failed and what to avoid.\n"
    )
    
    print(f"[*] Requesting recovery strategy from {model_id}...")
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
    except Exception as e:
        print(f"Error calling Gemini API for recovery: {e}")
        return None, "UNKNOWN"
        
    full_text = response.text
    
    classification_match = re.search(r"<classification>(.*?)</classification>", full_text, re.IGNORECASE)
    classification = classification_match.group(1).strip() if classification_match else "UNKNOWN"
    
    agent_prompt_match = re.search(r"(?:```(?:xml|html)?\s*)?<agent_prompt>(.*?)</agent_prompt>(?:\s*```)?", full_text, re.DOTALL)
    recovery_prompt = agent_prompt_match.group(1).strip() if agent_prompt_match else full_text
    
    return recovery_prompt, classification
