---
phase: 5
slug: prompts-dual-output
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_prompt_loader.py tests/test_renderer.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_prompt_loader.py tests/test_renderer.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | PRMT-01 | unit | `pytest tests/test_prompt_loader.py::TestLoadPrompt -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | PRMT-02 | unit | `pytest tests/test_prompt_loader.py::TestJsonAnchoring -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | PRMT-03 | unit | `pytest tests/test_prompt_loader.py::TestLoadPrompt -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | PRMT-04 | unit | `pytest tests/test_prompt_loader.py::TestRenderPrompt -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | DUAL-01 | unit | `pytest tests/test_renderer.py::TestSaveDual -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | DUAL-02 | unit | `pytest tests/test_renderer.py::TestRenderFunctions -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_prompt_loader.py` — stubs for PRMT-01, PRMT-02, PRMT-03, PRMT-04
- [ ] `tests/test_renderer.py` — stubs for DUAL-01, DUAL-02

*Existing test infrastructure covers framework/runner; only test files for new prompt/renderer code are needed.*

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
