---
phase: 17
slug: rollback-doctor-health-surface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥ 8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `python -m pytest tests/test_cli_rollback_doctor.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_cli_rollback_doctor.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | RBK-01, RBK-02 | unit RED | `python -m pytest tests/test_cli_rollback_doctor.py::TestRollback -x -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | RBK-01, RBK-02 | unit GREEN | `python -m pytest tests/test_cli_rollback_doctor.py::TestRollback -x -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | DOC-01, DOC-02, DOC-03 | unit RED | `python -m pytest tests/test_cli_rollback_doctor.py::TestDoctor -x -q` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | DOC-01, DOC-02, DOC-03 | unit GREEN | `python -m pytest tests/test_cli_rollback_doctor.py::TestDoctor -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_rollback_doctor.py` — full test file with all 15 RED test cases (6 rollback + 9 doctor); must all FAIL before implementation

*Existing test infrastructure (pytest, CliRunner, conftest) covers all other phase requirements — only the new test file is needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
