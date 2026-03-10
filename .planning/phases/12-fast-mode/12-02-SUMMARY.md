# Plan 12-02 Summary: Fast Mode in plan() + Downstream Preflight Wiring

**Status:** COMPLETE
**Date:** 2026-03-10
**Commit:** 6cbd253

## What Was Built

Implemented fast mode in the `plan()` command and updated downstream commands to propagate `skip_stages` through `check_preflight()`.

## Key Components

### `_get_skip_stages(state)` helper (new)

Reads `state.metadata["skipped_stages"]` (a JSON string) and returns a `set[str]`. Returns empty set if absent or malformed.

### Fast mode path in `plan()`

When `--fast` or `--skip-research-design` is passed:

1. **Synthetic state machine transitions**: advances through RESEARCH → DESIGN synthetically (state machine still enforces one-step-at-a-time)
2. **Bypassed preflight**: `check_preflight(Stage.PLAN, ..., skip_stages={"research", "design"})`
3. **Degraded LLM context**: `{{research_json}}` = `scan_codebase()` tree; `{{design_json}}` = stub JSON note
4. **Normal LLM call**: same planner prompt, same `validate_with_retry`
5. **Synthetic approvals**: `state.approvals["research_approved"] = True`, `state.approvals["design_approved"] = True`
6. **Skip record**: `state.metadata["skipped_stages"] = '["design", "research"]'`

### Downstream updates

- `execute()`: reads `_get_skip_stages(state)` → passes to `check_preflight(Stage.EXECUTE, ...)`
- `review()`: reads skip_stages → passes to `check_preflight(Stage.REVIEW, ...)` + loads RESEARCH.json/DESIGN.json with fallback stubs
- `archive()`: reads skip_stages → passes to `check_preflight(Stage.ARCHIVE, ...)` + handles missing DESIGN.json (writes "Fast mode" DECISIONS.md stub)

### Test mock signature updates

All existing tests that mocked `check_preflight` with `lambda s, pd: None` updated to `lambda s, pd, **kw: None`. Named mock functions updated to `def mock_preflight(stage, pd, skip_stages=None)`.

## Tests: 8 new (in `tests/test_cli_plan.py` — `TestFastMode`)

1. `test_fast_flag_bypasses_design_preflight` — `--fast` from brief stage succeeds
2. `test_skip_research_design_flag_equivalent_to_fast`
3. `test_fast_mode_sets_skipped_stages_metadata`
4. `test_fast_mode_sets_synthetic_approvals`
5. `test_fast_mode_transitions_to_plan_stage`
6. `test_fast_mode_uses_scan_codebase`
7. `test_fast_mode_from_brief_stage`
8. `test_normal_mode_unchanged` — no flags → skip_stages=None
