---
phase: 14
slug: history-foundation-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 14 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_history.py tests/test_state.py tests/test_context_assembler.py tests/test_cli.py -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_history.py tests/test_state.py -q`
- **After every plan wave:** Run `python -m pytest tests/test_history.py tests/test_state.py tests/test_context_assembler.py tests/test_cli.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | HST-01, HST-03 | unit | `python -m pytest tests/test_history.py::TestAppendEvent tests/test_history.py::TestReadHistory -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | HST-02, HST-05 | unit + integration | `python -m pytest tests/test_state.py tests/test_history.py::TestMigration -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | HST-04 | CLI integration | `python -m pytest tests/test_cli.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_history.py` - new coverage for append/read ordering, schema fields, and migration idempotency
- [ ] `tests/test_cli.py` - add command registration + output assertions for `minilegion history`
- [ ] `tests/test_context_assembler.py` - update/extend to verify history source is `history/` files
- [ ] `tests/test_init.py` - add assertion that new projects create `project-ai/history/` or first append creates it deterministically

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
