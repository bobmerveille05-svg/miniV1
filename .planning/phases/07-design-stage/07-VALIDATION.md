---
phase: 7
slug: design-stage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `python -m pytest tests/test_cli_design.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_cli_design.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green (431 + 10 = 441 tests)
- **Max feedback latency:** ~5 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 1 | DSGN-01 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_calls_preflight -v` | ❌ W0 | ⬜ pending |
| 7-01-01 | 01 | 1 | DSGN-01 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_calls_llm -v` | ❌ W0 | ⬜ pending |
| 7-01-01 | 01 | 1 | DSGN-01 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_saves_dual_output -v` | ❌ W0 | ⬜ pending |
| 7-01-01 | 01 | 1 | DSGN-01 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_preflight_failure_exits_1 -v` | ❌ W0 | ⬜ pending |
| 7-01-01 | 01 | 1 | DSGN-01 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_llm_error_exits_1 -v` | ❌ W0 | ⬜ pending |
| 7-01-01 | 01 | 1 | DSGN-01 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_writes_atomically_before_approval -v` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | DSGN-02 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_approval_accepted_transitions_state -v` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | DSGN-02 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_state_current_stage_is_design_after_approval -v` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | APRV-03 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_rejection_exits_0 -v` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | APRV-06 | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_rejection_leaves_state_unchanged -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_design.py` — 10 tests covering DSGN-01..05 + APRV-03/06

*All other infrastructure exists. No framework install needed — pytest already configured in pyproject.toml.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
