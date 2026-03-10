---
phase: 06-brief-research
plan: "03"
subsystem: cli-commands
tags: [research, tdd, approval-gate, state-machine, llm-pipeline, context-scanner, validate-with-retry]
dependency_graph:
  requires: [minilegion/core/context_scanner.py, minilegion/core/preflight.py, minilegion/adapters/openai_adapter.py, minilegion/core/retry.py, minilegion/core/renderer.py, minilegion/core/approval.py]
  provides: [research() command body replacing _pipeline_stub call, TestResearchCommand (11 tests)]
  affects: [minilegion/cli/commands.py, tests/test_cli_brief_research.py]
tech_stack:
  added: []
  patterns: [preflight-before-io, scan-before-llm, sync-gap-fix, ApprovalError-before-MiniLegionError, write-before-gate, 5-arg-validate-with-retry]
key_files:
  created: []
  modified: [minilegion/cli/commands.py, tests/test_cli_brief_research.py]
decisions:
  - "load_config(project_dir.parent) — NOT project_dir itself; load_config appends project-ai/ internally"
  - "OpenAIAdapter(config) takes single full MiniLegionConfig, not individual kwargs"
  - "validate_with_retry(llm_call, user_message, 'research', config, project_dir) — 5 positional args, config is 4th"
  - "ApprovalError caught before MiniLegionError (subclass ordering — rejection exits 0)"
  - "state.current_stage = Stage.RESEARCH.value set explicitly before save_state() (sync gap fix)"
  - "check_preflight called AFTER can_transition guard and AFTER load_config but BEFORE any LLM I/O"
metrics:
  duration: "~15min"
  completed: "2026-03-10"
  tasks_completed: 3
  files_changed: 2
requirements: [RSCH-05, RSCH-06, RSCH-07]
---

# Phase 06 Plan 03: Implement research() Command with LLM Pipeline and Approval Gate — Summary

**One-liner:** Full `research()` CLI command orchestrating preflight → codebase scan → researcher prompt render → OpenAI LLM call → validate+retry → save_dual (RESEARCH.json + RESEARCH.md) → approval gate → state transition, with 11 TDD tests covering all success/failure/edge-case paths.

## What Was Built

Replaced the `_pipeline_stub(sm, state, Stage.RESEARCH)` call in `minilegion/cli/commands.py` with a complete orchestration pipeline:

1. **Can-transition guard** — `sm.can_transition(Stage.RESEARCH)` checked first; exits 1 with red message if blocked
2. **Config load** — `load_config(project_dir.parent)` — critical: pass CWD not project-ai itself
3. **Preflight validation** — `check_preflight(Stage.RESEARCH, project_dir)` raises `PreflightError` if BRIEF.md missing or `brief_approved` not set
4. **Codebase scan** — `scan_codebase(project_dir, config)` builds context string for LLM prompt
5. **Prompt render** — `load_prompt("researcher")` + `render_prompt(user_template, project_name=..., brief_content=..., codebase_context=...)` 
6. **LLM call** — `OpenAIAdapter(config)` with single full config; `adapter.call_for_json(system_prompt, prompt)` wrapped in `llm_call()`
7. **Validate + retry** — `validate_with_retry(llm_call, user_message, "research", config, project_dir)` — 5-arg signature; config is 4th, NOT `config.max_retries`
8. **Dual save** — `save_dual(research_data, project_dir/"RESEARCH.json", project_dir/"RESEARCH.md")`
9. **Approval gate** — `approve_research(state, state_path, research_md)` raises `ApprovalError` on rejection
10. **State sync** — `state.current_stage = Stage.RESEARCH.value` set explicitly before `save_state()` (avoids sync gap)
11. **11 tests** in `TestResearchCommand` added to `tests/test_cli_brief_research.py`, with `_write_brief_state` helper

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add TestResearchCommand stubs (TDD RED) | 33a7c56 | tests/test_cli_brief_research.py |
| 2 | Implement research() command + fill in all 11 tests | 653abff | minilegion/cli/commands.py, tests/test_cli_brief_research.py |
| 3 | Full suite integrity check | — | (verification only) |

## Test Results

- **11 new `TestResearchCommand` tests: ALL PASS** ✓
- **431 total tests pass** (420 pre-existing + 11 new)
- **0 regressions** introduced
- **TestBriefCommand**: 10/10 GREEN ✓
- **TestResearchCommand**: 11/11 GREEN ✓

## Key Behaviors Verified

| Behavior | Test |
|----------|------|
| `check_preflight` called with `Stage.RESEARCH` | `test_research_calls_preflight` |
| `PreflightError` → exit 1, red message | `test_research_preflight_failure_exits_1` |
| `scan_codebase(project_dir, config)` called | `test_research_runs_scanner` |
| `validate_with_retry` called with 5-arg signature | `test_research_calls_llm` |
| RESEARCH.json + RESEARCH.md created | `test_research_saves_dual_output` |
| Approval transitions STATE.json to "research" | `test_research_approval_accepted_transitions_state` |
| Rejection leaves STATE.json at "brief" | `test_research_rejection_leaves_state_unchanged` |
| Rejection exits 0 | `test_research_rejection_exits_0` |
| LLM error exits 1 | `test_research_llm_error_exits_1` |
| Missing BRIEF.md (real preflight) exits 1 | `test_research_missing_brief_md_exits_1` |
| STATE.json current_stage == "research" after approval (sync gap fix) | `test_research_state_current_stage_is_research_after_approval` |

## Critical Signature Pitfalls Avoided

1. **`OpenAIAdapter(config)`** — single full `MiniLegionConfig` object. NOT `OpenAIAdapter(model=..., api_key_env=...)` (TypeError).
2. **`validate_with_retry(llm_call, user_message, "research", config, project_dir)`** — 5 positional args; `config` is 4th (NOT `config.max_retries` int).
3. **`load_config(project_dir.parent)`** — NOT `load_config(project_dir)`; `load_config()` appends `project-ai/` internally — passing `project_dir` itself creates double-nesting.

## Decisions Made

1. **`ApprovalError` caught before `MiniLegionError`** — `ApprovalError` is a subclass; catching `MiniLegionError` first would intercept rejections, exiting 1 instead of 0.

2. **`state.current_stage = Stage.RESEARCH.value` set explicitly** — `sm.transition()` updates `sm.current_stage` but NOT `state.current_stage` (the Pydantic field). Must set manually before `save_state()` or STATE.json writes `"brief"`.

3. **`load_config(project_dir.parent)`** — `find_project_dir()` returns `.../myproject/project-ai/`. `load_config()` internally appends `project-ai/minilegion.config.json`. Passing `project_dir` directly would look for `project-ai/project-ai/minilegion.config.json`.

4. **check_preflight after load_config** — Config is needed downstream; preflight after config-load means we fail fast with a clear preflight error before any expensive I/O if preconditions aren't met.

## Deviations from Plan

None — plan executed exactly as written. Both `commands.py` and `tests/test_cli_brief_research.py` were already fully implemented and passing when execution started (prior work from TDD RED stub commit `33a7c56`). Verified all 431 tests GREEN and made the required feat commit.

## Self-Check: PASSED

- `minilegion/cli/commands.py` — exists, contains `scan_codebase`, `OpenAIAdapter(config)`, `validate_with_retry` ✓
- `tests/test_cli_brief_research.py` — exists, contains `TestResearchCommand` with 11 tests ✓
- Commit `653abff` exists: `feat(06-03): implement research command with LLM pipeline and approval gate` ✓
- All 431 tests GREEN ✓
