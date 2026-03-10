---
phase: 06-brief-research
plan: "02"
subsystem: cli-commands
tags: [brief, tdd, approval-gate, state-machine, stdin, atomic-write]
dependency_graph:
  requires: [minilegion/core/approval.py, minilegion/core/file_io.py, minilegion/core/state.py]
  provides: [brief() command body with full stdin+approval+state flow]
  affects: [minilegion/cli/commands.py, tests/test_cli_brief_research.py]
tech_stack:
  added: []
  patterns: [write-before-gate, sync-gap-fix, ApprovalError-before-MiniLegionError]
key_files:
  created: [tests/test_cli_brief_research.py]
  modified: [minilegion/cli/commands.py]
decisions:
  - "ApprovalError caught before MiniLegionError (subclass ordering — order matters)"
  - "state.current_stage = Stage.BRIEF.value set explicitly before save_state() to avoid sync gap"
  - "BRIEF.md written atomically before approve_brief() (write-before-gate principle)"
  - "Rejection exits 0 (not an error); wrong-stage exits 1 (error)"
metrics:
  duration: "~20min"
  completed: "2026-03-10"
  tasks_completed: 3
  files_changed: 2
requirements: [BRIEF-01, BRIEF-02, BRIEF-03]
---

# Phase 06 Plan 02: Implement brief() Command with Stdin Support and Approval Gate — Summary

**One-liner:** Full `brief()` CLI command with stdin fallback, atomic `BRIEF.md` write before approval gate, `ApprovalError` exit-0 rejection, and explicit `state.current_stage` sync before `save_state()`.

## What Was Built

Replaced the `_pipeline_stub(Stage.BRIEF)` call in `minilegion/cli/commands.py` with a complete implementation:

1. **Text input** — reads `text` argument or falls back to `typer.get_text_stream("stdin").read().strip()`
2. **Atomic write first** — `write_atomic(project_dir / "BRIEF.md", brief_content)` called *before* the approval gate
3. **Approval gate** — `approve_brief(state, state_path, brief_content)` raises `ApprovalError` on rejection
4. **State sync** — `state.current_stage = Stage.BRIEF.value` set explicitly before `save_state()` (avoids sync gap pitfall)
5. **Exception ordering** — `except ApprovalError` before `except MiniLegionError` (subclass ordering)
6. **10 tests** in `TestBriefCommand` covering all success/failure/edge-case paths

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing TestBriefCommand stubs (TDD RED) | aba6056 | tests/test_cli_brief_research.py |
| 2 | Implement brief() command + fill in all 10 tests | 73962a6 | minilegion/cli/commands.py, tests/test_cli_brief_research.py |
| 3 | Full suite integrity check | — | (verification only) |

## Test Results

- **10 new `TestBriefCommand` tests: ALL PASS** ✓
- **389 total tests pass** (379 pre-existing + 10 new)
- **31 pre-existing stubs in `test_context_scanner.py`** remain RED (out of scope — Plan 06-01 TDD stubs awaiting Plan 06-01 implementation)
- **0 regressions** introduced

## Key Behaviors Verified

| Behavior | Test |
|----------|------|
| `brief "text"` creates BRIEF.md | `test_brief_creates_brief_md_with_text_arg` |
| BRIEF.md contains `## Overview` + text | `test_brief_content_contains_overview_heading` |
| BRIEF.md written BEFORE approval gate | `test_brief_writes_atomically_before_approval` |
| stdin fallback works | `test_brief_stdin_input` |
| Empty stdin creates empty Overview | `test_brief_stdin_empty_creates_empty_overview` |
| Approval transitions STATE.json to "brief" | `test_brief_approval_accepted_transitions_state` |
| Rejection leaves STATE.json unchanged | `test_brief_rejection_leaves_state_json_unchanged` |
| Rejection exits 0 | `test_brief_rejection_exits_0` |
| Missing project-ai exits 1 | `test_brief_without_project_dir_exits_1` |
| Wrong stage exits 1 | `test_brief_from_wrong_stage_exits_1` |

## Decisions Made

1. **`ApprovalError` caught before `MiniLegionError`** — `ApprovalError` is a subclass; if `MiniLegionError` was first it would intercept rejections and exit 1 instead of 0.

2. **`state.current_stage = Stage.BRIEF.value` set explicitly** — `sm.transition()` updates `sm.current_stage` but NOT `state.current_stage` (the Pydantic model field). Must set manually before `save_state()` or STATE.json writes `"init"`.

3. **`write_atomic` called before `approve_brief()`** — The write-before-gate pattern: artifact exists on disk whether approved or rejected. Test `test_brief_writes_atomically_before_approval` verifies BRIEF.md exists even after rejection.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
