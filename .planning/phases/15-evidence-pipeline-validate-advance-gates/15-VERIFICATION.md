---
phase: 15-evidence-pipeline-validate-advance-gates
verified: 2026-03-12T18:30:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
gaps: []
---

# Phase 15: Evidence Pipeline + Validate + Advance Gates Verification Report

**Phase Goal:** Separate artifact generation from progression, enforce validation gates with machine-readable evidence, and restore workflow strictness controls.
**Verified:** 2026-03-12T18:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | Running `minilegion validate <step>` always writes `project-ai/evidence/<step>.validation.json` with canonical evidence fields. | ✓ VERIFIED | Evidence.py lines 13-22 define ValidationEvidence with fields: step, status, checks_passed, validator, tool_used, date, notes. validate command (line 499) calls write_evidence to persist. |
| 2   | Re-running validate for the same step overwrites that step's evidence file instead of creating extra files. | ✓ VERIFIED | write_evidence (evidence.py line 29-33) writes to deterministic path `<step>.validation.json`, overwriting on each call. |
| 3   | Validation evidence is machine-readable JSON that downstream commands can parse directly. | ✓ VERIFIED | ValidationEvidence is a Pydantic model (evidence.py line 13) that produces/validates JSON. read_evidence (line 36-41) parses JSON back to typed object. |
| 4   | `validate` reports pass/fail and does not mutate `STATE.json.current_stage`. | ✓ VERIFIED | validate command (commands.py lines 501-510) prints PASS/FAIL and exits 1 on failure. No save_state call changes current_stage. |
| 5   | `minilegion advance` is the only forward stage mutator and succeeds only when current-step evidence is passing. | ✓ VERIFIED | advance command (commands.py lines 535-552) reads evidence, checks status=="pass", only then calls sm.transition (line 564) and saves state (line 572). |
| 6   | `minilegion advance` exits non-zero with clear gate messaging when evidence is missing or failing. | ✓ VERIFIED | advance command lines 537-552 show explicit error messages and typer.Exit(code=1) for missing or failing evidence. |
| 7   | Configs that omit `workflow` still load successfully with `strict_mode=true` and `require_validation=true` defaults. | ✓ VERIFIED | WorkflowConfig (config.py lines 230-234) has defaults True/True. MiniLegionConfig (line 266) includes workflow with Field(default_factory=WorkflowConfig). |
| 8   | Stage-producing commands create their artifacts but do not auto-advance `STATE.json.current_stage`. | ✓ VERIFIED | Commands checked: brief (line 619 save_state only updates approvals), research (no sm.transition), design (no sm.transition), plan normal mode (no sm.transition), execute (no sm.transition), review (lines 1100-1170 have sm.transition for archive only). |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `minilegion/core/evidence.py` | ValidationEvidence schema + read/write helpers | ✓ VERIFIED | 41 lines, exports ValidationEvidence, write_evidence, read_evidence |
| `minilegion/cli/commands.py` | validate + advance commands wired to evidence | ✓ VERIFIED | validate at line 460, advance at line 518, both import and use evidence.py |
| `tests/test_evidence.py` | Contract coverage for evidence fields, overwrite | ✓ VERIFIED | File exists, tests pass (6 tests) |
| `tests/test_cli_validate_advance.py` | CLI coverage for validate/advance pass/fail | ✓ VERIFIED | TestValidate + TestAdvancePass + TestAdvanceReject - all tests pass |
| `tests/test_cli.py` | Command registration coverage | ✓ VERIFIED | test_all_commands_registered checks validate + advance (lines 43-44) |
| `minilegion/core/config.py` | WorkflowConfig with defaults | ✓ VERIFIED | WorkflowConfig class at line 230, strict_mode=True, require_validation=True |
| `tests/test_config.py` | CFG-07 coverage | ✓ VERIFIED | TestWorkflowConfig tests pass |
| `tests/test_cli_brief_research.py` | Regression for preserve-stage | ✓ VERIFIED | 80 tests pass across 5 stage command test files |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| commands.py | evidence.py | validate command uses write_evidence | ✓ WIRED | Line 33 imports, line 499 calls write_evidence |
| commands.py | evidence.py | advance command uses read_evidence | ✓ WIRED | Line 33 imports, line 536 calls read_evidence |
| evidence.py | project-ai/evidence/*.validation.json | Atomic per-step writes | ✓ WIRED | write_evidence uses write_atomic to target path |
| commands.py | STATE.json | validate no-mutation | ✓ WIRED | validate does not call save_state with changed stage |
| commands.py | STATE.json | advance forward transition | ✓ WIRED | advance calls sm.transition and save_state (lines 564-572) |
| config.py | commands.py | workflow strict_mode enforcement | ✓ WIRED | Line 535 checks config.workflow.require_validation |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| EVD-01 | 15-01 | Evidence directory + structured files with required fields | ✓ SATISFIED | evidence.py ValidationEvidence model has all fields; validate writes to <step>.validation.json |
| EVD-02 | 15-01 | Validate overwrites same-step evidence file | ✓ SATISFIED | write_evidence writes deterministically to same path |
| EVD-03 | 15-01 | Machine-readable JSON for downstream parsing | ✓ SATISFIED | Pydantic model produces/reads JSON; advance uses read_evidence |
| VAD-01 | 15-03 | Stage commands don't auto-advance | ✓ SATISFIED | No sm.transition() in normal success paths for brief/research/design/plan/execute/review |
| VAD-02 | 15-01 | validate writes evidence and reports pass/fail without stage change | ✓ SATISFIED | validate command writes evidence, prints PASS/FAIL, no stage mutation |
| VAD-03 | 15-02 | advance checks passing evidence then changes stage + history | ✓ SATISFIED | advance reads evidence, checks status, transitions, appends event |
| VAD-04 | 15-02 | advance refuses with non-zero when evidence missing/failing | ✓ SATISFIED | advance exits 1 with clear messages (lines 537-552) |
| CFG-07 | 15-02 | Config accepts workflow.strict_mode and require_validation with defaults | ✓ SATISFIED | WorkflowConfig has defaults True/True; backward compatible |

**All 8 requirement IDs are accounted for and satisfied.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

No anti-patterns detected. All implementations are substantive and fully wired.

### Human Verification Required

No human verification required. All automated checks pass.

### Gaps Summary

No gaps found. All must-haves verified:
- 8 observable truths verified
- 8 artifacts verified at all 3 levels (exists, substantive, wired)
- 6 key links verified as properly connected
- 8 requirement IDs satisfied
- All tests pass (91 total)

---

_Verified: 2026-03-12T18:30:00Z_
_Verifier: OpenCode (gsd-verifier)_
