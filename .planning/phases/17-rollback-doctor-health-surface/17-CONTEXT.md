# Phase 17: Rollback + Doctor Health Surface — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning
**Source:** /gsd-discuss-phase 17

<domain>
## Phase Boundary

Phase 17 delivers two new CLI commands:

1. `minilegion rollback "<reason>"` — single-step backward reset with artifact preservation and history event
2. `minilegion doctor` — project health surface with per-check green/yellow/red output and pass/warn/fail summary

This is the final phase of v1.1 Portable Kernel. Both commands depend on already-complete subsystems: `core/history.py`, `core/state.py`, `core/evidence.py`, `core/preflight.py`.

</domain>

<decisions>
## Implementation Decisions

### Rollback — Scope

- **Single-step only**: `target = STAGE_ORDER[current_idx - 1]`. No multi-step rollback.
- **Rollback from first stage (init) = structured error**: Exit 1 with clear message — no previous stage exists.

### Rollback — Artifact Handling

- **Move current stage artifact only**: Do not touch artifacts from previous stages.
- **Destination**: `project-ai/rejected/<ARTIFACT>.<timestamp>.rejected.<ext>`
  - Example: `DESIGN.20260312T051000Z.rejected.json`
  - Timestamp format: ISO compact (YYYYMMDDTHHMMSSz or similar stable format)
- **Move semantics**: Rename/move the artifact file — do not copy.

### Rollback — History Event

- **Append rollback event** to `history/` via `core/history.py` `append_event()`
- **Event fields** (in `notes` or structured): `reason`, `from_stage`, `to_stage`, `artifact_moved` (path of moved artifact or `None` if no artifact existed)

### Doctor — Checks (7 total)

1. `state_valid` — STATE.json parses and validates against ProjectState schema
2. `artifact_present` — current-stage expected artifact file exists AND is non-whitespace
3. `history_readable` — `project-ai/history/` exists and all `.json` entries parse as HistoryEvent
4. `stage_coherence` — stage↔artifact coherence (stage=design → DESIGN.json exists, etc.)
5. `adapter_base` — `project-ai/adapters/_base.md` exists (required, always checked)
6. `adapter_active` — active/requested adapter present only if one is configured/selected in config or STATE
7. (implicit in checks 1-6; total check surface covers DOC-02's 4+ incoherence classes)

### Doctor — Output Format

- **One line per check**: `[PASS]`, `[WARN]`, `[FAIL]` prefix
- **Colored** using `typer.style()` (GREEN for PASS, YELLOW for WARN, RED for FAIL) — matching existing coherence check style
- **Final summary line**: `Doctor: pass` / `Doctor: warn` / `Doctor: fail`

### Doctor — Exit Behavior

- `0` — all checks pass
- `1` — any WARN (no FAIL)
- `2` — any FAIL

### Tests

- **Tests-first (TDD)** for both commands
- Single test file: `tests/test_cli_rollback_doctor.py`
- Both commands have clean, deterministic contracts — ideal for RED→GREEN cycle

### Plan Structure

- **17-01**: Rollback command (RBK-01, RBK-02) — implement first
- **17-02**: Doctor command (DOC-01, DOC-02, DOC-03) — implement second
- Wave 1 parallel (independent implementations)

### OpenCode's Discretion

- Exact stage→artifact filename mapping for doctor checks (follow `core/preflight.py` REQUIRED_FILES pattern)
- Whether `artifact_present` and `stage_coherence` are merged or separate checks
- Error message wording for structured rollback errors
- Timestamp format precision (seconds vs milliseconds)

</decisions>

<deferred>
## Deferred Ideas

None — all discussion points resolved. Scope is fully locked.

</deferred>

---

*Phase: 17-rollback-doctor-health-surface*
*Context gathered: 2026-03-12 via /gsd-discuss-phase 17*
