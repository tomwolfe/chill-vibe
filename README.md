# chill-vibe 🎧

**chill-vibe** is a CLI tool that orchestrates a high-leverage "Reasoning-to-Code" pipeline. It solves the critical problem of context starvation in autonomous coding agents by using Gemini's reasoning capabilities to analyze an entire codebase and generate a precise, tailored mission statement—transforming a generic agent into a highly effective, project-specific executor.

## 🚀 The Workflow

The tool operates in three distinct phases:

### Phase A: Context Extraction (The "Eyes")
Uses `git-dump` to aggregate the entire codebase into a single, LLM-friendly context file (default: `codebase_context.txt`). This ensures the "Brain" has a complete, unfiltered view of the project's structure, patterns, dependencies, and logic—eliminating the blind spots that plague standard agent workflows.

### Phase B: Strategic Reasoning (The "Brain")
Initializes the `google-genai` SDK using `gemini-3-flash-preview`.
- **Analysis:** Gemini critically analyzes the codebase, identifying architecture, style, and hidden constraints.
- **Mission:** It generates a highly specific, **checklist-driven**, and **deterministic** agent prompt. By eliminating vague instructions, `chill-vibe` ensures the agent operates with low-entropy, high-precision guidance.
- **Success Criteria:** It defines objective, **machine-verifiable success criteria** (shell commands, file checks, or invariants) that must pass for the mission to be considered successful.

### Phase C: Autonomous Execution (The "Muscle")
Launches a specialized coding agent (like `gemini-cli` or `qwen-code`) as a subprocess.
- **Handoff:** The strategic prompt from Phase B is automatically piped into the agent's input stream.
- **Verification:** After the agent completes its task, `chill-vibe` automatically runs the mission's success criteria. If the criteria fail (even if the agent exited with code 0), the mission is marked as a failure.
- **Structured Recovery (Control Loop):** If an agent fails or success criteria are not met, `chill-vibe` performs **failure classification** (`TOOLING`, `LOGIC`, `ENVIRONMENT`, `AMBIGUITY`). It then generates a targeted recovery strategy specifically designed for that failure class and retries the mission.

## 🛠 Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url> chill-vibe
   cd chill-vibe
   ```

2. **Install the package:**
   ```bash
   pip install .
   ```

3. **Configure your API Key:**
   ```bash
   export GEMINI_API_KEY='your-google-api-key'
   ```

## 📖 Usage

```bash
chill-vibe [path_to_repo] [options]
```

### Arguments:
- `path`: The directory of the repository you want to analyze and modify.
- `--agent`: Choice of coding agent: `gemini-cli` (default), `aider`, `qwen`, `mentat`, or `gpt-me`.
- `--thinking`: Thinking level for Gemini reasoning: `HIGH` (default), `MEDIUM`, or `LOW`.
- `--model`: The Gemini model ID (default: `gemini-3-flash-preview`).
- `--dry-run`: Extracts context and generates the strategic prompt without launching the coding agent.
- `--context-file`: The file to store the extracted codebase context (default: `codebase_context.txt`).
- `--cleanup`: Delete the context file after execution.
- `--retry`: If the agent fails, automatically request a recovery strategy and retry once.
- `--history`: Show mission history from `.chillvibe_logs.jsonl`.
- `--doctor`: Run a diagnostic check on the environment and agents.
- `--version`: Show the program's version number and exit.

### Example:
```bash
chill-vibe . --dry-run --cleanup
```

## ⚙️ Configuration

You can customize the project behavior and agent parameters using a `.chillvibe.json`, `.chillvibe.yaml`, or `.chillvibe.yml` file in the target directory.

### Example `.chillvibe.yaml`:
```yaml
extra_args: ["--no-auto-commit"]
```

If `extra_args` is provided, they will be appended to the coding agent's base command.

## 📝 Mission Logging

`chill-vibe` automatically logs every mission strategy to a hidden file named `.chillvibe_logs.jsonl` in the current working directory. Use `chill-vibe --history` to view a formatted table of past missions. Each entry contains:
- `timestamp`: When the mission was generated.
- `model_id`: The Gemini model used for reasoning.
- `status`: Result of the mission (`COMPLETED`, `FAILED`, `INTERRUPTED`).
- `classification`: If the mission failed, the category of failure (e.g., `LOGIC`, `TOOLING`).
- `success_criteria`: The machine-verifiable checks generated for the mission.
- `agent_prompt`: The full strategic prompt sent to the coding agent.

## 🛡️ Robustness

`chill-vibe` gracefully handles both git repositories and standard directories. If a directory is not a git repository, it will provide a warning and fallback to standard folder processing for context extraction.

## 🧰 Dependencies
- **git-dump:** Installed automatically via `requirements.txt`.
- **google-genai:** Latest Python SDK for Gemini.
- **gemini-cli:** `npx @google/gemini-cli` must be available if using the default agent.

## 💡 Why This Matters

Generic coding agents, given vague prompts and no codebase context, often produce incorrect, inconsistent, or architecturally unsound code—they are effectively working blindfolded. `chill-vibe` eliminates this fundamental flaw. By providing a comprehensive, project-specific mission, it shifts the agent's role from a general-purpose guesser to a precision executor. This isn't an incremental improvement—it's a qualitative leap that makes complex, system-level autonomous coding feasible for the first time.

## 📄 License
Refer to the `LICENSE` file for details.