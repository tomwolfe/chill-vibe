import os
import re
import time
import json
import sys
from pathlib import Path
from .constants import DEFAULT_CONFIG
from .context import MissionContract

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

def log_mission(mission, model_id, agent_name, duration, status="UNKNOWN", exit_code=None, classification=None, verification_results=None):
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
        "success_criteria": mission.success_criteria if hasattr(mission, 'success_criteria') else mission,
        "verification_results": verification_results,
        "agent_prompt": mission.agent_prompt if hasattr(mission, 'agent_prompt') else str(mission),
        "objectives": mission.objectives if hasattr(mission, 'objectives') else []
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

def validate_mission(mission_contract, codebase_context, model_id, config_data=None):
    """Second-pass validation of the mission contract."""
    if genai is None:
        return True, ""

    client = genai.Client()
    
    mission_dict = {
        'objectives': mission_contract.objectives,
        'success_criteria': mission_contract.success_criteria,
        'non_goals': mission_contract.non_goals,
        'checklist': mission_contract.checklist,
        'forbidden_actions': mission_contract.forbidden_actions,
        'summary': mission_contract.summary
    }
    mission_json_str = json.dumps(mission_dict, indent=2)

    prompt = (
        "You are an expert mission auditor. Review the following mission contract for a coding agent.\n\n"
        "--- MISSION CONTRACT ---\n"
        f"{mission_json_str}\n\n"
        "--- TASK ---\n"
        "Audit this mission for:\n"
        "1. Completeness: Do the success criteria fully cover the objectives?\n"
        "2. Testability: Are all success criteria machine-verifiable?\n"
        "3. Determinism: Are the instructions unambiguous?\n"
        "4. Safety: Are there any forbidden actions that are missing?\n\n"
        "If the mission is solid, respond with 'PASSED'. If it has flaws, respond with 'REJECTED' followed by a list of issues.\n"
    )

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        result = response.text.strip()
        if result.startswith("PASSED"):
            return True, ""
        else:
            return False, result
    except Exception as e:
        print(f"[!] Warning: Mission validation failed to run: {e}")
        return True, "" # Fallback to true if validation fails to execute

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
    )
    
    project_constraints = ""
    if config_data:
        project_constraints = f"\n\n--- User-Defined Project Constraints ---\n{json.dumps(config_data, indent=2)}"

    # We add a clear delimiter to extract the agent prompt later
    full_prompt = (
        f"{preamble}\n\n"
        "--- INSTRUCTIONS FOR YOUR RESPONSE ---\n"
        "1. Provide your analysis, grade, and goals first.\n"
        "2. Provide a structured mission contract in a block wrapped in <mission_contract> tags. "
        "The block must be a valid JSON object with the following schema:\n"
        "{\n"
        "  \"objectives\": [\"string\"],\n"
        "  \"non_goals\": [\"string\"],\n"
        "  \"checklist\": [\"string\"],\n"
        "  \"success_criteria\": [\"string\"],\n"
        "  \"forbidden_actions\": [\"string\"],\n"
        "  \"summary\": \"string\",\n"
        "  \"agent_prompt\": \"string\"\n"
        "}\n"
        "3. Ensure the 'agent_prompt' is checklist-driven, explicit, and self-contained.\n"
        "4. Success criteria must be machine-verifiable (shell commands, file checks like 'exists:path', 'contains:path regex', or 'not_contains:path regex').\n\n"
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
    
    mission_contract_match = re.search(r"(?:```(?:json)?\s*)?<mission_contract>(.*?)</mission_contract>(?:\s*```)?", full_text, re.DOTALL)
    if not mission_contract_match:
        print("[!] Error: Could not find <mission_contract> tags in response.")
        sys.exit(1)

    try:
        mission_json = mission_contract_match.group(1).strip()
        # Handle cases where the model might wrap JSON in extra backticks inside the tag
        if mission_json.startswith("```json"):
            mission_json = mission_json[7:]
        if mission_json.startswith("```"):
            mission_json = mission_json[3:]
        if mission_json.endswith("```"):
            mission_json = mission_json[:-3]
        
        mission_data = json.loads(mission_json.strip())
        mission = MissionContract(
            objectives=mission_data.get("objectives", []),
            success_criteria=mission_data.get("success_criteria", []),
            agent_prompt=mission_data.get("agent_prompt", ""),
            non_goals=mission_data.get("non_goals", []),
            checklist=mission_data.get("checklist", []),
            forbidden_actions=mission_data.get("forbidden_actions", []),
            summary=mission_data.get("summary", "")
        )
    except Exception as e:
        print(f"[!] Error parsing mission contract JSON: {e}")
        # Print the raw text for debugging if JSON parsing fails
        if verbose:
            print("--- RAW MISSION JSON ---")
            print(mission_contract_match.group(1))
        sys.exit(1)

    # Perform second-pass validation
    print("[*] Validating mission contract (second pass)...")
    valid, validation_msg = validate_mission(mission, codebase_context, model_id, config_data)
    if not valid:
        print(f"[!] Mission contract rejected by validator:\n{validation_msg}")
        # In a real scenario, we might want to re-try or fail. 
        # For now, let's just warn and continue if it's not catastrophic.
    
    return mission

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
    """Generate a recovery strategy after an agent fails, with grounded classification and memory."""
    if genai is None:
        print("Error: google-genai SDK not found.")
        sys.exit(1)

    client = genai.Client()
    
    signals = classify_failure_signals(exit_code, failure_output) if exit_code is not None else []
    signals_str = ", ".join(signals) if signals else "NONE"
    
    # Read history for memory
    history_context = ""
    log_file = Path(".chillvibe_logs.jsonl")
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                # Get last 5 failed missions for context
                failed_entries = []
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("status") == "FAILED":
                            failed_entries.append(entry)
                    except json.JSONDecodeError:
                        continue
                
                if failed_entries:
                    history_context = "\n--- RECENT FAILURE HISTORY ---\n"
                    for entry in failed_entries[-5:]:
                        history_context += f"- Date: {entry.get('timestamp')}\n"
                        history_context += f"  Classification: {entry.get('classification')}\n"
                        history_context += f"  Objectives: {', '.join(entry.get('objectives', []))}\n"
                        history_context += f"  Exit Code: {entry.get('exit_code')}\n"
        except Exception as e:
            print(f"[!] Warning: Could not read history for recovery: {e}")

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
        f"{history_context}\n"
        "--- ORIGINAL PROMPT ---\n"
        f"{original_prompt}\n\n"
        "--- FAILED OUTPUT (LAST 50 LINES) ---\n"
        f"{failure_output}\n\n"
        "--- INSTRUCTIONS ---\n"
        "1. Provide your analysis and classification first, incorporating the detected execution signals and historical context if relevant.\n"
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
