# Phase 10 Plan 02 — Summary

**Plan:** 10-02 — Wire review() command with revise loop
**Completed:** 2026-03-10
**Tests added:** 12 (test_cli_review.py)
**Total tests after:** 490

## What was built

### `minilegion/cli/commands.py` — `review()` fully implemented
Replaced stub with complete implementation:

1. **Standard pipeline setup**: `find_project_dir → load_config(parent) → load_state → StateMachine → can_transition(REVIEW) guard → check_preflight`
2. **Input reading**: PLAN.json, DESIGN.json, RESEARCH.json — extracts `existing_conventions`
3. **Main revise loop** (`while True`):
   - Reads EXECUTION_LOG.json, calls `generate_diff_text()`
   - `load_prompt("reviewer")` + `render_prompt(project_name, diff_text, plan_json, design_json, conventions)`
   - `OpenAIAdapter(config)` → `validate_with_retry(llm_call, user_message, "review", config, project_dir)`
   - `save_dual(REVIEW.json, REVIEW.md)`
   - `approve_review(state, STATE.json, review_md)` gate
   - **Verdict PASS**: transition to review stage, save state, return
   - **Revise limit check**: if `revise_count >= _MAX_REVISE_ITERATIONS` → escalate to human (exit 0)
   - **Non-conforming design**: `typer.confirm("Re-design before re-executing?")` → backtrack to design stage if yes
   - **Builder re-run**: increment `revise_count`, inject `corrective_actions`, `load_prompt("builder")`, re-run LLM, `validate_scope`, per-patch `approve_patch` + `apply_patch`, `save_dual(EXECUTION_LOG)`
4. **Error handling**: `ApprovalError` caught before `MiniLegionError`

### New constants/imports added
- `_MAX_REVISE_ITERATIONS = 2`
- Imports: `approve_review`, `generate_diff_text`, `ReviewSchema`, `Verdict`

## Key decisions
- `revise_count` in `state.metadata["revise_count"]` as string (metadata is `dict[str, str]`)
- `typer.confirm` for re-design called directly in commands.py (not through approval gate) — two separate mock targets in tests
- Builder re-run reuses `_read_source_files()` and same validate/apply_patch pattern as execute()
- `write_before_gate` principle: `save_dual(REVIEW.json)` before `approve_review()` gate
