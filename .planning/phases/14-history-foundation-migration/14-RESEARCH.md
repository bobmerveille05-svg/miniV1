# Phase 14: History Foundation + Migration - Research

**Researched:** 2026-03-11
**Domain:** Append-only history subsystem, legacy STATE history migration, and CLI timeline output
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### OpenCode's Discretion
- Exact normalization from legacy `{action, details}` to new `{event_type, notes}` fields
- How many rows to display by default in CLI timeline output
- Whether to include optional metadata keys in event files beyond HST minimum

### Deferred Ideas (OUT OF SCOPE)
- Rich timeline formatting (tables/colors/filter flags) - defer to DX pass after core contract is stable.
- Event compression/rotation for large histories - out of scope for Phase 14.
- Cross-linking history to evidence bundles - belongs to Phase 15.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HST-01 | `project-ai/history/` is created as an append-only event log directory; each event is a sequentially numbered JSON file with fields: event_type, stage, timestamp, actor, tool_used, notes | Defines canonical event model, filename contract (`NNN_<event_type>.json`), atomic write path, and ordering rules. |
| HST-02 | `STATE.json` no longer contains an embedded history field; it holds current state only | Documents model/save/load refactor to remove serialized `history` while preserving compatibility shim behavior. |
| HST-03 | `core/history.py` helper provides `append_event(event)` and `read_history()` functions | Provides API shape, error handling expectations, and typed read/write patterns. |
| HST-04 | `minilegion history` command reads `history/` and prints a chronological timeline of recent events | Defines CLI output contract, empty-state behavior, and test surface for timeline command registration/output. |
| HST-05 | On first access of old `STATE.json` containing history, tool non-destructively migrates to `history/` files then strips `history` from `STATE.json` | Specifies migration algorithm, idempotency guardrails, and preservation checks. |
</phase_requirements>

## Summary

Phase 14 is a structural decoupling phase: history must move from mutable state snapshots into an append-only filesystem log while preserving legacy project compatibility. The current codebase still embeds `history` in `ProjectState` and writes history through `state.add_history(...)` across commands, approval gates, and context assembly. That coupling is the core architecture gap identified in the v1.1 milestone audit.

The safest implementation path is to add a dedicated `minilegion/core/history.py` module and route all durable event writes there, while keeping `ProjectState.add_history()` as a transition shim for callers that still invoke it. `load_state()` should perform one-time migration when old embedded history is detected: emit sequential event files, rewrite `STATE.json` without `history`, and preserve event chronology. Use existing `write_atomic()` for both event files and rewritten state to maintain existing crash-safety patterns.

Testing strategy should be phase-focused: add unit tests for filename sequencing, event read ordering, and migration idempotency; update CLI/context tests to consume history from `project-ai/history/` rather than `state.history`; and add CLI integration coverage for `minilegion history` output. This closes both requirement-level and E2E flow gaps raised by the audit.

**Primary recommendation:** Implement `core/history.py` first (append/read + migration helpers), then rewire state/context/commands and finish with `minilegion history` CLI plus regression tests.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.10 | Runtime and filesystem orchestration | Existing project baseline in `pyproject.toml`. |
| Typer | >=0.24.0 | CLI command surface (`minilegion history`) | Existing command framework and test harness (`CliRunner`). |
| Pydantic | >=2.12.0 | Typed event/state models and JSON validation | Already used for state/schemas and fits additive event contracts. |
| pytest | >=8.0 | Unit + CLI integration verification | Existing suite and conventions already in place. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `pathlib` | built-in | Directory scans, filename parsing, deterministic ordering | All history file discovery and sorting. |
| stdlib `json` | built-in | Legacy migration parsing and serialization semantics | Reading old `STATE.json` payloads and event files. |
| Existing `write_atomic()` | local utility | Atomic event/state writes | Every history append and migration rewrite. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Filesystem append-only JSON events | SQLite/event DB | Better querying, but violates locked storage decision and adds operational complexity. |
| Compatibility shim (`ProjectState.add_history`) during transition | Hard cutover with immediate caller rewrite | Faster cleanup but higher regression risk across many callsites. |
| First-access migration in `load_state()` | Explicit migration command | More explicit UX, but fails locked decision and can leave stale projects unmigrated. |

**Installation:**
```bash
pip install -e .[dev]
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── core/
│   ├── history.py            # append/read/migration helpers + event model
│   ├── state.py              # current-only state model + migration trigger in load_state
│   └── context_assembler.py  # recent history from history.read_history()
└── cli/
    └── commands.py           # emits events via append_event(), adds `history` command

tests/
├── test_history.py           # new: append/read/migration unit tests
├── test_state.py             # updated: no persisted state.history
├── test_context_assembler.py # updated: history source switched to history/
└── test_cli.py               # updated: command registration/output + `minilegion history`
```

