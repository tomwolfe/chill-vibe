import os
import re
import time
import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
from .constants import DEFAULT_CONFIG
from .models import MissionContract
from .memory import MemoryManager
from .rules import get_global_rules

try:
    from google import genai
    from google.genai import types 
except ImportError:
    genai = Any # type: ignore
    types = Any # type: ignore

def log_mission(mission: Union[MissionContract, str], model_id: str, agent_name: str, duration: float, status: str = "UNKNOWN", exit_code: Optional[int] = None, classification: Optional[str] = None, verification_results: Optional[List[Dict[str, Any]]] = None, lessons_learned: Optional[str] = None, signals: Optional[List[str]] = None, budget_report: Optional[Dict[str, Any]] = None, diff_stats: Optional[Dict[str, int]] = None) -> None:
    """Log the mission details to a hidden file."""
    log_file = Path(".chillvibe_logs.jsonl")
    
    if isinstance(mission, MissionContract):
        success_criteria = mission.success_criteria
        agent_prompt = mission.agent_prompt
        objectives = mission.objectives
    else:
        success_criteria = []
        agent_prompt = mission
        objectives = []

    log_entry: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model_id": model_id,
        "agent_name": agent_name,
        "duration_seconds": round(duration, 2),
        "status": status,
        "exit_code": exit_code,
        "classification": classification,
        "signals": signals,
        "lessons_learned": lessons_learned,
        "success_criteria": success_criteria,
        "verification_results": verification_results,
        "agent_prompt": agent_prompt,
        "objectives": objectives,
        "diff_stats": diff_stats
    }
    if budget_report:
        log_entry.update(budget_report)
        # mission contract specifically asked for 'total_tokens' in logs
        if "total_tokens" not in log_entry:
            log_entry["total_tokens"] = budget_report.get("total_tokens", 0)

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[!] Warning: Could not write to log file: {e}")

def show_history() -> None:
    """Read and format the mission history from .chillvibe_logs.jsonl."""
    log_file = Path(".chillvibe_logs.jsonl")
    if not log_file.exists():
        print("No history found.")
        return

    print(f"{ 'Timestamp':<20} | { 'Model':<25} | { 'Agent':<15} | { 'Status':<10} | { 'Tokens':<8}")
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
                    tokens = entry.get("total_tokens", 0)
                    print(f"{timestamp:<20} | {model:<25} | {agent:<15} | {status:<10} | {tokens:<8}")
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading history: {e}")

