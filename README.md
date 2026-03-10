# MiniLegion

A Python CLI that runs software tasks through a structured, LLM-assisted pipeline with a human approval gate after every stage.

```
init → brief → research → design → plan → execute → review → archive
```

Each stage calls an LLM, validates the output against a JSON schema, and stops for your approval before writing anything to `STATE.json`. Rejecting at any gate leaves every file unchanged and exits with code 0.

---

## Table of contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Commands reference](#commands-reference)
- [Pipeline in depth](#pipeline-in-depth)
- [Project structure](#project-structure)
- [Development](#development)

---

## How it works

1. You write a brief describing what you want done.
2. MiniLegion runs a **researcher** LLM to analyse your codebase and the brief.
3. A **designer** LLM proposes an architecture.
4. A **planner** LLM decomposes the work into tasks with an explicit list of files to touch (`touched_files`).
5. A **builder** LLM generates patches (create / modify / delete) and applies them with per-patch approval.
6. A **reviewer** LLM checks the result against the design and conventions.  
   If the verdict is `"revise"`, the builder is re-run automatically with corrective actions injected (up to 2 iterations).
7. **Archive** writes `DECISIONS.md`, records the final verdict and task list, and closes the cycle.

Every artifact is saved as both JSON (machine-readable, schema-validated) and Markdown (human-readable).

---

## Requirements

- Python 3.10+
- At least one LLM provider API key (or a local Ollama instance)

---

## Installation

```bash
git clone https://github.com/bobmerveille05-svg/miniV1.git
cd miniV1
pip install -e .
```

OpenAI is the default provider and is included in the base install.  
Add optional provider SDKs as needed:

```bash
pip install -e ".[anthropic]"      # Anthropic Claude
pip install -e ".[gemini]"         # Google Gemini
pip install -e ".[all-providers]"  # Anthropic + Gemini
pip install -e ".[dev]"            # pytest (for development)
```

Ollama requires no extra package — communication uses the standard library.

---

## Quick start

```bash
# 1. Create a project
minilegion init my-feature
cd my-feature

# 2. Interactive config (provider, API key env var, model)
minilegion config init

# 3. Write a brief
minilegion brief "Add a dark mode toggle to the settings page"

# 4. Run the pipeline — each step pauses for approval
minilegion research
minilegion design
minilegion plan
minilegion execute
minilegion review
minilegion archive
```

You can also pipe a brief from stdin:

```bash
cat SPEC.md | minilegion brief
```

---

## Configuration

### Interactive setup (recommended)

```bash
minilegion config init    # choose provider + API key + model
minilegion config model   # change the model at any time
```

`config init` walks you through three steps:

1. Choose a provider from a numbered menu
2. Set the API key environment variable name (default is suggested; Ollama is skipped)
3. Choose from the recommended model list for that provider

The result is written to `project-ai/minilegion.config.json`.

### Providers and recommended models

| Provider | Slug | Env var | Recommended models |
|----------|------|---------|-------------------|
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-7-sonnet-20250219`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | `gemini-2.0-flash`, `gemini-2.0-pro`, `gemini-1.5-flash` |
| Ollama (local) | `ollama` | *(none)* | `llama3.2`, `mistral`, `deepseek-r1`, `qwen2.5-coder` |
| OpenRouter / compatible | `openai-compatible` | `OPENROUTER_API_KEY` | `openrouter/auto`, `anthropic/claude-3.7-sonnet`, `openai/gpt-4o-mini`, `google/gemini-2.0-flash`, `meta-llama/llama-3.3-70b-instruct` |

### Manual config

`project-ai/minilegion.config.json` — all fields optional, defaults shown:

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key_env": "OPENAI_API_KEY",
  "base_url": null,
  "timeout": 120,
  "max_retries": 2,
  "engines": {},
  "scan_max_depth": 5,
  "scan_max_files": 200,
  "scan_max_file_size_kb": 100
}
```

**`base_url`** — required for `openai-compatible` and Ollama endpoints:

```json
{
  "provider": "openai-compatible",
  "model": "llama-3.3-70b-versatile",
  "api_key_env": "GROQ_API_KEY",
  "base_url": "https://api.groq.com/openai/v1"
}
```

```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "base_url": "http://localhost:11434"
}
```

**`engines`** — assign a different model per pipeline role:

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key_env": "OPENAI_API_KEY",
  "engines": {
    "planner": "gpt-4o",
    "builder": "gpt-4o"
  }
}
```

Valid role names: `researcher`, `designer`, `planner`, `builder`, `reviewer`.

---

## Commands reference

### Global flag

```
--verbose    Enable verbose output
```

### Pipeline commands

| Command | Description |
|---------|-------------|
| `minilegion init <name>` | Create a new project directory |
| `minilegion status` | Show stage, approvals, task count, and last history entry |
| `minilegion brief [TEXT]` | Write a brief (text argument or stdin) |
| `minilegion research` | Scan codebase, call researcher LLM, save `RESEARCH.json/.md` |
| `minilegion design` | Call designer LLM from brief + research, save `DESIGN.json/.md` |
| `minilegion plan [--fast]` | Call planner LLM, save `PLAN.json/.md` with task list and `touched_files` |
| `minilegion execute [--task N] [--dry-run]` | Apply builder patches with per-patch approval |
| `minilegion review` | Call reviewer LLM; revise loop if verdict is `"revise"` |
| `minilegion archive` | Finalize cycle: coherence checks, write `DECISIONS.md`, close state |

### Flags

```bash
# brief
minilegion brief                          # reads from stdin

# plan
minilegion plan --fast                    # skip research + design stages
minilegion plan --skip-research-design    # same as --fast

# execute
minilegion execute --dry-run              # print what would change, no writes
minilegion execute --task 3               # run only task 3 (1-indexed)

# config
minilegion config init                    # interactive provider + API key + model setup
minilegion config model                   # show current model, pick a new one
```

---

## Pipeline in depth

### Approval gates

Every stage except `init` and `archive` ends with a Y/N prompt. On rejection:

- `STATE.json` is **not touched** — the current stage does not advance
- Approval keys remain `false`
- Exit code is **0** — rejection is not an error

Approval keys are cleared automatically on any backward state transition (e.g. reviewer backtracks to design for a re-design).

### Schema validation and retries

Every LLM response is validated against a Pydantic schema. On a validation failure:

1. The error is summarised (up to 5 issues) and injected back into the next prompt
2. The call is retried — **3 total attempts** by default (`1 + max_retries`)
3. If all attempts fail, the raw output is saved to `project-ai/debug/{ARTIFACT}_RAW_DEBUG_{timestamp}.txt` and a `ValidationError` is raised

### Scope lock

`PLAN.json` contains `touched_files` — the list of files the builder is authorised to write. After every builder LLM call, `validate_scope()` raises an error if the output contains any path not in that list.

### Revise loop

If the reviewer returns verdict `"revise"`:

1. `corrective_actions` from the review are formatted and appended to the builder prompt
2. The builder re-runs (`validate_with_retry` → scope lock → per-patch approval)
3. `EXECUTION_LOG.json/.md` is overwritten with the revised output
4. The reviewer re-runs on the new diff
5. This repeats up to **2 revise iterations** — after which the user is asked to intervene manually
6. If `design_conformity.conforms` is `false`, the reviewer offers to backtrack to the design stage instead of revising

### Coherence checks (archive)

`archive` runs five cross-phase checks. None are blocking — the archive always completes. Issues are logged in `STATE.json`.

| ID | Checks | Severity |
|----|--------|----------|
| COHR-01 | Every file in `research.recommended_focus_files` appears in `design.components[*].files` | Warning |
| COHR-02 | Every design component name has at least one task in `plan.tasks[*].component` | Warning |
| COHR-03 | Every `execution_log.tasks[*].changed_files[*].path` is in `plan.touched_files` | Error |
| COHR-04 | `review.design_conformity.conforms` is `true` | Error |
| COHR-05 | `review.convention_violations` is empty | Warning |

### Fast mode

```bash
minilegion plan --fast
```

Skips the research and design stages. The planner receives the directory tree and brief directly. Synthetic approvals are set for `research_approved` and `design_approved` in STATE.json. All downstream commands (execute, review, archive) pick this up automatically via `skipped_stages` in `state.metadata`.

### Codebase scanner

At the research stage, `scan_codebase()` builds LLM context from four sources:

- **Tech stack** — reads up to 500 chars of `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`
- **Directory tree** — walks up to 2 levels, 10 files per directory, excluding `.git`, `__pycache__`, `node_modules`, `.venv`, `dist`, `build`
- **Import patterns** — extracts imports from `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.go` files, grouped by language
- **Naming conventions** — counts snake_case / camelCase / PascalCase across source files

Configurable limits: `scan_max_depth`, `scan_max_files`, `scan_max_file_size_kb`.

### Atomic writes

Every file write uses `write_atomic()`: write to a temp file → `os.fsync()` → `os.replace()`. An interrupted write never corrupts the existing file.

---

## Project structure

After a full pipeline run:

```
my-feature/
├── (your source files — written by execute)
└── project-ai/
    ├── minilegion.config.json    # provider, model, limits
    ├── STATE.json                # current stage, approvals, history, metadata
    ├── BRIEF.md                  # task description
    ├── RESEARCH.json / .md       # codebase analysis
    ├── DESIGN.json / .md         # architecture decisions  (absent in fast mode)
    ├── PLAN.json / .md           # task list and touched_files
    ├── EXECUTION_LOG.json / .md  # applied patches (may be rewritten by revise loop)
    ├── REVIEW.json / .md         # review verdict and corrective actions
    ├── DECISIONS.md              # archived architecture decisions
    ├── prompts/                  # custom prompt templates (optional)
    └── debug/                    # created only on LLM validation failure
        └── {ARTIFACT}_RAW_DEBUG_{timestamp}.txt
```

Source files are written into the project root (next to `project-ai/`), not inside it. Their paths come from `PLAN.json touched_files`, resolved relative to the project root.

### STATE.json

```json
{
  "current_stage": "archive",
  "approvals": {
    "brief_approved": true,
    "research_approved": true,
    "design_approved": true,
    "plan_approved": true,
    "execute_approved": true,
    "review_approved": true
  },
  "completed_tasks": ["task-1", "task-2"],
  "history": [
    { "timestamp": "2026-03-10T21:25:36", "action": "init", "details": "Project initialized" }
  ],
  "metadata": {
    "final_verdict": "pass"
  }
}
```

---

## Development

```bash
pip install -e ".[dev]"
pytest                          # 607 tests, no real API calls (fully mocked)
python -m ruff check minilegion/ tests/   # lint
```

---

## License

MIT
