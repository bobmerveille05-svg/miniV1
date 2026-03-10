# Phase 9 Validation

## Requirements to Validate

| Requirement | Description | Validation Method |
|-------------|-------------|-------------------|
| BUILD-01 | Builder produces EXECUTION_LOG.json with structured patches | test_execute_saves_execution_log |
| BUILD-02 | EXECUTION_LOG.json has all required per-task fields | ExecutionLogSchema Pydantic validation |
| BUILD-03 | Each patch displayed + approved before application | test_execute_approves_each_patch |
| BUILD-04 | Patcher applies approved patches to filesystem | test_apply_patch_create / test_apply_patch_modify / test_apply_patch_delete |
| BUILD-05 | Dry-run shows changes without modifying files | test_execute_dry_run_no_files_modified |

## Pre-Implementation Checklist

- [x] `check_preflight(Stage.EXECUTE, ...)` requires PLAN.json + all prior approvals (preflight.py)
- [x] `approve_patch` exists in approval.py (lines 118-125)
- [x] `ExecutionLogSchema` registered as "execution_log" in registry
- [x] `render_execution_log_md()` and `save_dual()` dispatch exist in renderer.py
- [x] builder.md USER_TEMPLATE variables: project_name, plan_json, source_files
- [x] `validate_scope()` exists in scope_lock.py
- [x] StateMachine: PLAN → EXECUTE is valid transition

## Plan Coverage

- Plan 09-01: patcher.py module (BUILD-04)
- Plan 09-02: execute() command (BUILD-01, BUILD-02, BUILD-03, BUILD-05)

## Risk Assessment

- **Medium**: Patcher involves filesystem writes — use write_atomic() for create/modify; use Path.unlink() for delete
- **Medium**: Per-patch approval loop is new pattern (not identical to design/plan); needs careful ordering (preview → approve → apply)
- **Low**: dry-run branch is simple (preview only, return early)
- **Low**: scope check is one line using existing validate_scope()