def show_report() -> None:
    """Read and format a detailed summary report from .chillvibe_logs.jsonl."""
    log_file = Path(".chillvibe_logs.jsonl")
    if not log_file.exists():
        print("No logs found for report.")
        return

    print(f"{ 'Timestamp':<20} | { 'Status':<12} | { 'Cost ($)':<10} | { 'Model':<25} | { 'Summary'}")
    print("-" * 110)
    
    try:
        with open(log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    timestamp = entry.get("timestamp", "N/A")
                    status = entry.get("status", "N/A")
                    cost = entry.get("total_cost", 0.0)
                    model = entry.get("model_id", "N/A")
                    
                    # Extract a short summary from objectives if available
                    objectives = entry.get("objectives", [])
                    summary = objectives[0] if objectives else entry.get("agent_prompt", "")[:40] + "..."
                    if len(summary) > 40:
                        summary = summary[:37] + "..."
                        
                    print(f"{timestamp:<20} | {status:<12} | {cost:<10.6f} | {model:<25} | {summary}")
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading report: {e}")

def validate_mission(mission_contract: MissionContract, codebase_context: str, model_id: str, config_data: Optional[Dict[str, Any]] = None, budget_tracker: Any = None) -> Tuple[bool, str]:
    """Second-pass validation of the mission contract."""
    if genai is None:
        return True, ""

    client = genai.Client()
    
    mission_json_str = mission_contract.model_dump_json(indent=2)

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
        if budget_tracker:
            budget_tracker.update_from_response(response)

        if response.text:
            result = response.text.strip()
            if result.startswith("PASSED"):
                return True, ""
            else:
                return False, result
        return True, "" # Fallback
    except Exception as e:
        print(f"[!] Warning: Mission validation failed to run: {e}")
        return True, "" # Fallback to true if validation fails to execute

def get_strategic_reasoning(repo_path: str, context_file: str, model_id: str, thinking_level: str, config_data: Optional[Dict[str, Any]] = None, verbose: bool = False, budget_tracker: Any = None) -> MissionContract:
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
        "When grading, specifically look for 'Logic Regressions' and 'Type Safety'. "
        "I would like a prompt to give a coding agent to have the agent autonomously work on the attached codebase to achieve its goals for the project. "
    )
    
    project_constraints = ""
    if config_data:
        project_constraints = f"\n\n--- User-Defined Project Constraints ---\n{json.dumps(config_data, indent=2)}"

    global_rules = get_global_rules()
    global_rules_str = ""
    if global_rules:
        global_rules_str = f"\n\n--- GLOBAL PROJECT RULES ---\n{global_rules}"

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
        f"{global_rules_str}"
    )
    
    print(f"[*] Requesting strategic reasoning from {model_id} (Thinking level: {thinking_level})...")
    
    budgets: Dict[str, int] = DEFAULT_CONFIG["budgets"] # type: ignore
    thinking_budget = budgets.get(thinking_level.upper(), budgets["HIGH"])

    # Update config with thinking budget
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=thinking_budget
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
            if budget_tracker:
                budget_tracker.update_from_response(response)
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
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.thought:
                                print("\n--- INTERNAL THOUGHTS ---")
                                print(f"\033[2m{part.text}\033[0m")
                                print("-------------------------\n")
        except AttributeError:
            pass 

    full_text = response.text or ""
    
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
        mission = MissionContract(**mission_data)
        
        # Internal validation
        is_valid, error_msg = mission.validate_mission()
        if not is_valid:
            print(f"[!] Error: Mission contract validation failed: {error_msg}")
            sys.exit(1)
            
    except Exception as e:
        print(f"[!] Error parsing mission contract JSON: {e}")
        # Print the raw text for debugging if JSON parsing fails
        if verbose:
            print("--- RAW MISSION JSON ---")
            print(mission_contract_match.group(1))
        sys.exit(1)

    # Perform second-pass validation
    print("[*] Validating mission contract (second pass)...")
    valid, validation_msg = validate_mission(mission, codebase_context, model_id, config_data, budget_tracker=budget_tracker)
    if not valid:
        print(f"[!] Mission contract rejected by expert auditor:\n{validation_msg}")
        sys.exit(1)
    
    return mission

def classify_failure_signals(exit_code: int, last_output: List[str]) -> List[str]:
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