### Pattern 1: Event Log Module as Single Writer
**What:** Centralize event persistence and retrieval in `core/history.py`.
**When to use:** Any command/approval path that records historical activity.
**Example:**
```python
# Source: project convention + HST-03
event = HistoryEvent(
    event_type="plan",
    stage="plan",
    timestamp=datetime.now().isoformat(),
    actor="system",
    tool_used="minilegion",
    notes="Plan completed and approved",
)
append_event(project_dir, event)
```

### Pattern 2: Current-State-Only Serialization
**What:** Keep runtime state object compatibility while excluding `history` from persisted `STATE.json`.
**When to use:** `save_state()` and migration rewrite path.
**Example:**
```python
# Source: HST-02/HST-05 contract
payload = state.model_dump(exclude={"history"})
write_atomic(state_path, json.dumps(payload, indent=2))
```

### Pattern 3: Deterministic File Order for Reads
**What:** Sort by parsed numeric prefix, never rely on filesystem order.
**When to use:** `read_history()` and CLI timeline output.
**Example:**
```python
# Source: Python pathlib docs - Path.glob order is unspecified
files = sorted(history_dir.glob("*.json"), key=parse_event_index)
```

### Anti-Patterns to Avoid
- **Directly appending to `state.history` as durable storage:** breaks HST-02/HST-03 and preserves coupling.
- **Relying on raw `glob()` iteration order:** Python docs explicitly state path results are in no particular order.
- **Non-atomic migration writes:** partial rewrites can corrupt state/event integrity during interruption.
- **Making migration destructive (drop-first then write):** violates HST-05 non-destructive requirement.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic persistence | ad hoc temp-file/rename logic in multiple places | existing `write_atomic()` | Already used project-wide; centralizes crash-safe behavior. |
| Schema validation | loose dict-based event parsing | Pydantic event model + `model_validate_json` | Prevents malformed events entering history timeline. |
| CLI parsing/output harness | subprocess-based ad hoc checks | `typer.testing.CliRunner` | Existing stable test pattern in repo. |
| Migration detection | brittle regex over JSON text | parse JSON then branch on `"history" in payload` | More robust and easier to test idempotency. |

**Key insight:** The hard part is not writing JSON files; it is preserving ordering, idempotency, and backward compatibility under partial failures.

## Common Pitfalls

### Pitfall 1: Index collisions during append
**What goes wrong:** Two appends derive the same next `NNN` and one overwrites or fails.
**Why it happens:** Next-index logic uses stale directory snapshot or unsorted filenames.
**How to avoid:** Compute next index from parsed max existing prefix immediately before write; keep writes atomic.
**Warning signs:** Duplicate index filenames or sporadic append failures in rapid command sequences.

### Pitfall 2: Timeline order drift
**What goes wrong:** `read_history()` returns events in nondeterministic order.
**Why it happens:** Filesystem iteration order is not guaranteed.
**How to avoid:** Parse numeric prefixes and sort explicitly before reading contents.
**Warning signs:** Flaky CLI history output ordering tests.

### Pitfall 3: Migration not idempotent
**What goes wrong:** Re-running migration duplicates events.
**Why it happens:** Migration lacks guard condition after first successful strip.
**How to avoid:** Trigger migration only when `STATE.json` still contains embedded `history` field.
**Warning signs:** Event counts grow on repeated `load_state()` calls without new commands.

### Pitfall 4: Hidden coupling in context/status surfaces
**What goes wrong:** `status` or `context` still reads `state.history`, so migrated projects show empty history.
**Why it happens:** Partial refactor updates write path but not read path.
**How to avoid:** Move all read paths (`status`, `context_assembler`, `history` command) to `read_history()`.
**Warning signs:** `minilegion history` works but `status`/`context` does not show recent events.

## Code Examples

Verified patterns from this codebase and official docs:

### Atomic write contract reused for event files
```python
# Source: minilegion/core/file_io.py
write_atomic(history_dir / "001_init.json", event.model_dump_json(indent=2))
```

### Existing state load pattern (migration insertion point)
```python
# Source: minilegion/core/state.py
raw = Path(path).read_text(encoding="utf-8")
return ProjectState.model_validate_json(raw)
```

### Existing history display fallback text to preserve
```python
# Source: minilegion/core/context_assembler.py
history_block = "\n".join(history_lines) if history_lines else "_No history yet._"
```

