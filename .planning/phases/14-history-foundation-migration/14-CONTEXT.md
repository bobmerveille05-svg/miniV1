# Phase 14: History Foundation + Migration - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning
**Source:** YOLO auto-generated from codebase analysis + requirements

<domain>
## Phase Boundary

This phase introduces a persistent, append-only history subsystem and removes embedded history from `STATE.json` so project state remains current-only.

In scope:
1. `project-ai/history/` event files with stable sequential naming
2. `core/history.py` APIs for append + read operations
3. Migration path for old `STATE.json` files containing `history`
4. New `minilegion history` command for chronological timeline output

Out of scope:
- Evidence bundles (`project-ai/evidence/`) and validate/advance gates (Phase 15)
- Rollback command and doctor checks (Phase 17)
- Any change to stage-transition semantics

</domain>

<decisions>
## Implementation Decisions

### Decision 1: History event contract
- Introduce canonical event shape in `core/history.py` with fields required by HST-01:
  - `event_type`, `stage`, `timestamp`, `actor`, `tool_used`, `notes`
- Keep event payload minimal and additive so existing callsites can map from current `state.add_history(action, details)` behavior without schema churn.

### Decision 2: Storage and numbering model
- History files stored at `project-ai/history/`.
- Filename format: `NNN_<event_type>.json` (zero-padded to at least 3 digits, monotonic).
- Next index computed from existing filenames to preserve append-only behavior and avoid overwrites.
- Event writes are atomic via existing `write_atomic()` contract.

### Decision 3: Migration strategy for embedded history
- On first access to state (inside `load_state()`), detect raw JSON containing `history`.
- If present:
  1. Convert each embedded entry to history event file(s)
  2. Persist `STATE.json` without the `history` field
  3. Leave migrated events in `project-ai/history/` as source of truth
- Migration must be non-destructive and idempotent (safe if re-run).

### Decision 4: Backward-compatible runtime API
- Keep `ProjectState.add_history()` as a compatibility shim for this phase, but stop persisting a `history` field in serialized state.
- Commands should append events through `core/history.append_event()` as the durable path.
- `context_assembler` should read recent events via `read_history()` instead of `state.history`.

### Decision 5: CLI surface for timeline view
- Add `minilegion history` command to print newest events in chronological order with concise one-line entries.
- If no events exist, print `_No history yet._` (same graceful-degradation tone used elsewhere).

### OpenCode's discretion
- Exact normalization from legacy `{action, details}` to new `{event_type, notes}` fields
- How many rows to display by default in CLI timeline output
- Whether to include optional metadata keys in event files beyond HST minimum

</decisions>

<code_context>
## Existing Code Insights

### Current coupling that Phase 14 must break
- `ProjectState` currently embeds `history: list[HistoryEntry]` in `minilegion/core/state.py`.
- Many command handlers call `state.add_history(...)` before `save_state(...)` in `minilegion/cli/commands.py`.
- `context_assembler` currently renders `state.history[-3:]` in `minilegion/core/context_assembler.py`.

### Reusable assets
- `write_atomic()` in `minilegion/core/file_io.py` for safe event writes.
- Existing stage + approval lifecycle in `StateMachine` remains valid and unchanged.
- Existing CLI error handling (`MiniLegionError`, `typer.Exit`) should be reused for history command UX.

### Integration points
- `minilegion/core/state.py`: migrate `history` persistence out of state model/load-save flow.
- `minilegion/core/history.py`: new append/read APIs and migration helpers.
- `minilegion/cli/commands.py`: route event writes to new history APIs; add `history()` command.
- `minilegion/core/context_assembler.py`: consume history API for recent history rendering.
- Tests likely affected: `tests/test_state.py`, `tests/test_cli.py`, `tests/test_init.py`, `tests/test_context_assembler.py`, plus new history-focused tests.

</code_context>

<specifics>
## Specific Ideas

- Use a deterministic actor/tool default (for example: `actor="system"`, `tool_used="minilegion"`) when legacy callsites lack explicit values.
- Preserve chronological order during migration using embedded entry order from old `STATE.json`.
- Event type sanitization for filenames should be stable (lowercase, spaces to underscores, strip unsafe chars).
- `read_history()` should return typed objects sorted by filename index to avoid filesystem ordering issues.

</specifics>

<deferred>
## Deferred Ideas

- Rich timeline formatting (tables/colors/filter flags) - defer to DX pass after core contract is stable.
- Event compression/rotation for large histories - out of scope for Phase 14.
- Cross-linking history to evidence bundles - belongs to Phase 15.

</deferred>

---

*Phase: 14-history-foundation-migration*
*Context gathered: 2026-03-11 (YOLO auto-generated)*
