---
phase: 1
slug: action-immediate-harden-config-with-small-model-tool-permissions-confirm-default-recommended-models-vs-all-models-model-aliases-context-auto-compact-and-provider-healthcheck-before-research
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-11
---

# Phase 1 - Validation Strategy

> Per-phase validation contract for execution feedback sampling.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_config.py tests/test_config_commands.py tests/test_provider_health.py tests/test_cli_brief_research.py -q` |
| **Full suite command** | `python -m pytest --tb=short -q` |
| **Estimated runtime** | Task-level checks under 30 seconds; full suite under 60 seconds |

---

## Sampling Rate

- **After task 01-01-01:** Run `python -m pytest tests/test_config.py -q`
- **After task 01-01-02:** Run `python -m pytest tests/test_config_commands.py -q`
- **After task 01-01-03:** Run `python -m pytest tests/test_config.py tests/test_config_commands.py -q`
- **After task 01-02-01:** Run `python -m pytest tests/test_provider_health.py -q`
- **After task 01-02-02:** Run `python -m pytest tests/test_cli_brief_research.py -k "healthcheck or compact or scan_max_file_size" -q`
- **After each wave:** Run the phase quick run command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** under 30 seconds for task-level commands

---

## Per-task Verification Map

| Task ID | Plan | Wave | Requirement IDs | Planned work | Test type | Automated command | File exists | Status |
|---------|------|------|-----------------|--------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | `CFG-01`, `CFG-02` | Extend config schema with `small_model`, `tool_permissions`, and backward-compatible defaults/validation | unit | `python -m pytest tests/test_config.py -q` | `tests/test_config.py` | ⬜ pending |
| 01-01-02 | 01 | 1 | `CFG-03`, `CFG-04` | Add recommended-vs-all catalog helpers and canonical alias resolution in CLI flows | CLI/integration | `python -m pytest tests/test_config_commands.py -q` | `tests/test_config_commands.py` | ⬜ pending |
| 01-01-03 | 01 | 1 | `CFG-01`, `CFG-02`, `CFG-03`, `CFG-04` | Update README contract to match shipped config and CLI behavior | regression | `python -m pytest tests/test_config.py tests/test_config_commands.py -q` | `README.md` | ⬜ pending |
| 01-02-01 | 02 | 2 | `CFG-06` | Create reusable provider healthcheck helper with deterministic pass/fail coverage | unit | `python -m pytest tests/test_provider_health.py -q` | `tests/test_provider_health.py` | ⬜ pending |
| 01-02-02 | 02 | 2 | `CFG-05`, `CFG-06` | Wire healthcheck ordering, deterministic context compaction, and file-size contract regression coverage | integration | `python -m pytest tests/test_cli_brief_research.py -k "healthcheck or compact or scan_max_file_size" -q` | `tests/test_cli_brief_research.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- None. Every planned task already has a concrete `<automated>` verification target and each referenced test file is present in the plan set, so `wave_0_complete: true` is accurate.

---

## Requirement Coverage Map

| Requirement ID | Covered by tasks | Automated proof |
|----------------|------------------|-----------------|
| `CFG-01` | `01-01-01`, `01-01-03` | `python -m pytest tests/test_config.py -q` |
| `CFG-02` | `01-01-01`, `01-01-03` | `python -m pytest tests/test_config.py -q` |
| `CFG-03` | `01-01-02`, `01-01-03` | `python -m pytest tests/test_config_commands.py -q` |
| `CFG-04` | `01-01-02`, `01-01-03` | `python -m pytest tests/test_config_commands.py -q` |
| `CFG-05` | `01-02-02` | `python -m pytest tests/test_cli_brief_research.py -k "compact or scan_max_file_size" -q` |
| `CFG-06` | `01-02-01`, `01-02-02` | `python -m pytest tests/test_provider_health.py tests/test_cli_brief_research.py -k "healthcheck" -q` |

---

## Manual-Only Verifications

All planned phase behaviors have automated verification; no manual-only checkpoint is required for this revision.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] `tests/test_provider_health.py` included in the validation contract
- [x] No watch-mode flags
- [x] Task-level feedback latency stays below the Nyquist warning threshold
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
