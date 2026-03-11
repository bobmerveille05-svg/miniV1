---
phase: 15
slug: evidence-pipeline-validate-advance-gates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 15 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_evidence.py tests/test_cli_validate_advance.py tests/test_config.py -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_evidence.py tests/test_cli_validate_advance.py -q`
- **After every plan wave:** Run `python -m pytest tests/test_evidence.py tests/test_cli_validate_advance.py tests/test_config.py tests/test_cli_brief_research.py tests/test_cli_design.py tests/test_cli_plan.py tests/test_cli_execute.py tests/test_cli_review.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | EVD-01, EVD-02, EVD-03 | unit | `python -m pytest tests/test_evidence.py -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | VAD-01, VAD-02 | CLI integration | `python -m pytest tests/test_cli_validate_advance.py::TestValidate tests/test_cli_brief_research.py tests/test_cli_design.py tests/test_cli_plan.py tests/test_cli_execute.py tests/test_cli_review.py -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 2 | VAD-03, VAD-04 | CLI integration | `python -m pytest tests/test_cli_validate_advance.py::TestAdvancePass tests/test_cli_validate_advance.py::TestAdvanceReject -q` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 2 | CFG-07 | unit | `python -m pytest tests/test_config.py::TestWorkflowConfig -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_evidence.py` - evidence model contract, overwrite semantics, and read helper behavior
- [ ] `tests/test_cli_validate_advance.py` - command registration, validate pass/fail, and advance gate behavior
- [ ] `tests/test_config.py` - add `TestWorkflowConfig` for CFG-07 defaults and partial overrides
- [ ] Update `tests/test_cli.py` command registration list to include `validate` and `advance`
- [ ] Update stage command tests that currently assert immediate state advancement after approval

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
