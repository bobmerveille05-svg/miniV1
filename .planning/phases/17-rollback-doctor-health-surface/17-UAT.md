---
status: complete
phase: 17-rollback-doctor-health-surface
source:
  - 17-01-SUMMARY.md
  - 17-02-SUMMARY.md
started: 2026-03-12T00:00:00Z
updated: 2026-03-12T00:00:00Z
---

## Current Test

number: 1
name: Rollback resets stage
expected: |
  Run: minilegion init mytest && cd mytest
  Then advance to brief stage: minilegion brief "Test project"
  Then run: minilegion rollback "changed my mind"
  You should see a green success message like "Rolled back: brief → init. Reason: changed my mind"
  STATE.json should show current_stage = "init"
awaiting: user response

## Tests

### 1. Rollback resets stage
expected: Run `minilegion init mytest && cd mytest`, then `minilegion brief "Test project"` (so you're at brief stage), then `minilegion rollback "changed my mind"`. You should see a green success message like "Rolled back: brief → init. Reason: changed my mind" and STATE.json (inside mytest/project-ai/) should show current_stage = "init".
result: pass

### 2. Rollback moves artifact to rejected/
expected: After running rollback from brief stage (test 1 above, or a fresh setup at brief), check the mytest/project-ai/rejected/ directory. A file named BRIEF.<TIMESTAMP>.rejected.md should exist (e.g. BRIEF.20260312T051000Z.rejected.md), with the original BRIEF.md content inside it. The original BRIEF.md should be gone.
result: pass

### 3. Rollback from init is blocked
expected: In a fresh project at init stage, run `minilegion rollback "oops"`. You should see a red error message indicating you're already at the first stage and cannot roll back further. Exit code should be 1 (non-zero). STATE.json should be unchanged (current_stage = "init").
result: pass

### 4. Rollback appears in --help
expected: Run `minilegion --help`. Both "rollback" and "doctor" should appear in the command list with brief descriptions. `minilegion rollback --help` should show a "reason" argument. `minilegion doctor --help` should show the command description.
result: pass

### 5. Doctor on a healthy project passes
expected: In a project that has been through init (or fresh init), run `minilegion doctor`. You should see 6 output lines, each starting with [PASS], [WARN], or [FAIL], followed by a check name and description. The final line should be "Doctor: pass" (if all checks pass) or "Doctor: warn" (if only warnings). Exit code 0 for all pass, 1 for warn-only. No crashes.
result: pass

### 6. Doctor detects missing artifact
expected: In a project at design stage with no DESIGN.json file, run `minilegion doctor`. You should see at least one line starting with "[FAIL]" referencing artifact_present or stage_coherence (or both). The final line should be "Doctor: fail". Exit code should be 2.
result: pass

### 7. Doctor output format is consistent
expected: Run `minilegion doctor` in any project. Every output line should follow the exact pattern: `[PASS] check_name: description`, `[WARN] check_name: description`, or `[FAIL] check_name: description`. The very last line should be `Doctor: pass`, `Doctor: warn`, or `Doctor: fail` — nothing else.
result: pass

## Summary

total: 7
passed: 7
issues: 0
skipped: 0
pending: 0

## Gaps

[none yet]
