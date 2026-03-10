# Plan 11-03 Summary: Archive Command Implementation

**Status:** COMPLETE
**Date:** 2026-03-10
**Commit:** 0157d0d

## What Was Built

Wired the `archive()` Typer command in `minilegion/cli/commands.py` and created `tests/test_cli_archive.py` with 10 tests.

## Implementation Details

### `archive()` Command (`commands.py`)
The archive command is the final stage in the pipeline. It has two notable exceptions to the standard pipeline pattern:

**Standard pipeline pattern:**
`find_project_dir()` → `load_config()` → `load_state()` → `StateMachine` → `can_transition()` → `check_preflight()` → read inputs → work → `save_state()`

**archive() exceptions:**
1. **NO `load_config()`** — archive makes zero LLM calls, so config is not needed
2. **NO `except ApprovalError`** — archive has no approval gate; only catches `MiniLegionError`

### Key Operations
1. `find_project_dir()` — locate `project-ai/` directory
2. `load_state()` — load current STATE.json
3. `StateMachine` with `can_transition(Stage.ARCHIVE)` guard
4. `check_preflight(Stage.ARCHIVE, ...)` — validates REVIEW.json, PLAN.json, EXECUTION_LOG.json, DESIGN.json exist, and `review_approved` flag is set
5. Load REVIEW.json → extract `verdict`
6. Load EXECUTION_LOG.json → extract task IDs as strings for `completed_tasks`
7. Load DESIGN.json → pass to `render_decisions_md()` for DECISIONS.md content
8. `check_coherence(project_dir)` — run all 5 coherence checks (non-blocking: issues logged but do not abort)
9. `write_atomic(project_dir / "DECISIONS.md", decisions_content)` — written BEFORE `save_state()`
10. Update state: `state.current_stage = Stage.ARCHIVE.value`, `state.metadata["final_verdict"]`, `state.metadata["completed_tasks"]`, `state.metadata["coherence_issues"]` (only if issues exist)
11. `save_state()` — persist updated STATE.json

### Import additions
- `DesignSchema` — needed for typing the design artifact loaded for render_decisions_md
- `render_decisions_md` — renders DECISIONS.md from design artifact
- `check_coherence` — runs the 5 coherence sub-checks

## Tests: 10 total (in `tests/test_cli_archive.py`)
- Happy path: DECISIONS.md written, state updated to ARCHIVE, completed_tasks populated
- Coherence issues: non-blocking (command succeeds even with errors/warnings)
- Preflight failure: exits with error when required files missing
- Wrong stage: exits when not in REVIEW stage
- State save: verifies STATE.json persisted correctly
- `test_archive_no_llm_calls`: verifies `OpenAIAdapter` is never instantiated

## Mocking Pattern
- `minilegion.cli.commands.find_project_dir` — patched to return tmp_path
- `minilegion.core.approval.typer.confirm` — not needed (no approval gate in archive)
- `minilegion.cli.commands.validate_with_retry` — not needed (no LLM calls in archive)
