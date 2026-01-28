import os
import sys
import shutil
import subprocess
import threading
import tty
import termios

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
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def forward_stdin(process):
    """Thread function to forward system stdin to the subprocess stdin."""
    try:
        with raw_mode(sys.stdin):
            while True:
                char = sys.stdin.read(1)
                if not char:
                    break
                process.stdin.write(char)
                process.stdin.flush()
    except (Exception, EOFError):
        pass
    finally:
        try:
            process.stdin.close()
        except:
            pass

class CodingAgent:
    """Represents a coding agent that can be executed."""
    def __init__(self, name, command, dependencies=None):
        self.name = name
        self.command = command
        self.dependencies = dependencies or []
        self.extra_args = []

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
        process = subprocess.Popen(
            full_command,
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
        threading.Thread(target=forward_stdin, args=(process,), daemon=True).start()
        
        try:
            return process.wait()
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
