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

# 2. Interactive config (provider, API key env var, model catalogs)
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
3. Pick from the recommended catalog, switch to the full configured catalog, or type an alias/model ID

The result is written to `project-ai/minilegion.config.json`.

`config model` uses the same flow later: it reads `recommended_models`, `all_models`, and `model_aliases` from config, then writes the canonical model ID back to disk.

### Providers and default catalogs

| Provider | Slug | Env var | Recommended models | Additional full-catalog examples |
|----------|------|---------|--------------------|----------------------------------|
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` | `gpt-4.1`, `o1` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-7-sonnet-20250219`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229` | `claude-3-5-sonnet-20241022` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | `gemini-2.0-flash`, `gemini-2.0-pro`, `gemini-1.5-flash` | `gemini-1.5-pro` |
| Ollama (local) | `ollama` | *(none)* | `llama3.2`, `mistral`, `deepseek-r1`, `qwen2.5-coder` | `phi4` |
| OpenRouter / compatible | `openai-compatible` | `OPENROUTER_API_KEY` | `openrouter/auto`, `anthropic/claude-3.7-sonnet`, `openai/gpt-4o-mini`, `google/gemini-2.0-flash`, `meta-llama/llama-3.3-70b-instruct` | `deepseek/deepseek-r1` |

Aliases are provider-specific shortcuts stored in `model_aliases`. Examples from the shipped defaults include `mini -> gpt-4o-mini`, `reasoning -> o3-mini`, and `claude -> anthropic/claude-3.7-sonnet`. Aliases resolve before the config file is saved, so the persisted `model` value is always the canonical model ID.

### Manual config

`project-ai/minilegion.config.json` — all fields optional, defaults shown:

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "small_model": "gpt-4o-mini",
  "api_key_env": "OPENAI_API_KEY",
  "base_url": null,
  "timeout": 300,
  "max_retries": 2,
  "tool_permissions": "confirm",
  "recommended_models": {
    "openai": [
      {"id": "gpt-4o", "description": "GPT-4o - fast, multimodal flagship"},
      {"id": "gpt-4o-mini", "description": "GPT-4o mini - cheap, fast"},
      {"id": "o3-mini", "description": "o3-mini - reasoning model"}
    ]
  },
  "all_models": {
    "openai": [
      {"id": "gpt-4o", "description": "GPT-4o - fast, multimodal flagship"},
      {"id": "gpt-4o-mini", "description": "GPT-4o mini - cheap, fast"},
      {"id": "o3-mini", "description": "o3-mini - reasoning model"},
      {"id": "gpt-4.1", "description": "GPT-4.1 - newer general flagship"},
      {"id": "o1", "description": "o1 - high reasoning model"}
    ]
  },
  "model_aliases": {
    "openai": {
      "default": "gpt-4o",
      "fast": "gpt-4o-mini",
      "mini": "gpt-4o-mini",
      "reasoning": "o3-mini"
    }
  },
  "context_auto_compact": true,
  "provider_healthcheck": true,
  "engines": {},
  "scan_max_depth": 5,
  "scan_max_files": 200,
  "scan_max_file_size_kb": 100,
  "context": {
    "max_injection_tokens": 3000,
    "lookahead_tasks": 2,
    "warn_threshold": 0.7
  },
  "workflow": {
    "strict_mode": true,
    "require_validation": true
  },
  "research": {
    "default_mode": "fact",
    "default_options": 3,
    "min_options": 1,
    "max_options": 5,
    "require_recommendation": true
  }
}
```

Key config fields:

- `small_model` — first-class secondary default for cheaper or lighter-weight work.
- `tool_permissions` — validated at config load time; supported values are `confirm`, `allow`, and `deny`. Default is `confirm`.
- `timeout` — LLM request timeout in seconds. Default is `300`.
- `recommended_models` — curated provider catalog shown first in `config init` and `config model`.
- `all_models` — broader provider catalog available from the same interactive flow.
- `model_aliases` — provider-keyed shortcuts resolved to canonical model IDs before persistence.
- `context_auto_compact` — when true, deterministically truncates scanned codebase context to 50,000 chars before prompt rendering; appends an explicit truncation marker so the LLM knows data was cut.
- `provider_healthcheck` — when true, runs a fail-fast readiness check immediately after config load and before preflight, scanning, or any LLM calls in the research stage.

**`context` sub-block** (all fields optional, backward compatible):

