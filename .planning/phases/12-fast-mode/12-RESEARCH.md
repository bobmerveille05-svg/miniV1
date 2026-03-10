# Phase 12 Research: Fast Mode

**Phase:** 12 — Fast Mode
**Date:** 2026-03-10

## Findings

### FAST-01 / FAST-02: --fast and --skip-research-design flags

Both flags are already defined in the `plan()` command signature (`commands.py:438-445`) as boolean Typer options — they are accepted but completely ignored. Implementation must:

1. Detect when either flag is set
2. Bypass the normal preflight (which requires RESEARCH.json, DESIGN.json, research_approved, design_approved)
3. Use a degraded context for the LLM: tree summary + brief (no research JSON, no design JSON)
4. Synthetically advance state through skipped stages before transitioning to PLAN

### State machine advancement for fast mode

`StateMachine.can_transition()` (`state.py:114-129`) only allows one step forward. To reach PLAN from BRIEF (skipping RESEARCH and DESIGN), the code must apply two synthetic transitions:

```python
sm.transition(Stage.RESEARCH)   # brief → research (synthetic)
sm.transition(Stage.DESIGN)     # research → design (synthetic)
sm.transition(Stage.PLAN)       # design → plan (normal)
```

But `sm.transition()` only updates `sm.current_stage`, NOT `state.current_stage`. The `state.current_stage` sync happens in the command after the full sequence. Only the final `Stage.PLAN` value matters for `state.current_stage`.

Also, approvals for research and design must be set to True (otherwise future `check_preflight` will fail for downstream stages that check `research_approved`/`design_approved`). These are set directly on `state.approvals` before `save_state()`.

### FAST-03: Recording skipped stages in STATE.json

`state.metadata` is `dict[str, str]` (string values only). Use:
```python
import json
state.metadata["skipped_stages"] = json.dumps(["research", "design"])
```

Downstream commands check:
```python
import json
skipped = json.loads(state.metadata.get("skipped_stages", "[]"))
```

### Preflight bypass for downstream stages

`check_preflight()` (`preflight.py:56`) has no awareness of skipped stages. When fast mode skips research+design:

- `Stage.EXECUTE` requires `["BRIEF.md", "RESEARCH.json", "DESIGN.json", "PLAN.json"]` files — RESEARCH.json/DESIGN.json won't exist
- `Stage.REVIEW` requires the same + EXECUTION_LOG.json
- `Stage.ARCHIVE` requires `["REVIEW.json", "PLAN.json", "EXECUTION_LOG.json", "DESIGN.json"]` — DESIGN.json won't exist

**Solution**: Add `skip_stages: set[str] | None = None` parameter to `check_preflight()`. When provided, files belonging to skipped stages are excluded from validation.

We need a mapping from stage name to the artifacts it produces:
```python
STAGE_ARTIFACTS: dict[str, list[str]] = {
    "research": ["RESEARCH.json", "RESEARCH.md"],
    "design": ["DESIGN.json", "DESIGN.md"],
}
```

When `skip_stages={"research", "design"}`, filter these filenames out of the REQUIRED_FILES check. Also filter approvals: `research_approved` and `design_approved`.

### Degraded LLM context for fast-mode planner

The planner prompt uses placeholders `{{research_json}}` and `{{design_json}}`. When in fast mode:

- `{{research_json}}` → result of `scan_codebase(project_dir.parent, config)` — actual codebase tree/structure
- `{{design_json}}` → minimal stub: `{"note": "Fast mode: no design phase run. Plan based on brief and codebase context."}`

This reuses the existing `scan_codebase()` from `context_scanner.py` which is already imported in `commands.py`.

### Affected files

| File | Change |
|---|---|
| `minilegion/core/preflight.py` | Add `skip_stages` param + `STAGE_ARTIFACTS` dict + filter logic |
| `minilegion/cli/commands.py` | Implement fast mode in `plan()` + add `skip_stages` to downstream preflight calls |

### Test locations

- `tests/test_preflight.py` — new `TestSkipStages` class (fast mode preflight bypass)
- `tests/test_cli_plan.py` — new `TestFastMode` class (fast mode plan command)

## Risks

1. **Approval flag leakage**: Setting `research_approved=True` and `design_approved=True` synthetically in fast mode might confuse the coherence checker in archive (COHR-01 checks focus_file vs context_files). Mitigation: `check_coherence()` is fail-safe (skips checks if files missing) — no impact.

2. **ARCHIVE preflight**: ARCHIVE requires DESIGN.json. When research+design were skipped, DESIGN.json doesn't exist. Mitigation: `check_preflight(Stage.ARCHIVE, ..., skip_stages={"research", "design"})` will filter DESIGN.json out of the check.

3. **Reviewer prompt**: review() reads RESEARCH.json/DESIGN.json as context. In fast mode, these files don't exist. Mitigation: Same pattern — pass codebase tree as research substitute and stub JSON as design substitute, similar to plan fast mode.

## Scope (what Phase 12 does NOT do)

- Does NOT create a new `planner_fast.md` prompt (reuses existing prompt with substituted context)
- Does NOT modify the state machine's `FORWARD_TRANSITIONS` dict
- Does NOT add any new Pydantic schemas
