---
phase: 1
slug: foundation-cli
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | none — Wave 0 creates `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-task Verification Map

| Req ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|--------|------|------|-------------|-----------|-------------------|-------------|--------|
| FOUND-01 | 01 | 1 | init creates project-ai/ with template files | integration | `pytest tests/test_init.py -x` | ❌ W0 | ⬜ pending |
| FOUND-02 | 01 | 1 | Config loads from JSON with defaults | unit | `pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| FOUND-03 | 01 | 1 | State machine enforces valid transitions | unit | `pytest tests/test_state.py -x` | ❌ W0 | ⬜ pending |
| FOUND-04 | 01 | 1 | STATE.json written atomically after approval | unit | `pytest tests/test_state.py::test_atomic_write -x` | ❌ W0 | ⬜ pending |
| FOUND-05 | 01 | 1 | All file writes use atomic pattern | unit | `pytest tests/test_file_io.py -x` | ❌ W0 | ⬜ pending |
| FOUND-06 | 01 | 1 | Exception hierarchy exists | unit | `pytest tests/test_exceptions.py -x` | ❌ W0 | ⬜ pending |
| CLI-01 | 01 | 1 | 8 commands registered and routable | integration | `pytest tests/test_cli.py -x` | ❌ W0 | ⬜ pending |
| CLI-02 | 01 | 1 | plan accepts --fast and --skip-research-design | integration | `pytest tests/test_cli.py::test_plan_flags -x` | ❌ W0 | ⬜ pending |
| CLI-03 | 01 | 1 | execute accepts --task N and --dry-run | integration | `pytest tests/test_cli.py::test_execute_flags -x` | ❌ W0 | ⬜ pending |
| CLI-04 | 01 | 1 | No args shows help | integration | `pytest tests/test_cli.py::test_no_args_help -x` | ❌ W0 | ⬜ pending |
| CLI-05 | 01 | 1 | status reads and displays STATE.json | integration | `pytest tests/test_cli.py::test_status -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — test package init
- [ ] `tests/conftest.py` — shared fixtures (tmp_path for project dirs, sample configs)
- [ ] `tests/test_state.py` — state machine unit tests
- [ ] `tests/test_config.py` — config loading unit tests
- [ ] `tests/test_file_io.py` — atomic write unit tests
- [ ] `tests/test_exceptions.py` — exception hierarchy tests
- [ ] `tests/test_cli.py` — CLI integration tests using CliRunner
- [ ] `tests/test_init.py` — init command integration tests
- [ ] Framework install: `pip install pytest` — add to dev dependencies in pyproject.toml

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Colored output display | CLI behavior | Terminal rendering not capturable in CI | Run `python run.py status` and verify colored output visually |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
