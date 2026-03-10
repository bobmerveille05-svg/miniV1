# Phase 6: Brief & Research Stage - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Brief creation (BRIEF.md from free text + stdin) and the full research stage: deep context codebase scanner + Researcher pipeline stage producing RESEARCH.json + RESEARCH.md. This phase upgrades the `brief` and `research` CLI stubs into real implementations. It does NOT implement the design stage, LLM pipeline orchestration beyond research, or multi-model routing — those belong to Phases 7-8.

</domain>

<decisions>
## Implementation Decisions

### Brief Command Behavior
- `minilegion brief "some text"` creates BRIEF.md from the provided text, replacing BRIEF_TEMPLATE content with the user's text as the `## Overview` section (structured: Overview heading + raw text)
- If no text argument provided, read from stdin via `typer.get_text_stream("stdin").read()` — supports piped input AND interactive multi-line entry (terminated by EOF / Ctrl+D)
- After BRIEF.md is created, call `approve_brief()` to gate state transition — rejection leaves STATE.json unchanged (APRV-06)
- On approval: call `sm.transition(Stage.BRIEF)` and `save_state()` to advance state, then print success
- State transitions: INIT → BRIEF (brief command advances to BRIEF stage)
- BRIEF.md written atomically via `write_atomic()` before approval gate (file exists even if rejected, per append-only artifact principle)

### Deep Context Scanner
- Deep context module in `minilegion/core/context_scanner.py`
- Entry function: `scan_codebase(project_dir: Path, config: MiniLegionConfig) -> str` returning a formatted text blob consumed by the Researcher prompt `{{codebase_context}}`
- Configurable limits via `MiniLegionConfig` extensions (new fields with defaults): `scan_max_depth: int = 5`, `scan_max_files: int = 200`, `scan_max_file_size_kb: int = 100`
- Tech stack detection: read config files at root — `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`
- Import extraction: Python (`import X`, `from X import Y`), JS/TS (`import ... from '...'`, `require('...')`), Go (`import "..."`)
- Naming convention detection: detect snake_case vs camelCase vs PascalCase from identifiers in source files
- Directory structure: top-level dirs + first 2 levels, filtered (ignore `.git`, `__pycache__`, `node_modules`, `.venv`, `dist`, `build`)
- Output: structured text blob with sections: `## Tech Stack`, `## Directory Structure`, `## Key Files`, `## Import Patterns`, `## Naming Conventions` — plain text, not JSON

### Research Command Implementation
- `research` command in `commands.py`: load config, load state, run `check_preflight(Stage.RESEARCH, project_dir)`, scan codebase, load + render researcher prompt, call adapter, validate with retry, save dual (RESEARCH.json + RESEARCH.md), call `approve_research()`
- On approval: `sm.transition(Stage.RESEARCH)` and `save_state()`
- Adapter instantiation: `OpenAIAdapter(model=config.get_engine("researcher"), api_key_env=config.api_key_env, timeout=config.timeout)`
- Prompt rendering: `load_prompt("researcher")`, then `render_prompt(user_template, project_name=..., brief_content=..., codebase_context=...)`
- LLM call wired through `validate_with_retry(llm_call, "research", config.max_retries, project_dir)` — reuses Phase 2 retry/validation infrastructure
- RESEARCH.json and RESEARCH.md saved to `project_dir/` using `save_dual(data, project_dir/"RESEARCH.json", project_dir/"RESEARCH.md")`

### Error Handling & UX
- Pre-flight failure: print red error message and exit code 1 (consistent with existing `_pipeline_stub` pattern)
- Approval rejection: print yellow "Rejected" message and exit code 0 (not an error — user chose to not proceed)
- LLM/API errors: print red error message with exception text, exit code 1
- Missing API key: `LLMError` from `OpenAIAdapter` gives clear message before any API call
- All state mutations (approvals, stage transitions) happen AFTER all I/O and LLM calls succeed

### Commands.py Refactoring
- Replace `_pipeline_stub` call in `brief()` and `research()` with real implementations
- Keep `_pipeline_stub` for `design`, `plan`, `execute`, `review` (still stubs)
- `brief` command signature: `text: str | None = None` (already correct in existing stub)
- No new CLI flags needed for Phase 6 beyond what's already defined

### OpenCode's Discretion
- Exact format of the BRIEF.md output (heading structure, section titles)
- Scanner output format details (exact section headings, ordering of info)
- Whether to show a progress indicator during LLM call (typer.echo("Running researcher...") is sufficient)
- Test approach for scanner (unit tests with temp file trees vs integration tests)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `minilegion/core/preflight.py` — `check_preflight(stage, project_dir)` — already declares `Stage.RESEARCH: ["BRIEF.md"]` and `["brief_approved"]` requirements
- `minilegion/core/approval.py` — `approve_brief()` and `approve_research()` already implemented and tested
- `minilegion/core/retry.py` — `validate_with_retry(llm_call, schema_name, max_retries, project_dir)` — ready to use
- `minilegion/core/renderer.py` — `save_dual(data, json_path, md_path)` — saves both formats atomically
- `minilegion/adapters/openai_adapter.py` — `OpenAIAdapter` — ready for instantiation
- `minilegion/prompts/loader.py` — `load_prompt("researcher")` + `render_prompt()` — Phase 5 deliverable
- `minilegion/core/state.py` — `StateMachine.transition()`, `save_state()`, `load_state()` — all ready
- `minilegion/core/config.py` — `MiniLegionConfig` — needs `scan_max_depth`, `scan_max_files`, `scan_max_file_size_kb` fields added
- `minilegion/cli/commands.py` — `brief()` and `research()` stubs ready to be upgraded; `find_project_dir()` helper already exists

### Established Patterns
- `_pipeline_stub` pattern: load state → validate transition → run logic — Phase 6 replaces stubs with real implementations following same structure
- `write_atomic()` for all file writes — scanner output and BRIEF.md must use this
- `typer.echo(typer.style(..., fg=...))` for colored output — red for errors, green for success, yellow for warnings
- Exit via `raise typer.Exit(code=1)` on error, wrapped in `except MiniLegionError`
- `ProjectState.add_history()` + `save_state()` for all state mutations

### Integration Points
- `brief()` command replaces stub: creates BRIEF.md → calls `approve_brief()` → transitions state
- `research()` command replaces stub: `check_preflight` → `scan_codebase` → load prompt → `OpenAIAdapter` → `validate_with_retry` → `save_dual` → `approve_research` → transition state
- `MiniLegionConfig` gains 3 new scanner limit fields (with defaults — backward compatible)
- `context_scanner.py` is a new module with no dependencies outside stdlib + config model
- `ResearchSchema` (from Phase 2) is the validation target — no changes needed

</code_context>

<specifics>
## Specific Ideas

- Scanner must be testable without a real codebase — design it to accept a root path so tests can use `tmp_path` with synthetic file trees
- Deep context output should be human-readable text (not JSON) since it goes into the LLM prompt `{{codebase_context}}` slot which expects readable context
- RSCH-03 explicitly requires import extraction for Python, JS/TS, and Go — all three must be implemented even if Go/JS are less common
- The scanner respects `scan_max_depth` by skipping subdirectories beyond that depth
- `scan_max_file_size_kb` prevents reading huge generated files (e.g., minified JS, lock files)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-brief-research*
*Context gathered: 2026-03-10*
