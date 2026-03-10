---
phase: 6
slug: brief-research
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥ 8.0 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` `testpaths = ["tests"]` |
| **Quick run command** | `python -m pytest tests/test_context_scanner.py tests/test_cli_brief_research.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_context_scanner.py tests/test_cli_brief_research.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | RSCH-01..04 | unit stub | `python -m pytest tests/test_context_scanner.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | BRIEF-01..03 | CLI stub | `python -m pytest tests/test_cli_brief_research.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 1 | RSCH-02 | unit | `python -m pytest tests/test_context_scanner.py::TestScannerLimits -x -q` | ❌ W0 | ⬜ pending |
| 6-01-04 | 01 | 1 | RSCH-01 | unit | `python -m pytest tests/test_context_scanner.py::TestTechStackDetection -x -q` | ❌ W0 | ⬜ pending |
| 6-01-05 | 01 | 1 | RSCH-04 | unit | `python -m pytest tests/test_context_scanner.py::TestDirectoryStructure -x -q` | ❌ W0 | ⬜ pending |
| 6-01-06 | 01 | 1 | RSCH-03 | unit | `python -m pytest tests/test_context_scanner.py::TestImportExtraction -x -q` | ❌ W0 | ⬜ pending |
| 6-01-07 | 01 | 1 | RSCH-04 | unit | `python -m pytest tests/test_context_scanner.py::TestNamingConventions -x -q` | ❌ W0 | ⬜ pending |
| 6-01-08 | 01 | 1 | RSCH-01..04 | unit | `python -m pytest tests/test_context_scanner.py::TestScanCodebase -x -q` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | BRIEF-01 | CLI | `python -m pytest tests/test_cli_brief_research.py::TestBriefCommand::test_brief_creates_brief_md_with_text_arg -x -q` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | BRIEF-02 | CLI | `python -m pytest tests/test_cli_brief_research.py::TestBriefCommand::test_brief_stdin_input -x -q` | ❌ W0 | ⬜ pending |
| 6-02-03 | 02 | 1 | BRIEF-03 | CLI | `python -m pytest tests/test_cli_brief_research.py::TestBriefCommand::test_brief_rejection_leaves_state_json_unchanged -x -q` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 1 | RSCH-05 | CLI | `python -m pytest tests/test_cli_brief_research.py::TestResearchCommand::test_research_produces_output -x -q` | ❌ W0 | ⬜ pending |
| 6-03-02 | 03 | 1 | RSCH-05 | CLI | `python -m pytest tests/test_cli_brief_research.py::TestResearchCommand::test_research_calls_preflight -x -q` | ❌ W0 | ⬜ pending |
| 6-03-03 | 03 | 1 | RSCH-05 | CLI | `python -m pytest tests/test_cli_brief_research.py::TestResearchCommand::test_research_approval_accepted_transitions_state -x -q` | ❌ W0 | ⬜ pending |
| 6-03-04 | 03 | 1 | RSCH-06 | unit | `python -m pytest tests/test_schemas.py -x -q` | ✅ existing | ⬜ pending |
| 6-03-05 | 03 | 1 | RSCH-07 | unit | `python -m pytest tests/test_prompt_loader.py -x -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_context_scanner.py` — stubs for RSCH-01, RSCH-02, RSCH-03, RSCH-04
- [ ] `tests/test_cli_brief_research.py` — stubs for BRIEF-01, BRIEF-02, BRIEF-03, RSCH-05

*Existing infrastructure covers all other phase requirements (conftest.py, CliRunner fixtures, monkeypatch patterns all established).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
