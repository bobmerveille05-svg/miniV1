# Phase 1: Foundation & CLI - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Foundational infrastructure for MiniLegion: state machine managing 8 pipeline stages, atomic file I/O, config parsing, custom exception hierarchy, and CLI skeleton with 8 command stubs. This phase delivers the scaffolding that every subsequent phase builds on — no LLM calls, no schemas, no pipeline logic.

</domain>

<decisions>
## Implementation Decisions

### Project Layout
- Nested package structure: `minilegion/` with sub-packages `core/`, `cli/`, `adapters/`, `prompts/`
- Entry point: `run.py` at repo root — user runs `python run.py <command>`
- Dependencies declared in `pyproject.toml` with `[project]` metadata
- `minilegion init <name>` creates full template set in `project-ai/`: STATE.json, minilegion.config.json, BRIEF.md template, prompts/ directory

### State Machine Design
- Linear with backtrack: init → brief → research → design → plan → execute → review → archive. Can go backward but cannot skip forward.
- Backtracking clears downstream approvals (e.g., re-running research clears research_approved, design_approved, plan_approved)
- Single STATE.json as source of truth — holds current_stage, approvals dict, completed_tasks list, history entries, metadata
- STATE.json created immediately on `minilegion init` with stage="init", empty approvals, empty history

### CLI Behavior
- Framework: Typer (built on Click) for type hints, auto-help, colored output
- Error display: colored text only — red for errors, yellow for warnings, green for success. Uses Typer's built-in echo with color.
- Verbosity: `--verbose` flag. Default shows key actions (creating files, calling LLM, approvals). Verbose adds debug details (file paths, token counts, timing).
- Approval prompts: simple Y/n prompt with summary above. Lowercase default accepts on Enter.

### Config Structure
- Location: `project-ai/minilegion.config.json` inside the project directory
- Per-role engine assignment: top-level `model` field as default, `engines` dict with per-role overrides (`{"researcher": "gpt-4o", "builder": "gpt-4o-mini"}`). Unset roles use default.
- API key: configurable env var name via `api_key_env` field (default: "OPENAI_API_KEY"). Code reads `os.environ[config.api_key_env]`.
- Defaults: sensible defaults baked into code. Missing config fields fall back to defaults. Only fields the user wants to change need to be in the file.

### OpenCode's Discretion
- Exact sub-package boundaries within `minilegion/` (which modules go in `core/` vs top-level)
- Exception class naming and hierarchy details
- Atomic write implementation specifics (temp file naming, fsync behavior)
- Help text wording for CLI commands

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — this phase establishes the foundational patterns

### Integration Points
- `run.py` will import from `minilegion.cli` to set up Typer app
- `minilegion.core.state` will be imported by every pipeline command
- `minilegion.core.config` will be imported by adapter and pipeline modules in later phases

</code_context>

<specifics>
## Specific Ideas

- PROJECT.md specifies `run.py` as the CLI entrypoint — confirmed by user
- Research (STACK.md) recommended Typer + Pydantic + openai SDK — user confirmed Typer for CLI
- Config file named `minilegion.config.json` per PROJECT.md spec
- `project-ai/` as the working directory name per PROJECT.md spec

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-cli*
*Context gathered: 2026-03-10*
