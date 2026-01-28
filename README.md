# chill-vibe 🎧

**chill-vibe** is a CLI orchestration layer for autonomous coding agents that optimizes *reliability, determinism, and recovery* rather than raw model intelligence.

It implements a **Reasoning → Mission → Verification → Recovery** control loop that consistently outperforms direct agent invocation on complex, multi-file codebases—without requiring larger models, IDE lock-in, or human babysitting.

chill-vibe’s advantage is architectural: it makes autonomous coding **harder to fail**.

---

## 🚀 What Makes chill-vibe Different

Most coding agents rely on:

* implicit success (“this looks done”),
* blind retries,
* model self-assessment,
* and human intervention.

**chill-vibe replaces those failure points with explicit structure:**

* **Machine-verifiable success criteria** (not vibes)
* **Low-entropy, checklist-driven agent prompts**
* **Failure classification + targeted recovery strategies**
* **Deterministic behavior across different models**

This shifts performance from *peak brilliance* to *variance compression*—the dominant failure mode of autonomous agents today.

---

## 🧠 The Architecture

chill-vibe operates as a four-stage control loop:

### Phase A: Context Extraction (The "Eyes")

Uses `git-dump` to aggregate the entire repository into a single, LLM-friendly context file (default: `codebase_context.txt`).

This guarantees full architectural visibility and eliminates partial-context reasoning errors.

---

### Phase B: Strategic Reasoning (The "Brain")

Uses Gemini (default: `gemini-3-flash-preview`) exclusively for *planning*, not execution.

Outputs a **deterministic mission contract** containing:

* Explicit objectives
* Forbidden actions
* Ordered execution checklist
* **Machine-verifiable success criteria** (commands, file checks, invariants)

This step intentionally reduces prompt entropy and removes open-ended interpretation.

---

### Phase C: Autonomous Execution (The "Muscle")

Launches a coding agent (`gemini-cli`, `qwen`, `aider`, etc.) as a subprocess.

* The agent receives a self-contained mission
* No further interpretation or planning is required
* The agent is treated as a precision executor

---

### Phase D: Verification & Recovery (The Control Loop)

After execution:

1. Success criteria are run automatically. Supports shell commands and state-based invariants:
   * `exists: <path>` (file or directory existence)
   * `contains: <path> <regex>` (content validation)
   * `not_contains: <path> <regex>` (absence validation)
2. If *any* criterion fails, the mission is marked as failed—even if the agent exited cleanly.
3. Failures are **grounded and classified** using execution signals (exit codes, error patterns) into:

   * `LOGIC`
   * `TOOLING`
   * `ENVIRONMENT`
   * `AMBIGUITY`
4. A **targeted recovery strategy** is generated based on the failure class
5. The mission is retried with adapted instructions

This loop converts retries from blind restarts into informed adaptation.

---

## 📊 Competitive Positioning

| System         | Success Detection      | Recovery Quality          | Determinism | Model Lock-in | Expected Task Reliability |
| -------------- | ---------------------- | ------------------------- | ----------- | ------------- | ------------------------- |
| Claude Code    | Human judgment         | Manual                    | Low–Medium  | Yes           | High, high variance       |
| Codex Agent    | Partial (tests)        | Blind retry               | Medium      | Yes           | High, brittle             |
| Cursor Agent   | Implicit               | Manual                    | Low         | Yes           | Medium–High               |
| Devin          | Scripted               | Weak                      | Medium      | Yes           | Medium                    |
| **chill-vibe** | **Machine-verifiable** | **Targeted control loop** | **High**    | **No**        | **High, low variance**    |

chill-vibe does not replace better models—it **multiplies their reliability**.

---

## 🛠 Installation

```bash
git clone <repo-url> chill-vibe
cd chill-vibe
pip install .
export GEMINI_API_KEY='your-google-api-key'
```

---

## 📖 Usage

```bash
chill-vibe [path_to_repo] [options]
```

### Key Options

* `--agent` – Execution agent (`gemini-cli`, `aider`, `qwen`, `mentat`, `gpt-me`)
* `--thinking` – Reasoning depth for planning (`HIGH` default)
* `--model` – Gemini model for planning
* `--dry-run` – Generate mission without executing
* `--retry` – Enable structured recovery loop
* `--history` – View mission logs
* `--doctor` – Environment diagnostics

---

## 📝 Mission Logging

All missions are logged to `.chillvibe_logs.jsonl`, including:

* generated mission contracts
* success criteria
* failure classifications
* recovery strategies

This enables auditability, debugging, and reproducibility—features absent in most agent workflows.

---

## 💡 When to Use chill-vibe

Best suited for:

* Medium-to-large repositories
* Cross-cutting architectural changes
* Poorly documented codebases
* Long-running autonomous tasks

Not optimized for:

* Single-file edits
* Trivial changes
* Interactive pair-programming

---

## 🧠 Philosophy

Autonomous coding doesn’t fail because models are weak.

It fails because **success is implicit, retries are blind, and responsibility is fuzzy**.

chill-vibe fixes that—by turning autonomous coding into a control system instead of a guessing game.

---

## 📄 License

See `LICENSE` for details.
