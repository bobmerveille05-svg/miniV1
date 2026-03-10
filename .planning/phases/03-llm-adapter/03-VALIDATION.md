---
phase: 3
slug: llm-adapter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_adapter_base.py tests/test_openai_adapter.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_adapter_base.py tests/test_openai_adapter.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | ADPT-01 | unit | `pytest tests/test_adapter_base.py::TestLLMAdapterABC -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | ADPT-01 | unit | `pytest tests/test_adapter_base.py::TestDataclasses -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | ADPT-02 | unit | `pytest tests/test_openai_adapter.py::TestCallForJson -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | ADPT-02 | unit | `pytest tests/test_openai_adapter.py::TestCall -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | ADPT-03 | unit | `pytest tests/test_openai_adapter.py::TestCallParameters -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | ADPT-03 | unit | `pytest tests/test_openai_adapter.py::TestTokenUsage -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | ADPT-04 | unit | `pytest tests/test_openai_adapter.py::TestAPIKeyValidation -x` | ❌ W0 | ⬜ pending |
| 03-01-08 | 01 | 1 | ADPT-04 | unit | `pytest tests/test_openai_adapter.py::TestAPIKeyFromConfig -x` | ❌ W0 | ⬜ pending |
| 03-01-09 | 01 | 1 | — | unit | `pytest tests/test_openai_adapter.py::TestErrorWrapping -x` | ❌ W0 | ⬜ pending |
| 03-01-10 | 01 | 1 | — | unit | `pytest tests/test_openai_adapter.py::TestLazyInit -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_adapter_base.py` — stubs for ADPT-01 (ABC contract, dataclasses)
- [ ] `tests/test_openai_adapter.py` — stubs for ADPT-02, ADPT-03, ADPT-04 (OpenAI adapter, error wrapping, API key)
- [ ] No new conftest fixtures needed — existing `tmp_project_dir` and `sample_config_json` are reusable; add `make_mock_completion` helper

*Existing test infrastructure covers framework/runner; only test files for new adapter code are needed.*

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
