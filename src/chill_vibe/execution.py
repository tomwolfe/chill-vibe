import os
import sys
import shutil
import subprocess
import threading
import tty
import termios
import select
import re
import hashlib
import fnmatch
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

def get_git_head(repo_path):
    """Get the current git HEAD commit hash."""
    try:
        process = subprocess.run(
            "git rev-parse HEAD",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if process.returncode == 0:
            return process.stdout.strip()
    except Exception:
        pass
    return None

def git_rollback(repo_path, commit_hash):
    """Rollback the repository to a specific commit."""
    if not commit_hash:
        return False
    
    print(f"[*] Rolling back to commit {commit_hash}...")
    try:
        # Check for uncommitted changes and discard them
        subprocess.run("git reset --hard", shell=True, cwd=repo_path, capture_output=True)
        # Then reset to the specific commit if provided (though --hard usually enough if we just want to revert what agent did)
        process = subprocess.run(
            f"git reset --hard {commit_hash}",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return process.returncode == 0
    except Exception as e:
        print(f"[!] Rollback failed: {e}")
        return False

def get_file_hash(file_path):
    """Calculate the MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def get_file_baseline(repo_path):
    """Get a dictionary of all files and their hashes."""
    baseline = {}
    for root, dirs, files in os.walk(repo_path):
        # Skip .git and __pycache__
        if ".git" in dirs:
            dirs.remove(".git")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
            
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), repo_path)
            baseline[rel_path] = get_file_hash(os.path.join(root, file))
    return baseline

def verify_success(success_criteria, repo_path, file_baseline=None, protected_files=None):
    """Run machine-verifiable success criteria (shell commands or invariants)."""
    results = []
    all_passed = True
    
    # 1. Automatic Invariants (e.g., no_clobber)
    if protected_files:
        print(f"[*] Running no-clobber check on {len(protected_files)} protected files...")
        current_baseline = get_file_baseline(repo_path)
        clobbered = []
        
        for pf in protected_files:
            # Handle potential globs or exact paths
            # For now, assume exact paths for simplicity, or we can use fnmatch
            matched_files = fnmatch.filter(current_baseline.keys(), pf)
            for f in matched_files:
                if f in file_baseline and current_baseline[f] != file_baseline[f]:
                    clobbered.append(f)
        
        result = {
            "criterion": "no_clobber",
            "passed": len(clobbered) == 0,
            "message": f"Protected files modified: {', '.join(clobbered)}" if clobbered else "No protected files modified",
            "details": {"clobbered_files": clobbered}
        }
        if not result["passed"]:
            print(f"    [✗] Failed: {result['message']}")
            all_passed = False
        else:
            print(f"    [✓] Passed")
        results.append(result)

    if not success_criteria:
        return all_passed, results

    print("\n[*] Verifying success criteria...")
    
    for criterion in success_criteria:
        print(f"[*] Running check: {criterion}")
        result = {
            "criterion": criterion,
            "passed": False,
            "message": "",
            "details": {}
        }
        try:
            if criterion.startswith("exists:"):
                # Check if file/dir exists
                path_str = criterion[len("exists:"):].strip()
                target_path = Path(repo_path) / path_str
                passed = target_path.exists()
                result["passed"] = passed
                result["message"] = f"Path {path_str} exists: {passed}"
                
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
                    message = f"File {file_path_str} does not exist"
                else:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Use multiline search for better matching in files
                        match = re.search(regex_pattern, content, re.MULTILINE | re.DOTALL)
                        if is_negative:
                            passed = not match
                            message = f"Pattern '{regex_pattern}' not found in {file_path_str}" if passed else f"Pattern '{regex_pattern}' found in {file_path_str}"
                        else:
                            passed = bool(match)
                            message = f"Pattern '{regex_pattern}' found in {file_path_str}" if passed else f"Pattern '{regex_pattern}' not found in {file_path_str}"
                
                result["passed"] = passed
                result["message"] = message
                result["details"] = {"file": file_path_str, "pattern": regex_pattern}

            elif criterion == "no_new_files":
                if file_baseline is None:
                    passed = True
                    message = "No file baseline provided for comparison"
                else:
                    current_files = set(get_file_baseline(repo_path).keys())
                    baseline_files = set(file_baseline.keys())
                    new_files = current_files - baseline_files
                    passed = len(new_files) == 0
                    message = f"New files detected: {', '.join(new_files)}" if not passed else "No new files detected"
                
                result["passed"] = passed
                result["message"] = message
                result["details"] = {"new_files": list(new_files) if file_baseline is not None else []}

            elif criterion.startswith("pytest"):
                # Run pytest
                args = criterion[len("pytest"):].strip()
                cmd = f"pytest {args}" if args else "pytest"
                process = subprocess.run(cmd, shell=True, cwd=repo_path, capture_output=True, text=True)
                passed = (process.returncode == 0)
                result["passed"] = passed
                result["message"] = f"Pytest exited with code {process.returncode}"
                
                # Capture last 20 lines of output for grounded recovery
                stdout_lines = (process.stdout or "").splitlines()
                stderr_lines = (process.stderr or "").splitlines()
                result["details"] = {
                    "stdout": "\n".join(stdout_lines[-20:]),
                    "stderr": "\n".join(stderr_lines[-20:]),
                    "exit_code": process.returncode
                }

            elif criterion.startswith("eval:"):
                # Run a python snippet to verify state
                code = criterion[len("eval:"):].strip()
                try:
                    # Provide some useful context for the evaluation
                    context = {
                        "os": os,
                        "sys": sys,
                        "Path": Path,
                        "repo_path": repo_path
                    }
                    passed = eval(code, {"__builtins__": __builtins__}, context)
                    result["passed"] = bool(passed)
                    result["message"] = f"Eval '{code}' returned {passed}"
                except Exception as e:
                    result["passed"] = False
                    result["message"] = f"Eval error: {e}"

            elif criterion.startswith("coverage:"):
                # Ensure a minimum test coverage percentage
                try:
                    min_cov = float(criterion[len("coverage:"):].strip())
                    # We run pytest-cov, assuming it's available or the user wants to check it
                    cmd = "pytest --cov=. --cov-report=term-missing"
                    process = subprocess.run(cmd, shell=True, cwd=repo_path, capture_output=True, text=True)
                    
                    # Parse the output for the TOTAL line
                    output = process.stdout
                    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
                    if match:
                        actual_cov = int(match.group(1))
                        passed = actual_cov >= min_cov
                        result["passed"] = passed
                        result["message"] = f"Coverage {actual_cov}% (minimum {min_cov}%)"
                        result["details"] = {"actual_coverage": actual_cov, "stdout": output}
                    else:
                        result["passed"] = False
                        result["message"] = "Could not parse coverage percentage from pytest output"
                        result["details"] = {"stdout": output}
                except ValueError:
                    result["passed"] = False
                    result["message"] = f"Invalid coverage threshold: {criterion}"
                except Exception as e:
                    result["passed"] = False
                    result["message"] = f"Coverage check error: {e}"

            elif criterion.startswith("ruff"):
                # Run ruff
                args = criterion[len("ruff"):].strip()
                cmd = f"ruff check {args}" if args else "ruff check ."
                process = subprocess.run(cmd, shell=True, cwd=repo_path, capture_output=True, text=True)
                passed = (process.returncode == 0)
                result["passed"] = passed
                result["message"] = f"Ruff exited with code {process.returncode}"
                
                stdout_lines = (process.stdout or "").splitlines()
                stderr_lines = (process.stderr or "").splitlines()
                result["details"] = {
                    "stdout": "\n".join(stdout_lines[-20:]),
                    "stderr": "\n".join(stderr_lines[-20:]),
                    "exit_code": process.returncode
                }
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
                result["passed"] = passed
                result["message"] = f"Command exited with code {process.returncode}"
                
                stdout_lines = (process.stdout or "").splitlines()
                stderr_lines = (process.stderr or "").splitlines()
                result["details"] = {
                    "stdout": "\n".join(stdout_lines[-20:]),
                    "stderr": "\n".join(stderr_lines[-20:]),
                    "exit_code": process.returncode
                }
            
            if result["passed"]:
                print(f"    [✓] Passed")
            else:
                print(f"    [✗] Failed")
                all_passed = False
            results.append(result)

        except Exception as e:
            print(f"    [!] Error running check: {e}")
            result["passed"] = False
            result["message"] = f"Error: {str(e)}"
            results.append(result)
            all_passed = False
            
    return all_passed, results

def get_change_summary(repo_path):
    """Generate a summary of changes using git diff."""
    try:
        # Check if it's a git repo
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return "Not a git repository. Change summary unavailable."

        # Get changed files (unstaged + staged)
        process = subprocess.run(
            "git status --short",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            return "Could not retrieve git status."
        
        status_output = process.stdout.strip()
        if not status_output:
            return "No changes detected."

        # Get diff summary
        diff_process = subprocess.run(
            "git diff --stat",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        summary = "--- CHANGE SUMMARY ---\n"
        summary += status_output + "\n\n"
        if diff_process.returncode == 0:
            summary += diff_process.stdout
        
        return summary
    except Exception as e:
        return f"Error generating change summary: {e}"
