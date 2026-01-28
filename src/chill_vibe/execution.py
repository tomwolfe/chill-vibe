import os
import sys
import shutil
import subprocess
import threading
import tty
import termios
import select
import re
from pathlib import Path

import time
import collections
import contextlib

@contextlib.contextmanager
def raw_mode(file):
    if not file.isatty():
        yield
        return
    
    fd = file.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        yield
    finally:
        # Restore terminal settings regardless of what happens
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def forward_stdin(process):
    """Thread function to forward system stdin to the subprocess stdin."""
    log_file = os.path.join(os.getcwd(), ".chillvibe_debug.log")
    try:
        with raw_mode(sys.stdin):
            while process.poll() is None:
                try:
                    # Use select to wait for input or process death
                    # 0.1s timeout allows frequent checks of process.poll()
                    r, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if r:
                        char = sys.stdin.read(1)
                        if not char:
                            break
                        process.stdin.write(char)
                        process.stdin.flush()
                except (EOFError, BrokenPipeError, OSError):
                    break
                except Exception:
                    time.sleep(0.01)
    except Exception as e:
        try:
            with open(log_file, "a") as f:
                import time
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] forward_stdin unexpected error: {e}\n")
        except:
            pass
    finally:
        try:
            # Ensure stdin is closed to signal EOF to the subprocess
            if process.stdin:
                process.stdin.close()
        except Exception:
            pass

def output_reader(pipe, stream, buffer):
    """Read from a pipe and write to both a stream and a circular buffer."""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                stream.write(line)
                stream.flush()
                buffer.append(line)
    except Exception:
        pass

class CodingAgent:
    """Represents a coding agent that can be executed."""
    def __init__(self, name, command, dependencies=None):
        self.name = name
        self.command = command
        self.dependencies = dependencies or []
        self.extra_args = []
        self.last_output = collections.deque(maxlen=50)

    def validate(self):
        """Check if all dependencies for this agent are installed."""
        missing = []
        for dep in self.dependencies:
            if not shutil.which(dep):
                missing.append(dep)
        return missing

    def run(self, agent_prompt):
        """Launch the coding agent with the provided prompt."""
        print(f"[*] Launching {self.name} in autonomous mode...")
        
        full_command = self.command + self.extra_args
        self.last_output.clear()
        
        process = subprocess.Popen(
            full_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout for easier tracking
            text=True,
            bufsize=1
        )
        
        # 1. Pipe the initial agent prompt
        process.stdin.write(agent_prompt + "\n")
        process.stdin.flush()
        
        # 2. Start a background thread to forward user input to the agent
        threading.Thread(target=forward_stdin, args=(process,), daemon=True).start()
        
        # 3. Start a background thread to capture and display output
        reader_thread = threading.Thread(
            target=output_reader, 
            args=(process.stdout, sys.stdout, self.last_output),
            daemon=True
        )
        reader_thread.start()
        
        try:
            exit_code = process.wait()
            # Give the reader thread a moment to finish capturing output
            reader_thread.join(timeout=1)
            return exit_code
        except KeyboardInterrupt:
            print(f"[*] chill-vibe: Terminating {self.name}...")
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            return 130 # Standard exit code for SIGINT

def run_coding_agent(agent_name, agent_prompt, registry, config_data=None):
    """Phase C: Autonomous Execution"""
    if agent_name not in registry:
        print(f"Unknown agent: {agent_name}")
        sys.exit(1)
    
    agent = registry[agent_name]
    if config_data and "extra_args" in config_data:
        agent.extra_args = config_data["extra_args"]
        
    return agent.run(agent_prompt)

def verify_success(success_criteria, repo_path):
    """Run machine-verifiable success criteria (shell commands or invariants)."""
    if not success_criteria:
        return True, []

    print("\n[*] Verifying success criteria...")
    results = []
    all_passed = True
    
    for criterion in success_criteria:
        print(f"[*] Running check: {criterion}")
        try:
            if criterion.startswith("exists:"):
                # Check if file/dir exists
                path_str = criterion[len("exists:"):].strip()
                target_path = Path(repo_path) / path_str
                passed = target_path.exists()
                results.append({
                    "command": criterion,
                    "passed": passed,
                    "info": f"Path {path_str} exists: {passed}"
                })
            elif criterion.startswith("contains:") or criterion.startswith("not_contains:"):
                # Check if file contains/doesn't contain regex
                is_negative = criterion.startswith("not_contains:")
                prefix = "not_contains:" if is_negative else "contains:"
                parts = criterion[len(prefix):].strip().split(None, 1)
                if len(parts) < 2:
                    raise ValueError(f"Invalid {prefix} criterion format. Expected '{prefix} <path> <regex>'")
                
                file_path_str, regex_pattern = parts
                file_path = Path(repo_path) / file_path_str
                
                if not file_path.exists():
                    passed = False
                    info = f"File {file_path_str} does not exist"
                else:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Use multiline search for better matching in files
                        match = re.search(regex_pattern, content, re.MULTILINE | re.DOTALL)
                        if is_negative:
                            passed = not match
                            info = f"Pattern '{regex_pattern}' not found in {file_path_str}" if passed else f"Pattern '{regex_pattern}' found in {file_path_str}"
                        else:
                            passed = bool(match)
                            info = f"Pattern '{regex_pattern}' found in {file_path_str}" if passed else f"Pattern '{regex_pattern}' not found in {file_path_str}"
                
                results.append({
                    "command": criterion,
                    "passed": passed,
                    "info": info
                })
            else:
                # Default to shell command
                process = subprocess.run(
                    criterion,
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                passed = (process.returncode == 0)
                results.append({
                    "command": criterion,
                    "passed": passed,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode
                })
            
            if passed:
                print(f"    [✓] Passed")
            else:
                print(f"    [✗] Failed")
                all_passed = False
        except Exception as e:
            print(f"    [!] Error running check: {e}")
            results.append({
                "command": criterion,
                "passed": False,
                "error": str(e)
            })
            all_passed = False
            
    return all_passed, results
