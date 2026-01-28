import argparse
import os
import sys
import time
from . import __version__
from .config import get_agent_registry, load_config, get_default_model
from .doctor import run_doctor, validate_environment
from .context import run_git_dump
from .reasoning import get_strategic_reasoning, log_mission, show_history, get_recovery_strategy
from .execution import run_coding_agent

def get_parser(registry):
    default_model = get_default_model()
    parser = argparse.ArgumentParser(description="chill-vibe: A Reasoning-to-Code CLI pipeline")
    parser.add_argument("path", nargs="?", help="The directory of the repo to analyze")
    parser.add_argument("--agent", default="gemini-cli", 
                        help=f"Choice of coding agent (default: gemini-cli). Available: {', '.join(registry.keys())}")
    parser.add_argument("--thinking", default="HIGH", 
                        help="Thinking level (default: HIGH)")
    parser.add_argument("--model", default=default_model, 
                        help=f"Model ID (default: {default_model})")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Output the context and the reasoning prompt without invoking the coding agent")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print the model's internal thinking/reasoning")
    parser.add_argument("--context-file", default="codebase_context.txt",
                        help="The file to store the extracted codebase context (default: codebase_context.txt)")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete the context file after execution")
    parser.add_argument("--retry", action="store_true",
                        help="If the agent fails, automatically request a recovery strategy and retry once")
    parser.add_argument("--depth", type=int, help="Limit how deep the context extraction crawls")
    parser.add_argument("--include-ext", help="Filter extraction to specific file extensions (e.g., py,md)")
    parser.add_argument("--exclude", help="Comma-separated list of glob patterns to ignore during context extraction")
    parser.add_argument("--doctor", action="store_true",
                        help="Run a diagnostic check on the environment and agents")
    parser.add_argument("--history", action="store_true",
                        help="Show mission history")
    parser.add_argument("--version", action="version", version=f"chill-vibe v{__version__}")
    return parser

def main():
    # Load registry (pass None initially to get defaults and global)
    registry = get_agent_registry()
    
    parser = get_parser(registry)
    args = parser.parse_args()

    if args.history:
        show_history()
        sys.exit(0)

    if args.doctor:
        run_doctor(registry)
        sys.exit(0)

    if not args.path:
        parser.print_help()
        sys.exit(0)
    
    # Reload registry with local path if available
    registry = get_agent_registry(args.path)
    
    # Pre-flight checks
    validate_environment(args.agent, registry)
    
    # Load project config
    config_data = load_config(args.path)
    
    # Phase A: Context Extraction
    exclude_patterns = config_data.get("exclude_patterns", [])
    if args.exclude:
        exclude_patterns.extend([p.strip() for p in args.exclude.split(",")])
    
    run_git_dump(args.path, args.context_file, exclude_patterns, args.depth, args.include_ext)
    
    if args.model == "flash":
        args.model = "gemini-3-flash-preview"

    try:
        if args.dry_run:
            print("\n[*] Dry-run mode: Context extracted.")
        
        # Phase B: Strategic Reasoning
        start_time = time.time()
        agent_prompt = get_strategic_reasoning(args.path, args.context_file, args.model, args.thinking, config_data, args.verbose)
        duration = time.time() - start_time
        
        if args.dry_run:
            log_mission(agent_prompt, args.model, args.agent, duration, status="DRY_RUN")
            print("\n--- GENERATED AGENT PROMPT ---")
            print(agent_prompt)
            print("------------------------------")
        else:
            # Phase C: Autonomous Execution
            exit_code = run_coding_agent(args.agent, agent_prompt, registry, config_data)
            
            # Retry mechanism
            if exit_code != 0 and exit_code != 130 and args.retry:
                print(f"\n[!] Agent {args.agent} failed with exit code {exit_code}. Attempting recovery...")
                agent = registry[args.agent]
                failure_output = "".join(list(agent.last_output))
                recovery_prompt = get_recovery_strategy(args.path, args.model, agent_prompt, failure_output, config_data)
                
                if recovery_prompt:
                    print("[*] Running recovery strategy...")
                    exit_code = run_coding_agent(args.agent, recovery_prompt, registry, config_data)
                    agent_prompt = recovery_prompt # Update for logging
                else:
                    print("[!] Failed to generate recovery strategy.")

            status = "COMPLETED" if exit_code == 0 else "FAILED"
            if exit_code == 130:
                status = "INTERRUPTED"
                
            log_mission(agent_prompt, args.model, args.agent, duration, status=status)
    finally:
        if args.cleanup and os.path.exists(args.context_file):
            print(f"[*] Cleaning up context file: {args.context_file}")
            os.remove(args.context_file)

if __name__ == "__main__":
    main()
