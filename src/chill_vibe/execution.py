import os
import sys
import shutil
import subprocess
import threading
import tty
import termios
import select

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