### Official ordering warning for glob results
```python
# Source: https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob
files = sorted(Path(history_dir).glob("*.json"))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Embedded mutable `state.history` in `STATE.json` | External append-only event log in `project-ai/history/` | Planned in v1.1 Phase 14 | Enables auditability and decouples state snapshots from timeline history. |
| Command handlers call `state.add_history(...)` then `save_state(...)` | Commands emit events through `append_event()` and state persists current-only fields | Planned in this phase | Prevents history loss during state rewrites and supports timeline querying. |
| No dedicated timeline command | `minilegion history` CLI for chronological event view | Planned in this phase | Closes E2E visibility gap from milestone audit. |

**Deprecated/outdated:**
- Embedded `history` in `STATE.json` is now considered legacy input only (migration source), not runtime source of truth.

## Open Questions

1. **How strict should filename sanitization be for `event_type` suffixes?**
   - What we know: Locked format is `NNN_<event_type>.json`; context suggests lowercase + underscores + safe chars.
   - What's unclear: Whether to preserve unknown symbols for readability or normalize aggressively.
   - Recommendation: Normalize to `[a-z0-9_]+` for filename safety, keep original `event_type` in JSON payload.

2. **Default timeline depth for `minilegion history` output**
   - What we know: Discretion item allows choosing row count.
   - What's unclear: Whether default should favor concise DX (5-10 rows) or fuller context.
   - Recommendation: Default to last 10 events with optional `--limit` follow-up in later phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/test_history.py tests/test_state.py tests/test_context_assembler.py tests/test_cli.py -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HST-01 | Sequential append-only event files in `project-ai/history/` with required fields | unit | `python -m pytest tests/test_history.py::TestAppendEvent -q` | ❌ Wave 0 |
| HST-02 | Persisted `STATE.json` excludes `history` field | unit | `python -m pytest tests/test_state.py -q` | ✅ (needs updates) |
| HST-03 | `append_event()` and `read_history()` APIs exist and behave deterministically | unit | `python -m pytest tests/test_history.py::TestReadHistory -q` | ❌ Wave 0 |
| HST-04 | `minilegion history` command prints chronological timeline / empty fallback | CLI integration | `python -m pytest tests/test_cli.py -q` | ✅ (needs new cases) |
| HST-05 | First-access migration moves embedded history to files and strips state field idempotently | unit + integration | `python -m pytest tests/test_history.py::TestMigration tests/test_state.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_history.py tests/test_state.py -q`
- **Per wave merge:** `python -m pytest tests/test_history.py tests/test_state.py tests/test_context_assembler.py tests/test_cli.py -q`
- **Phase gate:** `python -m pytest tests/ -x -q` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_history.py` - new coverage for append/read ordering, schema fields, and migration idempotency
- [ ] `tests/test_cli.py` - add command registration + output assertions for `minilegion history`
- [ ] `tests/test_context_assembler.py` - update/extend to verify history source is `history/` files
- [ ] `tests/test_init.py` - add assertion that new projects create `project-ai/history/` (or first append creates it deterministically)

## Sources

### Primary (HIGH confidence)
- `D:\test cli\.planning\phases\14-history-foundation-migration\14-CONTEXT.md` - locked phase decisions and discretion scope
- `D:\test cli\.planning\REQUIREMENTS.md` - HST-01..HST-05 requirement definitions
- `D:\test cli\.planning\ROADMAP.md` - phase goal, dependency, and plan split
- `D:\test cli\.planning\v1.1-MILESTONE-AUDIT.md` - integration and E2E history-flow gaps
- `D:\test cli\minilegion\core\state.py` - embedded history schema and load/save behavior
- `D:\test cli\minilegion\cli\commands.py` - current callsites writing/reading state history
- `D:\test cli\minilegion\core\context_assembler.py` - existing history read path and fallback text
- `D:\test cli\minilegion\core\file_io.py` - atomic write contract to reuse
- `D:\test cli\tests\test_state.py` / `D:\test cli\tests\test_cli.py` / `D:\test cli\tests\test_context_assembler.py` / `D:\test cli\tests\test_init.py` - current verification surface and gaps

### Secondary (MEDIUM confidence)
- https://docs.python.org/3/library/os.html#os.replace - atomic rename guarantees and cross-filesystem caveat
- https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob - glob iteration order is unspecified; explicit sorting required
- https://docs.python.org/3/library/json.html - JSON parser/serializer behavior for migration handling
- https://docs.pydantic.dev/latest/concepts/models/ - model validation APIs and default extra-data behavior (`ignore`)
- https://typer.tiangolo.com/tutorial/commands/ - multi-command CLI registration patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - directly grounded in `pyproject.toml` and current repository usage
- Architecture: MEDIUM - implementation choices are clear, but migration normalization defaults still require final design picks
- Pitfalls: HIGH - based on current code coupling plus official filesystem/docs behavior

**Research date:** 2026-03-11
**Valid until:** 2026-04-10
