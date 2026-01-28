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
* **Automatic State Rollback** (never start recovery from a corrupted state)
* **Second-pass mission validation** (expert auditor pass)
* **Structured JSON mission contracts** (zero ambiguity)
* **Failure classification + memory-aware recovery**
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

1. **Strategic Analysis**: Analyzes the codebase and user constraints to define a path forward.
2. **Mission Synthesis**: Generates a **structured JSON mission contract** containing:
   * Explicit objectives & Non-goals
   * Forbidden actions
   * Ordered execution checklist
   * **Machine-verifiable success criteria** (commands, file checks, invariants)
3. **Second-Pass Validation**: An "Expert Mission Auditor" pass reviews the contract for completeness, testability, and safety before execution.

This step intentionally reduces prompt entropy and removes open-ended interpretation.

---

### Phase C: Autonomous Execution (The "Muscle")

Launches a coding agent (`gemini-cli`, `qwen`, `aider`, etc.) as a subprocess.

* The agent receives a self-contained, checklist-driven mission.
* Pre-execution file baselines are captured for invariant checking.
* The agent is treated as a precision executor.

---

### Phase D: Verification & Recovery (The Control Loop)

After execution:

1. **Success Verification**: Criteria are run automatically and results are normalized into structured, machine-readable forms. Supports:
   * `pytest` & `ruff`: Semantic and linting checks.
   * `coverage: <min_percent>`: Enforces minimum test coverage.
   * `eval: <python_snippet>`: Custom state verification via Python one-liners.
   * `no_new_files`: Invariant enforcement.
   * `no_clobber`: Protects specific files from modification (defined in project config).
   * `exists: <path>`: File/directory existence.
   * `contains: <path> <regex>`: Content validation.
2. **Automatic State Rollback**: If verification fails and `--rollback` is enabled, the system automatically performs a `git reset --hard` to the pre-execution HEAD. This ensures the next recovery attempt starts from a clean slate rather than a "half-baked" or broken state.
3. **Change Summarization**: Generates a human-readable summary of all filesystem changes using `git diff`.
4. **Classification & Memory**: If checks fail, the failure is classified (LOGIC, TOOLING, etc.). The recovery engine generates a **"Lessons Learned"** summary that is persisted to `.chillvibe_logs.jsonl`.
5. **Targeted Bounded Recovery**: A recovery strategy is generated, incorporating **historical failure memory** (top 3 lessons from similar past failures) and the detailed verification results. The loop is explicitly bounded to prevent unproductive retries or repeated failure modes.

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
* `--rollback` – Enable automatic git rollback on verification failure
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
