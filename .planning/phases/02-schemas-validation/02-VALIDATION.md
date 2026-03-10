---
phase: 2
slug: schemas-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | SCHM-01 | unit | `python -m pytest tests/test_schemas.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SCHM-01 | unit | `python -m pytest tests/test_schemas.py -x -k "test_invalid"` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | SCHM-02 | unit | `python -m pytest tests/test_json_schemas.py -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | SCHM-03 | unit | `python -m pytest tests/test_registry.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | SCHM-03 | unit | `python -m pytest tests/test_fixups.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | SCHM-04 | unit | `python -m pytest tests/test_retry.py -x -k "test_retry"` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | SCHM-05 | unit | `python -m pytest tests/test_retry.py -x -k "test_raw_debug"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schemas.py` — stubs for SCHM-01: model creation, validation, rejection for all 6 types
- [ ] `tests/test_json_schemas.py` — stubs for SCHM-02: JSON Schema file validity and model match
- [ ] `tests/test_registry.py` — stubs for SCHM-03: registry functions (get_schema, get_json_schema, validate)
- [ ] `tests/test_fixups.py` — stubs for SCHM-03: pre-parse fixup functions
- [ ] `tests/test_retry.py` — stubs for SCHM-04, SCHM-05: retry logic and RAW_DEBUG saving

*Existing infrastructure covers conftest.py (Phase 1).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

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
