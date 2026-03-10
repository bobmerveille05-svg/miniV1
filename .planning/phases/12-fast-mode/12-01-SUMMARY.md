# Plan 12-01 Summary: Preflight Skip-Stages Support

**Status:** COMPLETE
**Date:** 2026-03-10
**Commit:** 6cbd253

## What Was Built

Extended `minilegion/core/preflight.py` with a `skip_stages` parameter that allows file and approval requirements to be bypassed for explicitly-skipped pipeline stages.

## Changes

### New dictionaries added to `preflight.py`

```python
STAGE_ARTIFACTS: dict[str, list[str]] = {
    "research": ["RESEARCH.json", "RESEARCH.md"],
    "design": ["DESIGN.json", "DESIGN.md"],
}

STAGE_APPROVALS: dict[str, list[str]] = {
    "research": ["research_approved"],
    "design": ["design_approved"],
}
```

### Updated `check_preflight()` signature

```python
def check_preflight(
    stage: Stage | str,
    project_dir: Path,
    skip_stages: set[str] | None = None,
) -> None:
```

### Filter logic

When `skip_stages` is provided, file and approval requirements belonging to skipped stages are excluded before validation. Non-skipped requirements are still enforced.

## Tests: 8 new (in `tests/test_preflight.py` — `TestSkipStages`)

1. `test_skip_stages_none_behaves_normally` — no skip_stages → identical behavior
2. `test_skip_research_skips_research_json_file_check`
3. `test_skip_design_skips_design_json_file_check`
4. `test_skip_both_skips_both_file_checks`
5. `test_skip_research_skips_research_approved_check`
6. `test_skip_design_skips_design_approved_check`
7. `test_non_skipped_file_still_checked` — BRIEF.md still required
8. `test_non_skipped_approval_still_checked` — brief_approved still required

## Backward Compatibility

All 22 existing preflight tests pass. `skip_stages=None` (the default) produces identical behavior to the previous implementation.
