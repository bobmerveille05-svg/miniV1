# Phase 17: Rollback + Doctor Health Surface — Research

**Researched:** 2026-03-12
**Domain:** CLI command implementation (typer), state machine backtrack, artifact preservation, project health checks
**Confidence:** HIGH — all findings verified directly against project source code

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rollback — Scope**
- Single-step only: `target = STAGE_ORDER[current_idx - 1]`. No multi-step rollback.
- Rollback from first stage (init) = structured error: Exit 1 with clear message — no previous stage exists.

**Rollback — Artifact Handling**
- Move current stage artifact only: Do not touch artifacts from previous stages.
- Destination: `project-ai/rejected/<ARTIFACT>.<timestamp>.rejected.<ext>`
  - Example: `DESIGN.20260312T051000Z.rejected.json`
  - Timestamp format: ISO compact (YYYYMMDDTHHMMSSz or similar stable format)
- Move semantics: Rename/move the artifact file — do not copy.

**Rollback — History Event**
- Append rollback event to `history/` via `core/history.py` `append_event()`
- Event fields (in `notes` or structured): `reason`, `from_stage`, `to_stage`, `artifact_moved` (path of moved artifact or `None` if no artifact existed)

**Doctor — Checks (7 total)**
1. `state_valid` — STATE.json parses and validates against ProjectState schema
2. `artifact_present` — current-stage expected artifact file exists AND is non-whitespace
3. `history_readable` — `project-ai/history/` exists and all `.json` entries parse as HistoryEvent
4. `stage_coherence` — stage↔artifact coherence (stage=design → DESIGN.json exists, etc.)
5. `adapter_base` — `project-ai/adapters/_base.md` exists (required, always checked)
6. `adapter_active` — active/requested adapter present only if one is configured/selected in config or STATE
7. (implicit in checks 1-6; total check surface covers DOC-02's 4+ incoherence classes)

**Doctor — Output Format**
- One line per check: `[PASS]`, `[WARN]`, `[FAIL]` prefix
- Colored using `typer.style()` (GREEN for PASS, YELLOW for WARN, RED for FAIL) — matching existing coherence check style
- Final summary line: `Doctor: pass` / `Doctor: warn` / `Doctor: fail`

**Doctor — Exit Behavior**
- `0` — all checks pass
- `1` — any WARN (no FAIL)
- `2` — any FAIL

**Tests**
- Tests-first (TDD) for both commands
- Single test file: `tests/test_cli_rollback_doctor.py`
- Both commands have clean, deterministic contracts — ideal for RED→GREEN cycle

**Plan Structure**
- 17-01: Rollback command (RBK-01, RBK-02) — implement first
- 17-02: Doctor command (DOC-01, DOC-02, DOC-03) — implement second
- Wave 1 parallel (independent implementations)

### OpenCode's Discretion
- Exact stage→artifact filename mapping for doctor checks (follow `core/preflight.py` REQUIRED_FILES pattern)
- Whether `artifact_present` and `stage_coherence` are merged or separate checks
- Error message wording for structured rollback errors
- Timestamp format precision (seconds vs milliseconds)

### Deferred Ideas (OUT OF SCOPE)
None — all discussion points resolved. Scope is fully locked.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RBK-01 | `minilegion rollback "<reason>"` resets STATE.json stage to the correct previous stage without silently deleting the current artifact (artifact is moved to `rejected/`) | StateMachine.transition() handles backward transition + clears downstream approvals; Path.rename() for move semantics |
| RBK-02 | Rollback appends a rollback event to `history/` with reason, timestamp, previous stage, and reset-to stage | `append_event()` already accepts arbitrary `event_type` and `notes`; rollback metadata packed into `notes` field as JSON string |
| DOC-01 | `minilegion doctor` checks: STATE.json schema validity, stage coherence, current artifact present, history/ readable, and requested adapter present | All 6 checks derive from existing subsystems: `load_state()`, `STAGE_ORDER`, `preflight.REQUIRED_FILES`, `read_history()`, adapter file path convention |
| DOC-02 | Doctor detects at least 4 classes of incoherence: invalid STATE.json, missing current-stage artifact, missing or corrupt history/, stage-artifact mismatch, missing adapter definition | 6 distinct checks provide 6 incoherence classes, well exceeding the 4-class minimum; each class maps to a different FAIL/WARN level |
| DOC-03 | Doctor outputs a green/yellow/red status per check, with a summary pass/warn/fail conclusion | `typer.style()` with `typer.colors.GREEN/YELLOW/RED` — exact same pattern as coherence check output in commands.py lines 1406-1414 |
</phase_requirements>

---

## Summary

Phase 17 adds two fully independent CLI commands (`rollback` and `doctor`) to `minilegion/cli/commands.py`. Both depend on already-complete subsystems and introduce no new core modules — only new command functions wiring together existing APIs.

**Rollback** is a single backward state-machine step: compute previous stage via `STAGE_ORDER`, rename the current artifact to `project-ai/rejected/<NAME>.<timestamp>.rejected.<ext>`, call `StateMachine.transition()` to backtrack (which automatically clears downstream approvals), and append a history event via `append_event()`. The only subtlety is the `rejected/` directory creation, compact timestamp formatting, and the "rollback from first stage" guard.

**Doctor** is a stateless health-check loop: run 6 ordered checks against the project filesystem, accumulate pass/warn/fail statuses, emit one styled line per check, then emit a summary line and exit with the appropriate code (0/1/2). All 6 checks read from files only — no mutations. The "4+ incoherence classes" requirement (DOC-02) is satisfied by the 6 distinct checks, each covering a different failure class.

**Primary recommendation:** Implement both commands entirely within `commands.py` following the `advance()` / `validate()` command patterns. No new core modules needed.

---

## Standard Stack

### Core (already installed — no new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | ≥0.24.0 | CLI command registration, styled output, exit codes | Project-wide CLI framework |
| pydantic | ≥2.12.0 | ProjectState validation in doctor's `state_valid` check | Already used for all schema validation |
| pathlib.Path | stdlib | File move (rename), directory creation | Used throughout commands.py |
| datetime | stdlib | Compact ISO timestamp for rejected artifact filenames | Already used in `_append_state_event()` |

**No new dependencies required.**

---

## Architecture Patterns

### Existing Command Pattern (verified from commands.py)

Every command follows this exact structure:
```python
@app.command()
def rollback(reason: Annotated[str, typer.Argument(help="Reason for rollback")]) -> None:
    """..."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        # ... logic ...
        typer.echo(typer.style("...", fg=typer.colors.GREEN))
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

Key properties verified:
- `find_project_dir()` handles `ConfigError` if no `project-ai/` directory exists
- All structured errors raised as `MiniLegionError` subclasses, caught at the outer `except` block
- Non-zero exit via `raise typer.Exit(code=N)` — never `sys.exit()`
- Colored output via `typer.style(msg, fg=typer.colors.GREEN/YELLOW/RED)`

### Rollback: Stage → Artifact Mapping

From `preflight.py` REQUIRED_FILES, the canonical current-stage artifact per stage is:

| Stage | Current Artifact | File |
|-------|-----------------|------|
| `init` | none | — (rollback from init = error) |
| `brief` | BRIEF.md | `BRIEF.md` |
| `research` | RESEARCH.json | `RESEARCH.json` |
| `design` | DESIGN.json | `DESIGN.json` |
| `plan` | PLAN.json | `PLAN.json` |
| `execute` | EXECUTION_LOG.json | `EXECUTION_LOG.json` |
| `review` | REVIEW.json | `REVIEW.json` |
| `archive` | (terminal) | `REVIEW.json` (or no rollback) |

**OpenCode's discretion:** Define a `STAGE_ARTIFACT` dict in commands.py (parallel to `VALIDATION_TARGETS`):
```python
STAGE_CURRENT_ARTIFACT: dict[Stage, str] = {
    Stage.BRIEF: "BRIEF.md",
    Stage.RESEARCH: "RESEARCH.json",
    Stage.DESIGN: "DESIGN.json",
    Stage.PLAN: "PLAN.json",
    Stage.EXECUTE: "EXECUTION_LOG.json",
    Stage.REVIEW: "REVIEW.json",
    Stage.ARCHIVE: "REVIEW.json",  # or disallow rollback from archive
}
```

Stages `INIT` is absent — attempted rollback from init raises structured error before any artifact handling.

### Rejected Artifact Naming

**Format** (OpenCode's discretion — seconds precision is sufficient):
```
<BASENAME>.<YYYYMMDDTHHMMSSz>.<rejected>.<ext>
```

Examples:
- `DESIGN.json` → `DESIGN.20260312T051000Z.rejected.json`
- `BRIEF.md` → `BRIEF.20260312T051000Z.rejected.md`

**Python implementation:**
```python
from datetime import datetime, timezone

def _rejected_filename(original: str) -> str:
    """Build rejected artifact filename with compact UTC timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem, _, ext = original.partition(".")  # "DESIGN", ".", "json"
    return f"{stem}.{ts}.rejected.{ext}"
```

Note: `BRIEF.md` splits as stem=`BRIEF`, ext=`md`. `RESEARCH.json` splits as stem=`RESEARCH`, ext=`json`. All artifact names have exactly one dot — safe to use `partition(".")`.

### Rollback Move Semantics

```python
# Source: project_dir / DESIGN.json
# Dest:   project_dir / rejected / DESIGN.20260312T051000Z.rejected.json
rejected_dir = project_dir / "rejected"
rejected_dir.mkdir(parents=True, exist_ok=True)
artifact_path = project_dir / artifact_filename  # e.g. DESIGN.json
if artifact_path.exists():
    dest = rejected_dir / _rejected_filename(artifact_filename)
    artifact_path.rename(dest)
    artifact_moved = str(dest.relative_to(project_dir.parent))
else:
    artifact_moved = None
```

`Path.rename()` is the correct move primitive — atomic on same filesystem, no copy-then-delete.

### Rollback History Event

Pack structured rollback metadata into the `notes` field (HistoryEvent has no extra fields):
```python
import json as _json

notes = _json.dumps({
    "reason": reason,
    "from_stage": from_stage.value,
    "to_stage": to_stage.value,
    "artifact_moved": artifact_moved,  # str path or None
})
append_event(
    project_dir,
    HistoryEvent(
        event_type="rollback",
        stage=to_stage.value,
        timestamp=datetime.now().isoformat(),
        actor="system",
        tool_used="minilegion",
        notes=notes,
    ),
)
```

### Doctor: Check Structure

Doctor runs 6 independent checks and accumulates results. Each check produces one of:
- `("PASS", description)` — green
- `("WARN", description)` — yellow  
- `("FAIL", description)` — red

**Recommended internal structure:**
```python
CheckResult = tuple[str, str]  # (status, message)

def _check_state_valid(project_dir: Path) -> CheckResult: ...
def _check_artifact_present(project_dir: Path) -> CheckResult: ...
def _check_history_readable(project_dir: Path) -> CheckResult: ...
def _check_stage_coherence(project_dir: Path) -> CheckResult: ...
def _check_adapter_base(project_dir: Path) -> CheckResult: ...
def _check_adapter_active(project_dir: Path, config: MiniLegionConfig) -> CheckResult: ...
```

Each function is a standalone helper in commands.py — keeps doctor() function clean and each check independently testable.

### Doctor: Output Format (verified against existing coherence output)

```python
COLOR_MAP = {"PASS": typer.colors.GREEN, "WARN": typer.colors.YELLOW, "FAIL": typer.colors.RED}

for status, message in results:
    label = f"[{status}]"
    typer.echo(typer.style(f"{label} {message}", fg=COLOR_MAP[status]))

# Summary line
if any(s == "FAIL" for s, _ in results):
    summary_status = "fail"
    summary_color = typer.colors.RED
    exit_code = 2
elif any(s == "WARN" for s, _ in results):
    summary_status = "warn"
    summary_color = typer.colors.YELLOW
    exit_code = 1
else:
    summary_status = "pass"
    summary_color = typer.colors.GREEN
    exit_code = 0

typer.echo(typer.style(f"Doctor: {summary_status}", fg=summary_color))
raise typer.Exit(code=exit_code)
```

**Important:** `raise typer.Exit(code=0)` works correctly — Typer's CliRunner captures it as exit_code=0, not an exception. However, for the pass case, you can also simply `return` (Typer defaults to exit 0). Use `raise typer.Exit(code=exit_code)` uniformly for clarity.

### Doctor: Stage→Artifact Coherence (DOC-02 classes)

The `stage_coherence` check reuses the REQUIRED_FILES pattern from `preflight.py`. For doctor purposes, the "current stage artifact" mapping is:

| Stage | Expected Artifact |
|-------|------------------|
| init | (none required) |
| brief | BRIEF.md |
| research | RESEARCH.json |
| design | DESIGN.json |
| plan | PLAN.json |
| execute | EXECUTION_LOG.json |
| review | REVIEW.json |
| archive | REVIEW.json |

`stage_coherence` checks: does the current-stage artifact exist? If the stage has no expected artifact (init), it always passes.

**DOC-02 incoherence class mapping:**

| Class | Check Name | Trigger Condition | Severity |
|-------|-----------|-------------------|----------|
| 1. Invalid STATE.json | `state_valid` | Cannot parse/validate ProjectState | FAIL |
| 2. Missing current-stage artifact | `artifact_present` | Expected artifact file missing or whitespace-only | FAIL |
| 3. Missing or corrupt history/ | `history_readable` | history/ dir missing, OR any `.json` file fails HistoryEvent parse | WARN |
| 4. Stage-artifact mismatch | `stage_coherence` | state.current_stage reports X but X's artifact doesn't exist | FAIL |
| 5. Missing _base.md | `adapter_base` | `project-ai/adapters/_base.md` absent | WARN |
| 6. Missing active adapter | `adapter_active` | Config specifies a tool (e.g. "claude") but `adapters/claude.md` absent | WARN |

Classes 1+2+4 are FAIL-level (hard incoherence). Classes 3+5+6 are WARN-level (operational degradation). DOC-02 requires "at least 4 classes" — all 6 are covered.

**Note on `artifact_present` vs `stage_coherence`:** These are intentionally separate checks per CONTEXT.md. `artifact_present` checks content (non-whitespace) while `stage_coherence` checks existence + stage consistency. They can produce different pass/fail results for the same artifact.

### Doctor: Adapter Active Check

The `adapter_active` check is conditioned on whether a tool/adapter is configured. Based on the project:
- `load_config()` returns `MiniLegionConfig` which has no "selected_tool" field — adapters are specified at command invocation (`minilegion context claude`)
- **Recommendation:** Check if any non-`_base.md` adapter file is present at all. If `adapters/` exists but is empty of tool adapters, emit WARN. If `adapters/` directory itself is missing, that's covered by `adapter_base` FAIL.
- Alternatively (simpler): skip `adapter_active` check if no `engines` config or similar indicates a locked tool. Emit PASS with "no active adapter configured" message.

The CONTEXT.md says "active/requested adapter present only if one is configured/selected in config or STATE". Given no config field tracks selected adapter, the safest implementation is: always PASS if `adapters/` has at least one `*.md` besides `_base.md`, else WARN.

### Anti-Patterns to Avoid

- **Don't raise MiniLegionError inside doctor check helpers** — they should return `("FAIL", message)` tuples, never raise. Doctor must survive any individual check failure to report all checks.
- **Don't call `StateMachine.transition()` from rollback without loading state first** — always `load_state()` before constructing `StateMachine`.
- **Don't use `shutil.copy` for artifact preservation** — use `Path.rename()` (move semantics as required).
- **Don't forget `rejected_dir.mkdir(parents=True, exist_ok=True)`** — `rejected/` won't exist on first rollback.
- **Don't use `raise typer.Exit(code=0)` inside a nested `try` block** — Typer Exit is not a MiniLegionError, the outer except won't catch it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom open/write | `write_atomic()` from `core/file_io.py` | Already used for all artifact writes; handles temp-file swap |
| State loading/saving | Direct JSON read | `load_state()` / `save_state()` | Handles legacy migration, Pydantic validation, atomic writes |
| History append | Direct file write | `append_event()` from `core/history.py` | Handles monotonic index, safe naming, directory creation |
| State backtrack | Custom stage math | `StateMachine.transition()` | Handles approval clearing on backtrack automatically |
| Styled terminal output | ANSI escape codes | `typer.style()` with `typer.colors.*` | Project standard; works with CliRunner in tests |

---

## Common Pitfalls

### Pitfall 1: `raise typer.Exit(code=2)` Inside `except MiniLegionError`

**What goes wrong:** If doctor's summary `raise typer.Exit(code=2)` is inside the `except MiniLegionError` block, it will never be reached — it's only triggered by `MiniLegionError`.
**Why it happens:** Copy-paste from advance/validate commands that only use exit code 1.
**How to avoid:** Doctor's exit-code logic runs in the `try` block, not in the error handler. The `except MiniLegionError` block only handles unexpected errors (e.g., `find_project_dir()` failing).
**Structure:**
```python
@app.command()
def doctor() -> None:
    try:
        project_dir = find_project_dir()
        config = load_config(project_dir.parent)
        results = [
            _check_state_valid(project_dir),
            ...
        ]
        # emit lines, compute exit_code
        raise typer.Exit(code=exit_code)  # ← inside try, not except
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

### Pitfall 2: `StateMachine.transition()` Raises on Invalid Backtrack

**What goes wrong:** Rollback calls `sm.transition(to_stage)` but `to_stage` is only valid if `current_idx > 0`. Calling transition when at `init` raises `InvalidTransitionError`.
**Why it happens:** The guard against "rollback from init" must come BEFORE constructing StateMachine or calling transition.
**How to avoid:** Check `current_idx = STAGE_ORDER.index(current)` before any transition attempt:
```python
current_idx = STAGE_ORDER.index(current)
if current_idx == 0:
    typer.echo(typer.style("Cannot rollback: already at first stage (init).", fg=typer.colors.RED))
    raise typer.Exit(code=1)
to_stage = STAGE_ORDER[current_idx - 1]
```

### Pitfall 3: Doctor `state_valid` Check Must Handle Missing STATE.json

**What goes wrong:** `load_state()` raises `FileNotFoundError` (not a MiniLegionError) if STATE.json doesn't exist.
**Why it happens:** `load_state()` calls `state_path.read_text()` directly — no existence guard.
**How to avoid:** In `_check_state_valid()`, wrap in a broad `except (Exception,)`:
```python
def _check_state_valid(project_dir: Path) -> CheckResult:
    state_path = project_dir / "STATE.json"
    if not state_path.exists():
        return ("FAIL", "state_valid: STATE.json not found")
    try:
        load_state(state_path)
        return ("PASS", "state_valid: STATE.json valid")
    except Exception as exc:
        return ("FAIL", f"state_valid: {exc}")
```

### Pitfall 4: Rollback Leaves STATE.json Unsaved on Exception

**What goes wrong:** If `Path.rename()` succeeds but `save_state()` fails, state is rolled back in memory but not persisted — and the artifact is already moved.
**Why it happens:** Operations aren't transactional.
**How to avoid:** Follow the existing command pattern — do artifact move last, after state is fully prepared but before save:
```python
# 1. Prepare new state in memory
sm.transition(to_stage)
state.current_stage = to_stage.value

# 2. Move artifact (can fail safely — state not yet saved)
artifact_moved = _move_artifact_to_rejected(project_dir, from_stage)

# 3. Append history event
_append_state_event(...)

# 4. Save state (only after all other operations)
save_state(state, project_dir / "STATE.json")
```

### Pitfall 5: Doctor Exits With Code 0 Even When Using `raise typer.Exit(code=0)`

**What goes wrong:** Developer expects `raise typer.Exit(code=0)` to be "unusual" and wraps in error handling.
**How to avoid:** `typer.Exit` is a standard Typer control-flow exception, not an error. The CliRunner captures it as `result.exit_code`. Always use `raise typer.Exit(code=exit_code)` at the end of the doctor happy path, or simply `return` (which also gives exit 0).

---

## Code Examples

### Rollback Command Skeleton
```python
# Source: commands.py pattern (modeled on advance())
@app.command()
def rollback(
    reason: Annotated[str, typer.Argument(help="Reason for rollback")]
) -> None:
    """Reset to the previous stage, preserving the current artifact as rejected."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        current = Stage(state.current_stage)
        current_idx = STAGE_ORDER.index(current)

        # Guard: cannot rollback from first stage
        if current_idx == 0:
            typer.echo(
                typer.style(
                    "Cannot rollback: already at first stage (init). No previous stage exists.",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        to_stage = STAGE_ORDER[current_idx - 1]

        # Move current artifact to rejected/
        artifact_moved = _move_artifact_to_rejected(project_dir, current)

        # Transition state (clears downstream approvals automatically)
        sm = StateMachine(current, state.approvals)
        sm.transition(to_stage)
        state.current_stage = to_stage.value
        state.approvals = sm.approvals

        # Append rollback history event
        notes = _json.dumps({
            "reason": reason,
            "from_stage": current.value,
            "to_stage": to_stage.value,
            "artifact_moved": artifact_moved,
        })
        append_event(
            project_dir,
            HistoryEvent(
                event_type="rollback",
                stage=to_stage.value,
                timestamp=datetime.now().isoformat(),
                actor="system",
                tool_used="minilegion",
                notes=notes,
            ),
        )
        save_state(state, project_dir / "STATE.json")

        typer.echo(
            typer.style(
                f"Rolled back: {current.value} -> {to_stage.value}. Reason: {reason}",
                fg=typer.colors.GREEN,
            )
        )

    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

### `_move_artifact_to_rejected` Helper
```python
STAGE_CURRENT_ARTIFACT: dict[Stage, str] = {
    Stage.BRIEF: "BRIEF.md",
    Stage.RESEARCH: "RESEARCH.json",
    Stage.DESIGN: "DESIGN.json",
    Stage.PLAN: "PLAN.json",
    Stage.EXECUTE: "EXECUTION_LOG.json",
    Stage.REVIEW: "REVIEW.json",
    Stage.ARCHIVE: "REVIEW.json",
}

def _rejected_filename(original_name: str) -> str:
    """Build rejected artifact filename: DESIGN.20260312T051000Z.rejected.json"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem, _, ext = original_name.partition(".")
    return f"{stem}.{ts}.rejected.{ext}"

def _move_artifact_to_rejected(project_dir: Path, stage: Stage) -> str | None:
    """Move current stage artifact to rejected/. Returns relative path or None."""
    artifact_name = STAGE_CURRENT_ARTIFACT.get(stage)
    if artifact_name is None:
        return None
    artifact_path = project_dir / artifact_name
    if not artifact_path.exists():
        return None
    rejected_dir = project_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    dest = rejected_dir / _rejected_filename(artifact_name)
    artifact_path.rename(dest)
    return str(dest)
```

### Doctor Command Skeleton
```python
@app.command()
def doctor() -> None:
    """Check project health: state, artifacts, history, adapters."""
    try:
        project_dir = find_project_dir()
        config = load_config(project_dir.parent)

        results: list[tuple[str, str]] = [
            _check_state_valid(project_dir),
            _check_artifact_present(project_dir),
            _check_history_readable(project_dir),
            _check_stage_coherence(project_dir),
            _check_adapter_base(project_dir),
            _check_adapter_active(project_dir, config),
        ]

        color_map = {
            "PASS": typer.colors.GREEN,
            "WARN": typer.colors.YELLOW,
            "FAIL": typer.colors.RED,
        }
        for status, message in results:
            typer.echo(typer.style(f"[{status}] {message}", fg=color_map[status]))

        if any(s == "FAIL" for s, _ in results):
            typer.echo(typer.style("Doctor: fail", fg=typer.colors.RED))
            raise typer.Exit(code=2)
        elif any(s == "WARN" for s, _ in results):
            typer.echo(typer.style("Doctor: warn", fg=typer.colors.YELLOW))
            raise typer.Exit(code=1)
        else:
            typer.echo(typer.style("Doctor: pass", fg=typer.colors.GREEN))
            # exit 0 — no raise needed, but explicit is clearer:
            raise typer.Exit(code=0)

    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| STATE.json embedded history | Append-only history/ events | Phase 14 | Rollback event goes to history/, not STATE |
| Stage advancement bundled with artifact creation | Separate validate/advance gates | Phase 15 | Rollback must clear approval flags; `StateMachine.transition()` already handles this |
| No artifact preservation | Rejected artifact in `rejected/` | Phase 17 (this phase) | New directory convention |

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥ 8.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `python -m pytest tests/test_cli_rollback_doctor.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Test File

Single file: `tests/test_cli_rollback_doctor.py`

### Fixture Patterns (from test_cli_validate_advance.py)

All tests follow the same 4-line setup pattern:
```python
def test_something(self, tmp_path, monkeypatch):
    project_ai = tmp_path / "project-ai"
    project_ai.mkdir()
    _write_state(project_ai, "design")   # set current_stage
    monkeypatch.chdir(tmp_path)          # find_project_dir() resolves CWD/project-ai
    # arrange additional files, then invoke
    result = runner.invoke(app, ["rollback", "design rejected"])
    assert result.exit_code == ...
```

The `_write_state()` helper must be copied/shared in the new test file (or imported from a conftest). The existing helper pattern:
```python
def _write_state(project_ai, current_stage: str, approvals: dict[str, bool] | None = None):
    default_approvals = {k: False for k in [
        "brief_approved", "research_approved", "design_approved",
        "plan_approved", "execute_approved", "review_approved"
    ]}
    if approvals:
        default_approvals.update(approvals)
    state_data = {
        "current_stage": current_stage,
        "approvals": default_approvals,
        "completed_tasks": [],
        "metadata": {},
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
```

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RBK-01 | `rollback "reason"` resets STATE.json stage to previous | unit | `pytest tests/test_cli_rollback_doctor.py::TestRollback::test_rollback_resets_stage -x` | ❌ Wave 0 |
| RBK-01 | Rollback moves artifact to `rejected/` with correct name | unit | `pytest tests/test_cli_rollback_doctor.py::TestRollback::test_rollback_moves_artifact_to_rejected -x` | ❌ Wave 0 |
| RBK-01 | Rollback from `init` exits 1 with error (no previous stage) | unit | `pytest tests/test_cli_rollback_doctor.py::TestRollback::test_rollback_from_init_exits_nonzero -x` | ❌ Wave 0 |
| RBK-01 | Rollback with no artifact present still succeeds (artifact_moved=None) | unit | `pytest tests/test_cli_rollback_doctor.py::TestRollback::test_rollback_no_artifact_succeeds -x` | ❌ Wave 0 |
| RBK-01 | Rollback clears downstream approvals | unit | `pytest tests/test_cli_rollback_doctor.py::TestRollback::test_rollback_clears_downstream_approvals -x` | ❌ Wave 0 |
| RBK-02 | Rollback appends history event with reason/from_stage/to_stage/artifact_moved | unit | `pytest tests/test_cli_rollback_doctor.py::TestRollback::test_rollback_appends_history_event -x` | ❌ Wave 0 |
| DOC-01 | Doctor on healthy project exits 0, all PASS | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_healthy_project_exits_zero -x` | ❌ Wave 0 |
| DOC-01 | Doctor exits 2 on invalid STATE.json | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_invalid_state_fails -x` | ❌ Wave 0 |
| DOC-01 | Doctor exits 2 on missing current artifact | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_missing_artifact_fails -x` | ❌ Wave 0 |
| DOC-02 | Doctor detects corrupt history/ entry (WARN) | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_corrupt_history_warns -x` | ❌ Wave 0 |
| DOC-02 | Doctor detects stage-artifact mismatch (FAIL) | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_stage_artifact_mismatch_fails -x` | ❌ Wave 0 |
| DOC-02 | Doctor detects missing _base.md (WARN) | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_missing_adapter_base_warns -x` | ❌ Wave 0 |
| DOC-03 | Doctor outputs [PASS]/[WARN]/[FAIL] per check | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_output_format -x` | ❌ Wave 0 |
| DOC-03 | Doctor summary line is "Doctor: pass/warn/fail" | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_summary_line -x` | ❌ Wave 0 |
| DOC-03 | Doctor exits 1 on WARN-only (no FAIL) | unit | `pytest tests/test_cli_rollback_doctor.py::TestDoctor::test_doctor_warn_only_exits_one -x` | ❌ Wave 0 |

### RED Cases: Rollback (17-01)

These tests must be written BEFORE implementation and must fail (RED) until the `rollback` command is implemented:

```
TestRollback::test_rollback_resets_stage
  setup: stage=design, DESIGN.json present
  invoke: ["rollback", "rejected for budget reasons"]
  assert: exit_code == 0
  assert: STATE.json current_stage == "research"

TestRollback::test_rollback_moves_artifact_to_rejected
  setup: stage=design, DESIGN.json present with content
  invoke: ["rollback", "bad design"]
  assert: (project_ai / "DESIGN.json").exists() == False
  assert: any file in (project_ai / "rejected").iterdir() matches "DESIGN.*.rejected.json"
  assert: that file has non-empty content

TestRollback::test_rollback_from_init_exits_nonzero
  setup: stage=init
  invoke: ["rollback", "oops"]
  assert: exit_code == 1
  assert: "init" in result.output.lower() or "first" in result.output.lower()

TestRollback::test_rollback_no_artifact_succeeds
  setup: stage=design, NO DESIGN.json present
  invoke: ["rollback", "no artifact yet"]
  assert: exit_code == 0
  assert: STATE.json current_stage == "research"
  assert: (project_ai / "rejected").exists() == False  (or empty)

TestRollback::test_rollback_clears_downstream_approvals
  setup: stage=plan, approvals={brief_approved: True, research_approved: True, design_approved: True, plan_approved: True}
  invoke: ["rollback", "plan rejected"]
  assert: exit_code == 0
  state = load STATE.json
  assert: state.approvals["plan_approved"] == False
  assert: state.approvals["design_approved"] == False  (design is at/after rollback target "research")
  assert: state.approvals["brief_approved"] == True   (brief is before target)
  assert: state.approvals["research_approved"] == True (research is target — stays True? Verify StateMachine logic)
  # Note: StateMachine clears approvals for stages AT OR AFTER target_idx

TestRollback::test_rollback_appends_history_event
  setup: stage=design, DESIGN.json present
  invoke: ["rollback", "not good enough"]
  assert: exit_code == 0
  history_files = list((project_ai / "history").glob("*.json"))
  assert: len(history_files) >= 1
  last_event = HistoryEvent.model_validate_json(max(history_files, key=lambda p: p.stem).read_text())
  assert: last_event.event_type == "rollback"
  notes = json.loads(last_event.notes)
  assert: notes["reason"] == "not good enough"
  assert: notes["from_stage"] == "design"
  assert: notes["to_stage"] == "research"
  assert: notes["artifact_moved"] is not None  (path string)
```

### RED Cases: Doctor (17-02)

These tests must be written BEFORE implementation and must fail (RED) until the `doctor` command is implemented:

```
TestDoctor::test_doctor_healthy_project_exits_zero
  setup: stage=research, RESEARCH.json present (non-empty),
         history/ exists with one valid event,
         adapters/_base.md exists, adapters/claude.md exists,
         BRIEF.md present (coherence: research stage has BRIEF.md)
  invoke: ["doctor"]
  assert: exit_code == 0
  assert: "Doctor: pass" in result.output
  assert: result.output.count("[PASS]") >= 4

TestDoctor::test_doctor_invalid_state_fails
  setup: STATE.json = "not valid json!!!"
  (no monkeypatch.chdir needed for state — doctor catches parse error)
  invoke: ["doctor"]
  assert: exit_code == 2
  assert: "[FAIL]" in result.output
  assert: "Doctor: fail" in result.output

TestDoctor::test_doctor_missing_artifact_fails
  setup: stage=design, NO DESIGN.json
  invoke: ["doctor"]
  assert: exit_code == 2
  assert: "[FAIL]" in result.output

TestDoctor::test_doctor_corrupt_history_warns
  setup: stage=research, RESEARCH.json present,
         history/ exists, history/001_corrupt.json = "not-valid-json!!!"
         (but HistoryEvent parse fails)
  invoke: ["doctor"]
  assert: exit_code >= 1  (WARN → 1 or FAIL → 2)
  assert: "[WARN]" in result.output or "[FAIL]" in result.output
  # Note: history_readable returns WARN for corrupt entries per decisions

TestDoctor::test_doctor_stage_artifact_mismatch_fails
  setup: stage=design, DESIGN.json missing (but BRIEF.md and RESEARCH.json present)
  invoke: ["doctor"]
  assert: exit_code == 2
  assert: "stage_coherence" in result.output  (check name in message)

TestDoctor::test_doctor_missing_adapter_base_warns
  setup: stage=init, history/ exists (empty is fine),
         adapters/ exists but NO _base.md
  invoke: ["doctor"]
  assert: exit_code == 1  (WARN only)
  assert: "[WARN]" in result.output
  assert: "adapter_base" in result.output

TestDoctor::test_doctor_warn_only_exits_one
  setup: stage=init, history/ missing (WARN for history_readable)
         but STATE.json valid, no artifact required for init
  invoke: ["doctor"]
  assert: exit_code == 1
  assert: "Doctor: warn" in result.output

TestDoctor::test_doctor_output_format
  setup: minimal healthy project (all checks pass)
  invoke: ["doctor"]
  assert: each line in output starts with "[PASS]", "[WARN]", "[FAIL]", or "Doctor:"
  assert: "Doctor: pass" is last line (or near last)

TestDoctor::test_doctor_summary_line
  setup: stage=design, DESIGN.json missing (→ FAIL)
  invoke: ["doctor"]
  assert: result.output.strip().endswith("Doctor: fail")
```

### DOC-02: Verifying "4+ Incoherence Classes"

DOC-02 requires detecting "at least 4 classes of incoherence." The 6 check implementation covers 6 distinct classes. Test coverage approach:

1. **Class 1 (invalid STATE.json):** `test_doctor_invalid_state_fails` — corrupt JSON
2. **Class 2 (missing current-stage artifact):** `test_doctor_missing_artifact_fails` — stage=design, no DESIGN.json
3. **Class 3 (missing/corrupt history/):** `test_doctor_corrupt_history_warns` — corrupt history entry
4. **Class 4 (stage-artifact mismatch):** `test_doctor_stage_artifact_mismatch_fails` — stage says design but no DESIGN.json
5. **Class 5 (missing _base.md):** `test_doctor_missing_adapter_base_warns` — no adapters/_base.md
6. **Class 6 (missing active adapter):** Optional — covered by `adapter_active` check

Note: Classes 2 and 4 may overlap (`artifact_present` and `stage_coherence` can detect the same missing file from different angles). This is intentional — they're separate checks with distinct messages. The tests for each should verify the specific check name appears in output.

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_cli_rollback_doctor.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cli_rollback_doctor.py` — covers RBK-01, RBK-02, DOC-01, DOC-02, DOC-03 (full test file, all RED at start)
- [ ] No new framework install needed — pytest ≥ 8.0 already present per pyproject.toml

*(Existing test infrastructure covers all phase requirements — only the new test file is needed)*

---

## Open Questions

1. **Approval clearing on rollback: which approvals get cleared?**
   - What we know: `StateMachine.transition(to_stage)` on backtrack clears approvals "for stages AT OR AFTER target_idx" (from state.py lines 153-161)
   - What's clear: Rolling back from `plan` to `research` would clear `design_approved`, `plan_approved` (stages ≥ research idx). `brief_approved` and `research_approved` remain True.
   - Recommendation: Trust the existing `StateMachine.transition()` behavior and verify with test `test_rollback_clears_downstream_approvals`.

2. **Doctor `adapter_active` check — what counts as "an active adapter"?**
   - What we know: No config field tracks which tool is "selected". The context command takes `tool` as an argument.
   - What's unclear: Should `adapter_active` check if ALL 4 tool adapters are present, or just any one?
   - Recommendation (OpenCode's discretion): PASS if at least one `*.md` adapter file (besides `_base.md`) exists in `adapters/`. WARN if `adapters/` exists but has no tool-specific adapters. If `adapters/` is absent, `adapter_base` already FAIL'd.

3. **Rollback from `archive` stage — allowed or blocked?**
   - What we know: CONTEXT.md defines rollback as "single-step backward". Archive has no forward stage but does have a backward (review).
   - What's unclear: Should archive rollback be allowed?
   - Recommendation: Allow it (StateMachine.can_transition supports any backward step). The `STAGE_CURRENT_ARTIFACT` mapping for ARCHIVE → REVIEW.json provides the artifact to preserve.

---

## Sources

### Primary (HIGH confidence)
- Direct source code analysis: `minilegion/core/state.py` — StateMachine.transition(), STAGE_ORDER, approval clearing logic
- Direct source code analysis: `minilegion/core/history.py` — append_event(), HistoryEvent schema
- Direct source code analysis: `minilegion/core/preflight.py` — REQUIRED_FILES stage→artifact mapping
- Direct source code analysis: `minilegion/cli/commands.py` — command pattern (advance, validate, history), `_append_state_event()`, `typer.style()` usage
- Direct source code analysis: `tests/test_cli_validate_advance.py` — `_write_state()` fixture, CliRunner pattern
- Direct source code analysis: `minilegion/core/exceptions.py` — exception hierarchy

### Secondary (MEDIUM confidence)
- `pyproject.toml` — pytest ≥ 8.0, typer ≥ 0.24.0, pydantic ≥ 2.12.0 confirmed installed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in pyproject.toml and imports
- Architecture: HIGH — all patterns verified directly in commands.py source
- Pitfalls: HIGH — derived from reading actual implementation code
- Test patterns: HIGH — copied from working test_cli_validate_advance.py

**Research date:** 2026-03-12
**Valid until:** Until commands.py or history.py API changes (stable — no LLM-layer changes in this phase)
