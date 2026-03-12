# Phase 17-02 Summary: Doctor Command

## What Was Built

Implemented the `minilegion doctor` command — a 6-check project health surface with per-check colored output (`[PASS]`/`[WARN]`/`[FAIL]`) and pass/warn/fail verdict summary.

## Artifacts Created / Modified

| File | Change |
|------|--------|
| `tests/test_cli_rollback_doctor.py` | Added 9 TestDoctor tests (replaced placeholder `pass`) |
| `minilegion/cli/commands.py` | Added 6 `_check_*` helper functions + `doctor` command |

## Key Decisions

- **6 checks** in order: `state_valid`, `artifact_present`, `history_readable`, `stage_coherence`, `adapter_base`, `adapter_active`
- **Exit codes**: 0=all PASS, 1=any WARN (no FAIL), 2=any FAIL — computed inside `try` block, NOT in `except MiniLegionError`
- **`raise typer.Exit(code=exit_code)` inside `try`** — critical structural constraint: `typer.Exit` is not a `MiniLegionError`, so it propagates cleanly past the except block
- **Check helpers return tuples** `("PASS"|"WARN"|"FAIL", message)` — never raise; doctor survives any individual check failure
- **Graceful degradation**: `_check_artifact_present` and `_check_stage_coherence` skip if state is invalid (return PASS with "skipped" note)
- **Colors**: GREEN=PASS, YELLOW=WARN, RED=FAIL via `typer.style()`

## Severity Mapping

| Check | Severity |
|-------|---------|
| `state_valid` | FAIL — STATE.json missing or unparseable |
| `artifact_present` | FAIL — current-stage artifact missing or whitespace-only |
| `history_readable` | WARN — history/ missing or any .json fails parse |
| `stage_coherence` | FAIL — stage has expected artifact but it doesn't exist |
| `adapter_base` | WARN — adapters/_base.md absent |
| `adapter_active` | WARN — no tool .md files in adapters/ besides _base.md |

## Test Coverage

9 TestDoctor tests — all pass:
1. `test_doctor_healthy_project_exits_zero` — exit 0, "Doctor: pass", ≥4 [PASS] lines
2. `test_doctor_invalid_state_fails` — invalid STATE.json → exit 2, "Doctor: fail"
3. `test_doctor_missing_artifact_fails` — stage=design, no DESIGN.json → exit 2
4. `test_doctor_corrupt_history_warns` — corrupt history event → exit ≥1
5. `test_doctor_stage_artifact_mismatch_fails` — stage_coherence FAIL → "stage_coherence" in output
6. `test_doctor_missing_adapter_base_warns` — no _base.md → exit 1, "adapter_base" [WARN]
7. `test_doctor_warn_only_exits_one` — missing history (WARN only) → exit 1, "Doctor: warn"
8. `test_doctor_output_format` — every line matches `[PASS/WARN/FAIL] ` or `Doctor:` prefix
9. `test_doctor_summary_line` — output ends with "Doctor: fail" on FAIL condition

## Verification

```
python -m pytest tests/test_cli_rollback_doctor.py -q
# 15 passed (6 rollback + 9 doctor)

python -m pytest tests/ -q
# 4 pre-existing failures, 0 regressions

minilegion doctor --help
# Shows command with description
```

## Requirements Satisfied

- **DOC-01**: 6 checks implemented covering state, artifact, history, coherence, adapters
- **DOC-02**: 6 incoherence classes detected (exceeds 4-class minimum)
- **DOC-03**: [PASS]/[WARN]/[FAIL] colored lines + "Doctor: pass/warn/fail" summary + exit 0/1/2
