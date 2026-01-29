# 🎧 chill-vibe 

### **The Reliability Layer for Autonomous Coding Agents.**

`chill-vibe` is a CLI orchestration layer that wraps autonomous coding agents (like Aider, Gemini-CLI, or Qwen) in a **Reasoning → Mission → Verification → Recovery** control loop. 

Most coding agents fail because success is implicit and retries are blind. `chill-vibe` fixes this by treating autonomous coding as a **closed-loop control system** rather than a chat interface.

---

## 🚀 Why chill-vibe?

If you've used autonomous agents, you know the **"Peak Brilliance vs. High Variance"** problem: an agent might solve a complex refactor in one go, then spend the next hour hallucinating a fix for a syntax error it just created.

**chill-vibe eliminates variance by enforcing:**
*   **Explicit Mission Contracts:** Gemini 2.0 generates a structured JSON contract with machine-verifiable success criteria *before* a single line of code is written.
*   **Automatic State Rollback:** If a mission fails verification, the system performs a `git reset --hard`. No more "corrupted state" loops.
*   **Grounded Recovery:** When an agent fails, `chill-vibe` classifies the error (Logic, Tooling, Environment) and injects "Lessons Learned" from previous failures into the next attempt.
*   **Full Context Visibility:** Uses `git-dump` to ensure the agent sees the entire architectural state, not just a few files.

---

## 🧠 The Control Loop

### 1. Context Extraction (The Eyes)
Aggregates your entire repository into a single, LLM-friendly context file using `git-dump`. This eliminates partial-context reasoning errors.

### 2. Strategic Reasoning (The Brain)
Uses **Gemini 2.0 (Flash or Pro)** to analyze the codebase and generate a **Mission Contract**:
*   **Objectives & Non-goals:** Clear boundaries for the agent.
*   **Machine-Verifiable Success Criteria:** Commands like `pytest`, `exists: path/to/file`, or `coverage: 80`.
*   **Expert Auditor Pass:** A second-pass validation ensures the mission is testable and safe before execution.

### 3. Autonomous Execution (The Muscle)
Launches your preferred agent (Aider, Gemini-CLI, Mentat, etc.) as a subprocess. The agent is treated as a precision executor of the Mission Contract.

### 4. Verification & Recovery (The Safety Net)
*   **Verification:** Runs the success criteria. If any fail, the mission is marked as failed.
*   **Rollback:** Automatically reverts the codebase to the pre-mission state.
*   **Memory-Aware Recovery:** The system analyzes the failure, classifies it, and generates a new strategy based on historical "Lessons Learned" from your `.chillvibe_logs.jsonl`.

---

## 📊 Competitive Landscape

| Feature | Cursor / Claude Code | Aider (Standalone) | **chill-vibe** |
| :--- | :--- | :--- | :--- |
| **Success Detection** | Human "Vibes" | Manual Testing | **Machine-Verifiable** |
| **Failure Recovery** | Manual Undo | Blind Retry | **Classified & Grounded** |
| **State Management** | Manual | Git Commits | **Auto-Rollback on Failure** |
| **Context Strategy** | RAG / Map | Repository Map | **Full-Repo git-dump** |
| **Model Lock-in** | Yes | No | **No (Bring your own agent)** |

---

## 🛠 Installation

```bash
# Clone and setup
git clone https://github.com/youruser/chill-vibe.git
cd chill-vibe
./setup.sh

# Set your API Key
export GEMINI_API_KEY='your-api-key-here'
```

---

## 📖 Usage

### Basic Command
```bash
chill-vibe . --agent aider --retry --rollback
```

### Key Options
*   `--agent`: Choose your executor (`aider`, `gemini-cli`, `qwen`, `mentat`, `gpt-me`).
*   `--thinking`: Set reasoning depth (`LOW`, `MEDIUM`, `HIGH`).
*   `--retry`: Enable the structured recovery loop.
*   `--rollback`: Automatically `git reset` if verification fails.
*   `--history`: View the log of past missions and failure classifications.

---

## ⚙️ Configuration

Customize `chill-vibe` per project by creating a `.chillvibe.yaml` file:

```yaml
model: "gemini-2.0-pro-exp-02-05"
thinking_level: "HIGH"
max_cost: 1.50  # Stop if mission costs > $1.50

# Files the agent is NEVER allowed to change
protected_files:
  - "src/auth/crypto.py"
  - "config/production.yaml"

exclude_patterns:
  - "**/tests/data/**"
```

---

## 📝 Mission Logging & Memory

Every mission is logged to `.chillvibe_logs.jsonl`. This file isn't just for show—it's the system's **Memory**. 

When a mission fails, `chill-vibe` searches this log for the most relevant "Lessons Learned" from previous failures (using weighted signal matching) and feeds them into the recovery prompt. This prevents the agent from making the same mistake twice.

---

## ⚖️ License

MIT License. See `LICENSE` for details. 

*Built for developers who want autonomous coding to feel like a control system, not a slot machine.* 🎧