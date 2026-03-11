---
phase: 1
slug: action-immediate-harden-config-with-small-model-tool-permissions-confirm-default-recommended-models-vs-all-models-model-aliases-context-auto-compact-and-provider-healthcheck-before-research
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_config.py tests/test_config_commands.py tests/test_cli_brief_research.py -q` |
| **Full suite command** | `python -m pytest --tb=short -q` |
| **Estimated runtime** | ~40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_config.py tests/test_config_commands.py tests/test_cli_brief_research.py -q`
- **After every plan wave:** Run `python -m pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CFG-01 | unit | `python -m pytest tests/test_config.py -q` | ✅ | ⬜ pending |
| 01-01-02 | 01 | 1 | CFG-02 | integration | `python -m pytest tests/test_config_commands.py -q` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 2 | SAFE-01 | integration | `python -m pytest tests/test_cli_brief_research.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config.py` — add/expand cases for new config keys (`small_model`, `tool_permissions`, `recommended_models`, `all_models`, `model_aliases`, `context_auto_compact`)
- [ ] `tests/test_config_commands.py` — add coverage for recommended vs all model selection and alias handling
- [ ] `tests/test_cli_brief_research.py` — add provider healthcheck gate coverage before research

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
