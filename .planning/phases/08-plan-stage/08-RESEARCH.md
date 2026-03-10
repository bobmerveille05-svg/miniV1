# Phase 8 Research: Plan Stage

## Existing Infrastructure (Already Built)

### What's Already Done

**`minilegion/core/preflight.py`**
- `Stage.PLAN` already declared in `REQUIRED_FILES`: requires `BRIEF.md`, `RESEARCH.json`, `DESIGN.json`
- `Stage.PLAN` already declared in `REQUIRED_APPROVALS`: requires `brief_approved`, `research_approved`, `design_approved`
- `check_preflight(Stage.PLAN, project_dir)` will work immediately

**`minilegion/core/approval.py`**
- `approve_plan(state, state_path, plan_summary)` already fully implemented (lines 108-115)
- Sets `plan_approved` in STATE.json on acceptance

**`minilegion/core/schemas.py`**
- `PlanSchema` already fully defined (lines 123-133):
  - `objective: str`, `design_ref: str`, `assumptions`, `tasks: list[PlanTask]`, `touched_files`, `risks`, `success_criteria`, `test_plan: str`
- `PlanTask` already defined (lines 49-57): `id`, `name`, `description`, `files`, `depends_on`, `component`

**`minilegion/core/registry.py`**
- `"plan"` is already registered in `SCHEMA_REGISTRY` → `validate_with_retry("plan", ...)` works

**`minilegion/core/renderer.py`**
- `render_plan_md()` already fully implemented; `save_dual()` dispatches to it
- `save_dual(plan_data, project_dir/"PLAN.json", project_dir/"PLAN.md")` works immediately

**`minilegion/prompts/planner.md`**
- Fully implemented in Phase 5
- System: enforces "decompose, don't design", JSON-only
- USER_TEMPLATE: `{{project_name}}`, `{{brief_content}}`, `{{research_json}}`, `{{design_json}}`
- Note: variable name is `design_json` (not `design_content`)

**`minilegion/cli/commands.py`**
- `plan()` command exists but calls `_pipeline_stub(Stage.PLAN, ...)`
- `approve_plan` is NOT yet imported — must add to import block
- The stub accepts `--fast` and `--skip-research-design` flags; these must be preserved in the real implementation

### State Machine Transitions

From `minilegion/core/state.py`:
- `Stage.DESIGN → Stage.PLAN` is a valid transition
- Approvals needed: `design_approved` must be True (already enforced by StateMachine)

### Gap: Missing Import

`commands.py` imports `approve_brief`, `approve_research`, `approve_design` but NOT `approve_plan`.
Must add `approve_plan` to the import.

### Template Variables

The planner prompt USER_TEMPLATE uses:
- `{{project_name}}` — `project_dir.parent.name`
- `{{brief_content}}` — read from `BRIEF.md`
- `{{research_json}}` — read from `RESEARCH.json`
- `{{design_json}}` — read from `DESIGN.json`

## Implementation Plan

Single plan (08-01-PLAN.md):
1. Add `approve_plan` to the import in `commands.py`
2. Replace `_pipeline_stub(Stage.PLAN, ...)` with full `plan()` implementation
3. Create `tests/test_cli_plan.py` with 10 tests mirroring TestDesignCommand

## Risk Assessment

- Low risk: all infrastructure is already in place
- Only change to commands.py: add import + replace stub body
- Tests follow established pattern from Phase 7
