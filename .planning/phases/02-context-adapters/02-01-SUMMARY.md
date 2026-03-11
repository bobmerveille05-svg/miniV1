---
phase: 02-context-adapters
plan: "01"
subsystem: context-assembly
tags: [context, assembler, config, cli, tdd]
dependency_graph:
  requires: [minilegion/core/state.py, minilegion/core/file_io.py, minilegion/core/config.py, minilegion/cli/commands.py]
  provides: [minilegion/core/context_assembler.py, minilegion context CLI command, ContextConfig sub-model]
  affects: [minilegion/cli/commands.py, minilegion/core/config.py]
tech_stack:
  added: []
  patterns: [TDD red-green, optional-file graceful degradation, atomic write, Pydantic sub-model with default_factory]
key_files:
  created:
    - minilegion/core/context_assembler.py
    - tests/test_context_assembler.py
  modified:
    - minilegion/core/config.py
    - minilegion/cli/commands.py
    - tests/test_config.py
decisions:
  - "ContextConfig uses default_factory=ContextConfig so omitting 'context' from JSON is backward compatible (CFG-09)"
  - "assemble_context is a pure function — no file I/O; CLI command owns all writes"
  - "Graceful degradation: missing adapters/templates/memory files produce stub text, never raise"
  - "Warn to stderr (not raise) when assembled context exceeds warn_threshold × max_injection_tokens"
  - "Artifact truncation appends [TRUNCATED] marker so consumers know content was cut"
metrics:
  duration: "~15 min"
  completed: "2026-03-11"
  tasks_completed: 2
  tests_added: 36
  files_created: 2
  files_modified: 3
  baseline_tests: 620
  final_tests: 656
requirements: [CTX-01, CTX-02, CFG-08, CFG-09]
---

# Phase 2 Plan 01: Context Assembler Summary

**One-liner:** `minilegion context <tool>` assembles a tool-specific portable context block from STATE.json, adapters, memory, templates, and artifacts — writes `project-ai/context/<tool>.md` and prints to stdout.

## What Was Built

### `minilegion/core/context_assembler.py` (new)
Pure function `assemble_context(tool, project_dir, config) -> str` that:
- Reads `STATE.json` via `load_state()` — includes current stage, completed task count, last 3 history entries
- Optionally reads `adapters/<tool>.md` → `adapters/_base.md` → uses default framing stub
- Optionally reads `memory/decisions.md`, `glossary.md`, `constraints.md` — concatenates with `---` separator
- Optionally reads `templates/<current_stage>.md` — stub text if absent
- Optionally reads stage artifact (`BRIEF.md`, `RESEARCH.md`, etc.) — truncates at `max_injection_tokens` with `[TRUNCATED]` marker
- Warns to stderr if total assembled output exceeds `warn_threshold × max_injection_tokens`
- Returns markdown string with 5 sections: `## Current State`, `## Previous Artifact`, `## Stage Template`, `## Memory`, `## Adapter Instructions`

### `minilegion/core/config.py` (modified)
Added `ContextConfig` Pydantic sub-model:
```python
class ContextConfig(BaseModel):
    max_injection_tokens: int = 3000
    lookahead_tasks: int = 2
    warn_threshold: float = 0.7
```
Added `context: ContextConfig = Field(default_factory=ContextConfig)` to `MiniLegionConfig`. Fully backward-compatible — existing configs that omit `"context"` get defaults via `default_factory`.

### `minilegion/cli/commands.py` (modified)
Added `context` Typer command:
- Finds project dir, loads config
- Calls `assemble_context(tool, project_dir, config)`
- Writes `project-ai/context/<tool>.md` atomically via `write_atomic()`
- Prints assembled block to stdout via `typer.echo()`
- Handles `MiniLegionError` with red error + exit 1 (consistent with all other commands)

### `tests/test_context_assembler.py` (new, 30 tests)
Full TDD test suite covering:
- `TestAssembleContextBasic` — returns non-empty string, sections present, stage in output, tool name in output, unknown tool degrades
- `TestAssembleContextState` — completed task count, history entries, non-default stage
- `TestAssembleContextGracefulDegradation` — works with no adapters/, memory/, templates/, artifacts
- `TestAssembleContextOptionalFiles` — includes adapter file, falls back to _base.md, reads memory, reads template, reads artifact
- `TestAssembleContextConfig` — truncation at max_injection_tokens, [TRUNCATED] marker present
- `TestContextCLICommand` — writes file, file content matches stdout, claude/chatgpt/copilot/opencode all work, no-project exits 1, command registered in help

### `tests/test_config.py` (modified, +6 tests)
Added `TestContextConfig` class:
- ContextConfig defaults, MiniLegionConfig.context field type check
- Partial context override in JSON, absent context key gives defaults
- Regression test for existing MiniLegionConfig defaults

## Test Results

| Metric | Value |
|---|---|
| Baseline tests | 620 |
| New tests added | 36 (30 assembler + 6 config) |
| Final test count | 656 |
| Regressions | 0 |
| Test duration | ~21s |

## Commits

| Hash | Description |
|---|---|
| `ca9f4e7` | test(02-01): add failing tests for ContextConfig sub-model (TDD RED) |
| `f76dc1a` | feat(02-01): add ContextConfig sub-model to MiniLegionConfig (GREEN) |
| `1496a76` | test(02-01): add failing tests for context assembler (TDD RED) |
| `f4eaa34` | feat(02-01): implement context assembler and minilegion context CLI command (GREEN) |

## Deviations from Plan

None — plan executed exactly as written.

The test file structure was expanded beyond the minimum behavior tests listed in the plan to include CLI integration tests (`TestContextCLICommand`) and additional graceful degradation coverage. All additions are additive and don't change the scope.

## Self-Check

## Self-Check: PASSED

| Check | Result |
|---|---|
| `minilegion/core/context_assembler.py` | FOUND |
| `tests/test_context_assembler.py` | FOUND |
| `.planning/phases/02-context-adapters/02-01-SUMMARY.md` | FOUND |
| commit `ca9f4e7` | FOUND |
| commit `f76dc1a` | FOUND |
| commit `1496a76` | FOUND |
| commit `f4eaa34` | FOUND |
| 656 tests passing | VERIFIED |
