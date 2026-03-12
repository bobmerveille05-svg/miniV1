---
phase: 13
slug: context-evidence-verification-backfill
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 13 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_context_assembler.py tests/test_config.py tests/test_init.py -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_context_assembler.py tests/test_config.py -q`
- **After every plan wave:** Run `python -m pytest tests/test_context_assembler.py tests/test_config.py tests/test_init.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | CTX-01, CFG-08 | unit + CLI integration | `python -m pytest tests/test_context_assembler.py tests/test_config.py -q` | ✅ | ⬜ pending |
| 13-01-02 | 01 | 1 | CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CFG-09 | integration + docs verification | `python -m pytest tests/test_init.py tests/test_context_assembler.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_context_assembler.py` - add lookahead/compact-plan behavior tests tied to `context.lookahead_tasks`
- [ ] `.planning/phases/02-context-adapters/02-VERIFICATION.md` - add requirement-ID evidence table for CTX-01..06 and CFG-08..09
- [ ] README context config docs - add `context.max_injection_tokens`, `context.lookahead_tasks`, `context.warn_threshold` defaults and semantics

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ADR-0007 has complete required sections and wording | CTX-06 | Requirement is document content quality, not runtime behavior | Open `.planning/milestones/v1.1-ADR-0007.md` and confirm required sections: status, context, decision, consequences, rejected alternatives, success criterion |
| Config defaults documented for users | CFG-09 | Requires documentation review beyond code execution | Open README/config docs and verify `context.max_injection_tokens`, `context.lookahead_tasks`, `context.warn_threshold` defaults and meaning |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
