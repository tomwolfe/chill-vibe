# chill-vibe 🎧

**chill-vibe** is a CLI tool that orchestrates a high-leverage "Reasoning-to-Code" pipeline. It bridges the gap between deep architectural analysis and autonomous execution by using Gemini's reasoning capabilities to analyze a codebase and then handing off a tailored mission to a coding agent.

## 🚀 The Workflow

The tool operates in three distinct phases:

### Phase A: Context Extraction (The "Eyes")
Uses `git-dump` to aggregate the entire codebase into a single, LLM-friendly context file (`codebase_context.txt`). This ensures the "Brain" has a complete view of the project's structure, patterns, and logic.

### Phase B: Strategic Reasoning (The "Brain")
Initializes the `google-genai` SDK using `gemini-3-flash-preview`.
- **Analysis:** Gemini critically analyzes the codebase and assigns it a "grade."
- **Strategy:** It identifies high-level goals and success metrics.
- **Mission:** It generates a highly specific, comprehensive prompt designed for a coding agent to execute the required work autonomously.

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

### Example:
```bash
./chill-vibe.py ../my-project --agent gemini-cli --thinking HIGH
```

## 🧰 Dependencies
- **git-dump:** Expected to be in `../git_dump` or available in your `PATH`.
- **google-genai:** Latest Python SDK for Gemini.
- **gemini-cli:** `npx @google/gemini-cli` must be available if using the default agent.

## 📄 License
Refer to the `LICENSE` file for details.
