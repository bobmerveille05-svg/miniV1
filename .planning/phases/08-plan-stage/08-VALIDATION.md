# Phase 8 Validation

## Requirements to Validate

| Requirement | Description | Validation Method |
|-------------|-------------|-------------------|
| PLAN-01 | plan() command produces PLAN.json + PLAN.md | test_plan_saves_dual_output |
| PLAN-02 | PLAN.json has all required fields | PlanSchema Pydantic validation (existing) |
| PLAN-03 | Each task references a component from DESIGN.json | Enforced by planner.md prompt instruction |
| PLAN-04 | touched_files ⊆ files in DESIGN.json components | Enforced by planner.md prompt instruction |
| PLAN-05 | Planner prompt enforces "decompose, don't design" | planner.md system prompt (Phase 5, verified) |

## Pre-Implementation Checklist

- [x] `check_preflight(Stage.PLAN, ...)` requires BRIEF.md + RESEARCH.json + DESIGN.json (preflight.py:21)
- [x] `check_preflight` requires brief_approved + research_approved + design_approved (preflight.py:37)
- [x] `approve_plan` exists in approval.py (lines 108-115)
- [x] `PlanSchema` validated by schema registry "plan" key
- [x] `render_plan_md()` and `save_dual()` dispatch for PlanSchema exist in renderer.py
- [x] planner.md USER_TEMPLATE variables: project_name, brief_content, research_json, design_json
- [x] StateMachine: DESIGN → PLAN is valid transition

## Plan Coverage

Single plan 08-01-PLAN.md covers all 5 requirements:
- Task A: Add approve_plan import + replace stub (PLAN-01, PLAN-02)
- Task B: Create test_cli_plan.py with 10 tests (PLAN-01, PLAN-03, PLAN-04, PLAN-05 via prompt)

## Risk Assessment

- **Low**: All infrastructure is pre-built; changes confined to commands.py (2 lines: import + stub replacement)
- **Low**: Test pattern is established and proven in Phase 7