def get_recovery_strategy(repo_path: str, model_id: str, original_prompt: str, failure_output: List[str], exit_code: Optional[int] = None, config_data: Optional[Dict[str, Any]] = None, verification_results: Optional[List[Dict[str, Any]]] = None, budget_tracker: Any = None) -> Tuple[str, str, Optional[str], List[str]]:
    """Generate a recovery strategy after an agent fails, with grounded classification and memory."""
    if genai is None:
        print("Error: google-genai SDK not found.")
        sys.exit(1)

    client = genai.Client()
    
    signals = classify_failure_signals(exit_code, failure_output) if exit_code is not None else []
    signals_str = ", ".join(signals) if signals else "NONE"
    
    # Map signals to a tentative classification for memory lookup
    tentative_class = "UNKNOWN"
    if "COMMAND_NOT_FOUND" in signals or "PERMISSION_DENIED" in signals:
        tentative_class = "TOOLING"
    elif "TEST_FAILURE" in signals or "SYNTAX_ERROR" in signals:
        tentative_class = "LOGIC"
    elif "DEPENDENCY_MISSING" in signals or "ENVIRONMENT" in signals:
        tentative_class = "ENVIRONMENT"

    # Format verification results if available
    verification_context = ""
    error_details = ""
    if verification_results:
        verification_context = "\n--- VERIFICATION RESULTS ---\n"
        for res in verification_results:
            status = "PASSED" if res.get("passed") else "FAILED"
            verification_context += f"- [{status}] {res.get('criterion')}: {res.get('message')}\n"
            
            # Extract details for grounded recovery
            if not res.get("passed") and "details" in res:
                details = res["details"]
                if "stdout" in details or "stderr" in details:
                    error_details += f"\n--- Error snippet for {res.get('criterion')} ---\n"
                    if details.get("stdout"):
                        error_details += f"STDOUT:\n{details['stdout']}\n"
                    if details.get("stderr"):
                        error_details += f"STDERR:\n{details['stderr']}\n"

    if error_details:
        verification_context += "\n--- SPECIFIC ERROR DETAILS ---\n" + error_details
    
    # Read history for memory using MemoryManager
    memory = MemoryManager()
    current_success_criteria: Optional[List[str]] = None
    if verification_results:
        current_success_criteria = [str(res.get("criterion")) for res in verification_results if res.get("criterion") is not None]
    
    top_lessons = memory.get_top_lessons(tentative_class, signals=signals, limit=3, current_prompt=original_prompt, success_criteria=current_success_criteria)
    
    history_context = ""
    if top_lessons:
        history_context = "\n--- HISTORICAL LESSONS (Same Classification) ---\n"
        for i, lesson in enumerate(top_lessons, 1):
            history_context += f"{i}. {lesson}\n"
    else:
        # Fallback to general recent failures if no specific ones found
        recent_failures = memory.get_similar_failures("LOGIC", signals=signals, limit=2) + memory.get_similar_failures("TOOLING", signals=signals, limit=1)
        if recent_failures:
            history_context = "\n--- RECENT FAILURE HISTORY ---\n"
            for entry in recent_failures:
                history_context += f"- Date: {entry.get('timestamp')}\n"
                history_context += f"  Classification: {entry.get('classification')}\n"
                if entry.get('lessons_learned'):
                    history_context += f"  Lesson: {entry.get('lessons_learned')}\n"

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
        f"{verification_context}\n"
        f"{history_context}\n"
        "--- ORIGINAL PROMPT ---\n"
        f"{original_prompt}\n\n"
        "--- FAILED OUTPUT (LAST 50 LINES) ---\n"
        f"{failure_output}\n\n"
        "--- INSTRUCTIONS ---\n"
        "1. Provide a 'Lessons Learned' summary: what we tried, what specifically failed, and why. "
        "Wrap this summary in <lessons_learned> tags.\n"
        "2. Provide your analysis and classification, incorporating the detected execution signals, verification results, and historical context.\n"
        "3. Provide the failure classification wrapped in <classification> tags.\n"
        "4. Provide a NEW, targeted agent prompt wrapped in <agent_prompt> tags to fix the issue. "
        "Explicitly address why the previous attempt failed and what to avoid.\n"
    )
    
    print(f"[*] Requesting recovery strategy from {model_id}...")
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        if budget_tracker:
            budget_tracker.update_from_response(response)
    except Exception as e:
        print(f"Error calling Gemini API for recovery: {e}")
        return "", "UNKNOWN", None, []
        
    full_text = response.text or ""
    
    classification_match = re.search(r"<classification>(.*?)</classification>", full_text, re.IGNORECASE)
    classification = classification_match.group(1).strip() if classification_match else "UNKNOWN"
    
    lessons_learned_match = re.search(r"<lessons_learned>(.*?)</lessons_learned>", full_text, re.DOTALL | re.IGNORECASE)
    lessons_learned = lessons_learned_match.group(1).strip() if lessons_learned_match else None
    
    agent_prompt_match = re.search(r"(?:```(?:xml|html)?\s*)?<agent_prompt>(.*?)</agent_prompt>(?:\s*```)?", full_text, re.DOTALL)
    recovery_prompt = agent_prompt_match.group(1).strip() if agent_prompt_match else full_text
    
    return str(recovery_prompt), str(classification), lessons_learned, signals

