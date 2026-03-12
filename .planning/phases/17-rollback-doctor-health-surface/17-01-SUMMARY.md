# Phase 17-01 Summary: Rollback Command

## What Was Built

Implemented the `minilegion rollback "<reason>"` command — a single-step backward stage reset with rejected-artifact preservation and audit trail.

## Artifacts Created / Modified

| File | Change |
|------|--------|
| `tests/test_cli_rollback_doctor.py` | Created — 6 TestRollback tests (+ TestDoctor placeholder) |
| `minilegion/cli/commands.py` | Added `STAGE_ORDER` import, `STAGE_CURRENT_ARTIFACT` dict, `_rejected_filename()` helper, `_move_artifact_to_rejected()` helper, `rollback` command, `timezone` import |

## Key Decisions

- **Artifact moved (not copied)** via `Path.rename()` before state mutation — safe: if rename fails, state unchanged
- **Timestamp format**: `datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")` — UTC compact ISO
- **Rejected filename**: `<STEM>.<TIMESTAMP>.rejected.<EXT>` (e.g. `DESIGN.20260312T051000Z.rejected.json`)
- **Init guard**: `if current_idx == 0` check before any StateMachine construction
- **Approval clearing**: delegated to `StateMachine.transition(to_stage)` — existing behavior trusted
- **Notes as JSON string**: `_json.dumps({"reason": ..., "from_stage": ..., "to_stage": ..., "artifact_moved": ...})`

## Test Coverage

6 TestRollback tests — all pass:
1. `test_rollback_resets_stage` — design→research stage reset
2. `test_rollback_moves_artifact_to_rejected` — artifact rename + timestamp pattern
3. `test_rollback_from_init_exits_nonzero` — init guard, exit 1, no mutation
4. `test_rollback_no_artifact_succeeds` — missing artifact succeeds, artifact_moved=None
5. `test_rollback_clears_downstream_approvals` — plan→design clears design+plan approvals
6. `test_rollback_appends_history_event` — rollback event in history with correct notes JSON

## Verification

```
python -m pytest tests/test_cli_rollback_doctor.py::TestRollback -q
# 6 passed

python -m pytest tests/ -q
# 4 pre-existing failures, 0 regressions
```

## Requirements Satisfied

- **RBK-01**: Rollback command resets current_stage to previous, moves artifact to rejected/
- **RBK-02**: History event appended with event_type="rollback", notes JSON with reason/from_stage/to_stage/artifact_moved