- `context.max_injection_tokens` — max characters of the current-stage artifact injected into assembled context before truncation (default `3000`).
- `context.lookahead_tasks` — number of pending PLAN tasks included in `## Compact Plan` (default `2`).
- `context.warn_threshold` — warning ratio for assembled context size vs `max_injection_tokens`; emits a stderr warning when exceeded (default `0.7`).

**`workflow` sub-block** (all fields optional, backward compatible):

- `workflow.strict_mode` — reserved for future strict pre-flight enforcement (default `true`).
- `workflow.require_validation` — when true, `advance` requires passing evidence from `validate` before allowing a stage transition (default `true`).

**`research` sub-block** (all fields optional, backward compatible):

- `research.default_mode` — default research mode: `fact` (codebase scan) or `brainstorm` (default `"fact"`).
- `research.default_options` — number of candidate directions produced in brainstorm mode (default `3`; clamped to `min_options`/`max_options`).
- `research.min_options` / `research.max_options` — bounds for brainstorm option count (defaults `1` / `5`).
- `research.require_recommendation` — when true, the LLM must include a `recommended_option` in brainstorm output (default `true`).

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
| `minilegion research [--mode MODE] [--options N]` | Scan codebase (fact mode) or explore directions (brainstorm mode) |
| `minilegion design` | Call designer LLM from brief + research, save `DESIGN.json/.md` |
| `minilegion plan [--fast]` | Call planner LLM, save `PLAN.json/.md` with task list and `touched_files` |
| `minilegion execute [--task N] [--dry-run]` | Apply builder patches with per-patch approval |
| `minilegion review` | Call reviewer LLM; revise loop if verdict is `"revise"` |
| `minilegion archive` | Finalize cycle: coherence checks, write `DECISIONS.md`, close state |

### Utility commands

| Command | Description |
|---------|-------------|
| `minilegion history [-n N]` | Show the N most recent history events (default 10) |
| `minilegion validate <step>` | Validate a stage artifact set and write machine-readable evidence |
| `minilegion advance` | Advance one stage after passing validation (requires `workflow.require_validation`) |
| `minilegion context <tool>` | Assemble a portable context block for `claude`, `chatgpt`, `copilot`, or `opencode` |
| `minilegion rollback <reason>` | Roll back to the previous stage, preserving the current artifact in `rejected/` |
| `minilegion doctor` | Check project health: state validity, artifacts, history, and adapters |

### Flags

```bash
# brief
minilegion brief                          # reads from stdin

# research
minilegion research --mode brainstorm     # explore directions instead of scanning codebase
minilegion research --mode brainstorm --options 4   # request 4 candidate directions

# plan
minilegion plan --fast                    # skip research + design stages
minilegion plan --skip-research-design    # same as --fast

# execute
minilegion execute --dry-run              # print what would change, no writes
minilegion execute --task 3               # run only task 3 (1-indexed)

# history
minilegion history -n 20                  # show last 20 events

# validate / advance (explicit workflow)
minilegion validate research              # validate research artifact, write evidence
minilegion advance                        # advance to next stage (checks evidence first)

# context
minilegion context claude                 # assemble context for Claude
minilegion context opencode               # assemble context for OpenCode

# rollback
minilegion rollback "design needs rethink"   # step back one stage, keep artifact

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

### Brainstorm mode

```bash
minilegion research --mode brainstorm
minilegion research --mode brainstorm --options 4
```

Instead of scanning the codebase, the researcher LLM generates N candidate directions for solving the brief. Each direction includes a title, description, and trade-offs. When `research.require_recommendation` is true (the default), the LLM must designate one direction as the recommended option. The brainstorm output is saved as `RESEARCH.json/.md` and the standard pipeline continues from there.

### Codebase scanner (fact mode)

At the research stage in `fact` mode (the default), `scan_codebase()` builds LLM context from four sources:

- **Tech stack** — reads up to 500 chars of `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`
- **Directory tree** — walks up to 2 levels, 10 files per directory, excluding `.git`, `__pycache__`, `node_modules`, `.venv`, `dist`, `build`
- **Import patterns** — extracts imports from `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.go` files, grouped by language
- **Naming conventions** — counts snake_case / camelCase / PascalCase across source files

Configurable limits: `scan_max_depth`, `scan_max_files`, `scan_max_file_size_kb`.

### Append-only history

Every state change (init, approval, advance, rollback, etc.) is appended as an individual JSON file under `project-ai/history/` with a monotonic numeric prefix:

```
project-ai/history/
├── 001_init.json
├── 002_brief.json
├── 003_research.json
└── ...
```

`STATE.json` no longer embeds a rolling history array — history is now the canonical record. Use `minilegion history` to read it or inspect the files directly.

### Validation evidence

`minilegion validate <step>` checks pre-flight conditions for a stage and writes a machine-readable result to `project-ai/evidence/<step>.validation.json`:

```json
{
  "step": "research",
  "status": "pass",
  "checks_passed": ["preflight:research"],
  "validator": "preflight",
  "tool_used": "minilegion",
  "date": "2026-03-12T10:00:00",
  "notes": "Validation passed"
}
```

When `workflow.require_validation` is true, `minilegion advance` reads this file and blocks if evidence is missing or not passing.

### Context assembly

`minilegion context <tool>` assembles a portable markdown block from the current project state and writes it to `project-ai/context/<tool>.md`. Paste the block at the start of a conversation with your AI tool to give it full project context.

The assembled block has five sections:

| Section | Source |
|---------|--------|
| `## Current State` | `STATE.json` + last 3 history events |
| `## Compact Plan` | `PLAN.json` — next N pending tasks (`context.lookahead_tasks`) |
| `## Previous Artifact` | Most recent stage artifact (e.g. `RESEARCH.md`) — truncated to `context.max_injection_tokens` chars |
| `## Stage Template` | `project-ai/templates/<stage>.md` (created by `init`) |
| `## Memory` | `project-ai/memory/decisions.md`, `glossary.md`, `constraints.md` |
| `## Adapter Instructions` | `project-ai/adapters/<tool>.md` or `_base.md` |

