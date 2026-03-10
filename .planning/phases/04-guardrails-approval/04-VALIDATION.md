---
phase: 4
slug: guardrails-approval
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_preflight.py tests/test_scope_lock.py tests/test_approval.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_preflight.py tests/test_scope_lock.py tests/test_approval.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | GUARD-01 | unit | `pytest tests/test_preflight.py::TestPreflightFiles -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | GUARD-02 | unit | `pytest tests/test_preflight.py::TestPreflightApprovals -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | GUARD-03 | unit | `pytest tests/test_preflight.py::TestSafeModeGuards -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | GUARD-04 | unit | `pytest tests/test_scope_lock.py::TestCheckScope -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | GUARD-05 | unit | `pytest tests/test_scope_lock.py::TestNormalizePath -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | APRV-01 | unit | `pytest tests/test_approval.py::TestApproveBrief -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | APRV-02 | unit | `pytest tests/test_approval.py::TestApproveResearch -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | APRV-03 | unit | `pytest tests/test_approval.py::TestApproveDesign -x` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 1 | APRV-04 | unit | `pytest tests/test_approval.py::TestApprovePlan -x` | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 1 | APRV-05 | unit | `pytest tests/test_approval.py::TestApprovePatch -x` | ❌ W0 | ⬜ pending |
| 04-02-06 | 02 | 1 | APRV-06 | unit | `pytest tests/test_approval.py::TestRejectionByteIdentical -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_preflight.py` — stubs for GUARD-01, GUARD-02, GUARD-03
- [ ] `tests/test_scope_lock.py` — stubs for GUARD-04, GUARD-05
- [ ] `tests/test_approval.py` — stubs for APRV-01 through APRV-06

*Existing test infrastructure covers framework/runner; only test files for new guardrails/approval code are needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
