# chill-vibe 🎧

**chill-vibe** is a CLI tool that orchestrates a high-leverage "Reasoning-to-Code" pipeline. It solves the critical problem of context starvation in autonomous coding agents by using Gemini's reasoning capabilities to analyze an entire codebase and generate a precise, tailored mission statement—transforming a generic agent into a highly effective, project-specific executor.

## 🚀 The Workflow

The tool operates in three distinct phases:

### Phase A: Context Extraction (The "Eyes")
Uses `git-dump` to aggregate the entire codebase into a single, LLM-friendly context file (default: `codebase_context.txt`). This ensures the "Brain" has a complete, unfiltered view of the project's structure, patterns, dependencies, and logic—eliminating the blind spots that plague standard agent workflows.

### Phase B: Strategic Reasoning (The "Brain")
Initializes the `google-genai` SDK using `gemini-3-flash-preview`.
- **Analysis:** Gemini critically analyzes the codebase, identifying architecture, style, and hidden constraints.
- **Strategy:** It defines clear, measurable goals and success criteria for the task at hand.
- **Mission:** It generates a highly specific, self-contained prompt designed *exclusively* for the downstream agent, embedding all necessary context. This is not a generic instruction—it is a project-specific blueprint.

### Phase C: Autonomous Execution (The "Muscle")
Launches a specialized coding agent (like `gemini-cli` or `qwen-code`) as a subprocess.
- **Handoff:** The strategic prompt from Phase B is automatically piped into the agent's input stream.
- **YOLO Mode:** For `gemini-cli`, it uses the `--yolo` flag to streamline operations.
- **Interactivity:** Unlike standard pipes, `chill-vibe` maintains a direct connection to your terminal, allowing you to monitor progress and provide manual input (e.g., "keep trying" or handling rate limits) while the agent works.

## 🛠 Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url> chill-vibe
   cd chill-vibe
   ```

2. **Run the setup script:**
   This will install required Python packages (`google-genai`, `pathspec`) and set permissions.
   ```bash
   ./setup.sh
   ```

3. **Configure your API Key:**
   ```bash
   export GEMINI_API_KEY='your-google-api-key'
   ```

## 📖 Usage

```bash
./chill-vibe.py [path_to_repo] [options]
```

### Arguments:
- `path`: The directory of the repository you want to analyze and modify.
- `--agent`: Choice of coding agent: `gemini-cli` (default) or `qwen`.
- `--thinking`: Thinking level for Gemini reasoning: `HIGH` (default), `MEDIUM`, or `LOW`.
- `--model`: The Gemini model ID (default: `gemini-3-flash-preview`).
- `--dry-run`: Extracts context and generates the strategic prompt without launching the coding agent.
- `--context-file`: The file to store the extracted codebase context (default: `codebase_context.txt`).
- `--cleanup`: Delete the context file after execution.
- `--version`: Show the program's version number and exit.

### Example:
```bash
./chill-vibe.py . --dry-run --cleanup --context-file temp_context.txt
```

## 🧰 Dependencies
- **git-dump:** Installed automatically via `requirements.txt`.
- **google-genai:** Latest Python SDK for Gemini.
- **gemini-cli:** `npx @google/gemini-cli` must be available if using the default agent.

## 💡 Why This Matters

Generic coding agents, given vague prompts and no codebase context, often produce incorrect, inconsistent, or architecturally unsound code—they are effectively working blindfolded. `chill-vibe` eliminates this fundamental flaw. By providing a comprehensive, project-specific mission, it shifts the agent's role from a general-purpose guesser to a precision executor. This isn't an incremental improvement—it's a qualitative leap that makes complex, system-level autonomous coding feasible for the first time.

## 📄 License
Refer to the `LICENSE` file for details.