All sections degrade gracefully — missing files are skipped, never errors.

Supported tools: `claude`, `chatgpt`, `copilot`, `opencode`.

### Rollback

```bash
minilegion rollback "design needs a different approach"
```

Rolls back to the previous pipeline stage. The current stage's artifact (e.g. `DESIGN.json`) is moved to `project-ai/rejected/DESIGN.<timestamp>.rejected.json` before any state mutation, so nothing is permanently lost. The rollback reason and affected stages are recorded in history.

### Doctor

```bash
minilegion doctor
```

Runs six health checks and prints a colour-coded `[PASS]` / `[WARN]` / `[FAIL]` result for each:

1. **State valid** — `STATE.json` parses and current stage is a known value
2. **Artifact present** — the expected artifact for the current stage exists
3. **History readable** — at least one history event is readable
4. **Stage coherence** — approvals are consistent with the current stage
5. **Base adapter present** — `project-ai/adapters/_base.md` exists
6. **Active adapter present** — `project-ai/adapters/<configured-provider>.md` exists

Exit codes: `0` = all pass, `1` = warnings only, `2` = at least one failure.

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
    ├── STATE.json                # current stage, approvals, metadata
    ├── BRIEF.md                  # task description
    ├── RESEARCH.json / .md       # codebase analysis (fact) or directions (brainstorm)
    ├── DESIGN.json / .md         # architecture decisions  (absent in fast mode)
    ├── PLAN.json / .md           # task list and touched_files
    ├── EXECUTION_LOG.json / .md  # applied patches (may be rewritten by revise loop)
    ├── REVIEW.json / .md         # review verdict and corrective actions
    ├── DECISIONS.md              # archived architecture decisions
    ├── history/                  # append-only event files (001_init.json, ...)
    ├── evidence/                 # per-step validation evidence (<step>.validation.json)
    ├── context/                  # assembled context blocks (<tool>.md)
    ├── adapters/                 # tool-specific context adapter instructions
    │   ├── _base.md
    │   ├── claude.md
    │   ├── chatgpt.md
    │   ├── copilot.md
    │   └── opencode.md
    ├── templates/                # per-stage prompt templates (one .md per stage)
    ├── memory/                   # persistent project memory
    │   ├── decisions.md
    │   ├── glossary.md
    │   └── constraints.md
    ├── prompts/                  # custom prompt templates (optional overrides)
    ├── rejected/                 # artifacts preserved by rollback
    └── debug/                    # created only on LLM validation failure
        └── {ARTIFACT}_RAW_DEBUG_{timestamp}.txt
```

Source files are written into the project root (next to `project-ai/`), not inside it. Their paths come from `PLAN.json touched_files`, resolved relative to the project root.

### STATE.json

`STATE.json` stores current stage, approvals, completed tasks, and metadata. History is no longer embedded here — it lives in `project-ai/history/` as individual append-only files.

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
  "history": [],
  "metadata": {
    "final_verdict": "pass"
  }
}
```

---

## Development

```bash
pip install -e ".[dev]"
pytest                          # 717 tests, no real API calls (fully mocked)
python -m ruff check minilegion/ tests/   # lint
```

---

## License

MIT
