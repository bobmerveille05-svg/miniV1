# Phase 11: Archivist & Coherence - Research

**Researched:** 2026-03-10
**Domain:** Python — deterministic pipeline archival + cross-artifact coherence validation
**Confidence:** HIGH (all findings from direct codebase inspection, zero LLM speculation)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `archive` command replaces the `_pipeline_stub` at `Stage.ARCHIVE`
- Fully deterministic: reads REVIEW.json, PLAN.json, EXECUTION_LOG.json, DESIGN.json — NO LLM calls
- Requires `review_approved = True` in STATE.json (enforce via preflight)
- Updates `state.completed_tasks` from EXECUTION_LOG.json task IDs
- Adds `final_verdict` to `state.metadata` (pulled from REVIEW.json)
- Adds history entry: "archive" action with summary
- Transitions `current_stage` → `archive` after saving
- **No new approval gate** — archive is deterministic, no human approval needed
- Writes `DECISIONS.md` in `project-ai/` from DESIGN.json `architecture_decisions` list
- DECISIONS.md format: `### Decision: {decision}`, Rationale, Alternatives Rejected sections
- Created/overwritten atomically via `write_atomic()`
- `render_decisions_md(design_data: DesignSchema) -> str` added to `renderer.py`
- 5 coherence checks in a new `core/coherence.py` module
- `check_coherence(project_dir: Path) -> list[CoherenceIssue]` — never raises, never mutates
- `CoherenceIssue` dataclass: `check_name: str`, `severity: str` ("warning"|"error"), `message: str`
- Coherence issues are **non-blocking** — archive proceeds even if issues found
- Issues logged as warnings in STATE.json metadata and printed to stdout
- Coherence runs inside `archive()` (and can be surfaced in `status`)

### OpenCode's Discretion
- Internal structure of `coherence.py` (helper functions, etc.)
- Whether `CoherenceIssue` uses dataclass vs NamedTuple vs Pydantic — prefer dataclass for simplicity
- Exact wording of coherence check messages
- Whether coherence is its own command or only called from archive — implement as function called by archive; expose in status output

### Deferred Ideas (OUT OF SCOPE)
- Standalone `minilegion coherence` command
- Rich/TUI output for coherence issues
- Coherence check for conventions→review is relaxed (check 5 is soft) — no strict enforcement
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-01 | Archivist is fully deterministic — no LLM calls | Archive reads JSON artifacts only; no adapter/LLM paths in implementation |
| ARCH-02 | After review passes, Archivist updates STATE.json with completed tasks, final verdict, and history entry | `state.completed_tasks`, `state.metadata["final_verdict"]`, `state.add_history()` all available in ProjectState |
| ARCH-03 | Archivist updates DECISIONS.md with any architecture decisions made during the cycle | `DesignSchema.architecture_decisions: list[ArchitectureDecision]` — each has `decision`, `rationale`, `alternatives_rejected` |
| COHR-01 | Research→Design check: recommended_focus_files from RESEARCH.json were read by Designer | `ResearchSchema.recommended_focus_files: list[str]`; DESIGN.json components have `files: list[str]` |
| COHR-02 | Design→Plan check: every component in DESIGN.json has at least 1 task in PLAN.json | `DesignSchema.components[*].name` vs `PlanSchema.tasks[*].component` |
| COHR-03 | Plan→Execute check: files in patches are subset of touched_files in PLAN.json | `ExecutionLogSchema.tasks[*].changed_files[*].path` vs `PlanSchema.touched_files` |
| COHR-04 | Design→Review check: execution conforms to DESIGN.json components and interfaces | `ReviewSchema.design_conformity.conforms: bool` — direct boolean read |
| COHR-05 | Research conventions→Review check: code follows conventions from RESEARCH.json | `ResearchSchema.existing_conventions` vs `ReviewSchema.convention_violations` — soft check |
</phase_requirements>

---

## Summary

Phase 11 delivers two fully deterministic capabilities with zero LLM calls. The **Archivist** (`archive` command) finalizes the pipeline cycle by reading four existing JSON artifacts (REVIEW.json, PLAN.json, EXECUTION_LOG.json, DESIGN.json), updating STATE.json with completed tasks and verdict, and writing DECISIONS.md. The **Coherence** subsystem (`core/coherence.py`) performs 5 read-only checks across artifact boundaries, returning issues as a list of dataclass instances without mutating state or raising exceptions.

Both capabilities compose entirely from existing infrastructure: `write_atomic()`, `load_state()`/`save_state()`, existing Pydantic schemas, and the `renderer.py` render-function pattern. The `archive` command follows the identical pattern as all 8 existing pipeline commands: `find_project_dir → load_config(parent) → load_state → StateMachine → can_transition guard → check_preflight → [work] → save_state`. No approval gate is added (archive is deterministic).

The test suite currently has 490 tests. Phase 11 should add approximately 20–25 new tests across three new test files: `test_coherence.py` (unit tests for each check), `test_render_decisions.py` (renderer unit tests), and `test_cli_archive.py` (CLI integration tests).

**Primary recommendation:** Implement in three logical units — (1) `render_decisions_md()` in renderer.py, (2) `core/coherence.py` with `CoherenceIssue` dataclass and `check_coherence()`, (3) `archive()` command in commands.py with preflight update. This separation matches existing test file organization.

---

## Standard Stack

### Core (already present — no new dependencies)
| Module | Location | Purpose | Already Used By |
|--------|----------|---------|-----------------|
| `dataclasses` | stdlib | `CoherenceIssue` dataclass | N/A — stdlib only |
| `json` | stdlib | Parse JSON artifacts in coherence checks | `commands.py` (review command) |
| `pathlib.Path` | stdlib | File path resolution | All modules |
| `pydantic` | minilegion deps | Schema validation for loaded artifacts | All pipeline commands |

**No new pip dependencies required.**

### Existing Infrastructure to Reuse
| Asset | Location | How Used in Phase 11 |
|-------|----------|---------------------|
| `write_atomic(path, content)` | `core/file_io.py` | Write DECISIONS.md atomically |
| `save_state(state, path)` | `core/state.py` | Persist updated STATE.json after archive |
| `load_state(path)` | `core/state.py` | Read current state in archive command |
| `check_preflight(stage, project_dir)` | `core/preflight.py` | Enforce review_approved before archive |
| `ResearchSchema`, `DesignSchema`, `PlanSchema`, `ExecutionLogSchema`, `ReviewSchema` | `core/schemas.py` | Parse all 5 artifacts in coherence checks |
| `Stage.ARCHIVE` | `core/state.py` | Target stage for state transition |
| `FORWARD_TRANSITIONS[Stage.REVIEW] = Stage.ARCHIVE` | `core/state.py` | Already defined — no changes needed |
| `_RENDERERS` dict | `core/renderer.py` | Register `render_decisions_md` (NOT needed — DECISIONS.md is a standalone file, not via save_dual) |
| `CliRunner` + `typer.testing` | test infrastructure | CLI tests |
| `monkeypatch` | pytest | Mock `find_project_dir`, `check_preflight`, etc. |

---

## Architecture Patterns

### Recommended File Structure for Phase 11
```
minilegion/
├── core/
│   ├── coherence.py        # NEW: CoherenceIssue dataclass + check_coherence()
│   ├── preflight.py        # MODIFY: add Stage.ARCHIVE to REQUIRED_FILES + REQUIRED_APPROVALS
│   ├── renderer.py         # MODIFY: add render_decisions_md()
│   └── ...existing...
├── cli/
│   └── commands.py         # MODIFY: add archive() command (replace stub)
tests/
├── test_coherence.py       # NEW: unit tests for all 5 checks
├── test_cli_archive.py     # NEW: CLI integration tests for archive command
└── test_renderer.py        # MODIFY: add render_decisions_md tests (or new file)
```

### Pattern 1: Pipeline Command (archive follows this exactly)
**What:** Every pipeline command loads state, guards transition, runs preflight, does work, saves state.
**When to use:** Every `@app.command()` that advances the pipeline.

```python
# Source: minilegion/cli/commands.py (all existing commands)
@app.command()
def archive() -> None:
    """Run the archive stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.ARCHIVE):
            typer.echo(typer.style(
                f"Cannot transition from {state.current_stage} to {Stage.ARCHIVE.value}",
                fg=typer.colors.RED,
            ))
            raise typer.Exit(code=1)

        # No load_config() needed — archive makes no LLM calls
        check_preflight(Stage.ARCHIVE, project_dir)

        # [archive work — see below]

        sm.transition(Stage.ARCHIVE)
        state.current_stage = Stage.ARCHIVE.value  # CRITICAL: sync ProjectState manually
        state.add_history("archive", "Pipeline archived")
        save_state(state, project_dir / "STATE.json")
        typer.echo(typer.style("Archive complete. Stage: archive", fg=typer.colors.GREEN))

    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

**Key difference from other commands:** No `ApprovalError` try/except block — no approval gate in archive.

### Pattern 2: Preflight Extension
**What:** Add `Stage.ARCHIVE` to both declarative dicts in `preflight.py`.
**Critical:** ARCHIVE has no LLM call, but still needs files + approval enforced.

```python
# Source: minilegion/core/preflight.py — extend existing dicts
REQUIRED_FILES: dict[Stage, list[str]] = {
    # ... existing entries ...
    Stage.ARCHIVE: ["REVIEW.json", "PLAN.json", "EXECUTION_LOG.json", "DESIGN.json"],
}

REQUIRED_APPROVALS: dict[Stage, list[str]] = {
    # ... existing entries ...
    Stage.ARCHIVE: ["review_approved"],
}
```

### Pattern 3: Renderer Function Addition
**What:** `render_decisions_md()` follows the exact same signature pattern as the 5 existing render functions. It is NOT registered in `_RENDERERS` because DECISIONS.md is written with `write_atomic()` directly (not via `save_dual()`).

```python
# Source: minilegion/core/renderer.py — follow existing pattern
def render_decisions_md(design_data: DesignSchema) -> str:
    """Render architecture decisions from DesignSchema to DECISIONS.md."""
    parts: list[str] = ["# Architecture Decisions\n\n"]

    if not design_data.architecture_decisions:
        parts.append("_No architecture decisions recorded._\n")
        return "".join(parts)

    for ad in design_data.architecture_decisions:
        parts.append(f"### Decision: {ad.decision}\n\n")
        parts.append(f"**Rationale:** {ad.rationale}\n\n")
        if ad.alternatives_rejected:
            parts.append("**Alternatives Rejected:**\n\n")
            for alt in ad.alternatives_rejected:
                parts.append(f"- {alt}\n")
            parts.append("\n")

    return "".join(parts)
```

### Pattern 4: CoherenceIssue Dataclass
**What:** Simple dataclass per CONTEXT.md decision. Prefer `@dataclass` over NamedTuple (mutable if needed for testing, cleaner repr).

```python
# Source: new core/coherence.py
from dataclasses import dataclass

@dataclass
class CoherenceIssue:
    check_name: str
    severity: str  # "warning" | "error"
    message: str
```

### Pattern 5: check_coherence() — Never Raises
**What:** Loads all available artifacts, runs 5 checks, returns issues. Missing artifacts = partial check (skip gracefully with a warning).

```python
# Source: new core/coherence.py
def check_coherence(project_dir: Path) -> list[CoherenceIssue]:
    """Run all 5 inter-phase coherence checks. Never raises. Never mutates state."""
    issues: list[CoherenceIssue] = []
    project_dir = Path(project_dir)

    # Load artifacts — each wrapped in try/except; missing file = skip that check
    research = _load_json(project_dir / "RESEARCH.json", ResearchSchema)
    design = _load_json(project_dir / "DESIGN.json", DesignSchema)
    plan = _load_json(project_dir / "PLAN.json", PlanSchema)
    execution_log = _load_json(project_dir / "EXECUTION_LOG.json", ExecutionLogSchema)
    review = _load_json(project_dir / "REVIEW.json", ReviewSchema)

    # Run checks only when required artifacts are available
    if research and design:
        issues.extend(_check_research_design(research, design))
    if design and plan:
        issues.extend(_check_design_plan(design, plan))
    if plan and execution_log:
        issues.extend(_check_plan_execute(plan, execution_log))
    if review:
        issues.extend(_check_design_review(review))
    if research and review:
        issues.extend(_check_research_review(research, review))

    return issues
```

### Pattern 6: Archive Command — Reading Artifacts
**What:** Archive reads all 4 JSON artifacts using the same `.model_validate_json()` pattern.

```python
# Source: pattern from commands.py review() reading PLAN.json, DESIGN.json
import json as _json

# Read EXECUTION_LOG.json for completed task IDs
execution_log_json = (project_dir / "EXECUTION_LOG.json").read_text(encoding="utf-8")
execution_log = ExecutionLogSchema.model_validate_json(execution_log_json)

# Read REVIEW.json for final_verdict
review_json = (project_dir / "REVIEW.json").read_text(encoding="utf-8")
review_data = ReviewSchema.model_validate_json(review_json)

# Read DESIGN.json for architecture decisions
design_json = (project_dir / "DESIGN.json").read_text(encoding="utf-8")
design_data = DesignSchema.model_validate_json(design_json)
```

### Pattern 7: completed_tasks Population
**What:** `state.completed_tasks` is `list[str]`. Populate from `ExecutionLogSchema.tasks[*].task_id`.

```python
# Source: schemas.py — TaskResult.task_id: str, ExecutionLogSchema.tasks: list[TaskResult]
task_ids = [tr.task_id for tr in execution_log.tasks]
state.completed_tasks = task_ids  # Replace (not extend) — archive is final
```

**Edge case:** If `execution_log.tasks` is empty, `state.completed_tasks` becomes `[]`. This is valid — archive still succeeds.

### Pattern 8: final_verdict in metadata
**What:** `state.metadata` is `dict[str, str]`. Store verdict as string.

```python
# Source: schemas.py — ReviewSchema.verdict: Verdict (Verdict is str+Enum, .value is str)
state.metadata["final_verdict"] = review_data.verdict.value  # "pass" or "revise"
```

### Pattern 9: Coherence Issues in metadata
**What:** Non-blocking issues are logged to `state.metadata` as a JSON string.

```python
# Consistent with how revise_count is stored: state.metadata["revise_count"] = str(n)
if issues:
    import json as _json
    state.metadata["coherence_issues"] = _json.dumps([
        {"check": i.check_name, "severity": i.severity, "message": i.message}
        for i in issues
    ])
```

### Anti-Patterns to Avoid
- **Calling `load_config()` in archive:** Archive needs NO LLM calls, so NO config/adapter needed. Do not follow the LLM command pattern of `config = load_config(project_dir.parent)`.
- **Adding ApprovalError handler:** Archive has no approval gate. Don't copy the `except ApprovalError` block from other commands.
- **Registering `render_decisions_md` in `_RENDERERS`:** DECISIONS.md is written directly with `write_atomic()`, not through `save_dual()`. The renderer dict is for the 5 LLM schema types only.
- **Raising from `check_coherence()`:** The function contract is "never raises". Wrap every artifact load in try/except. A missing file is a skipped check, not an error.
- **Blocking archive on coherence issues:** Issues are warnings. Print them, log them to metadata, then proceed with archival.
- **Using `state.current_stage = Stage.ARCHIVE` (enum value instead of `.value`):** Always set `state.current_stage = Stage.ARCHIVE.value` (the string "archive") to maintain JSON serializability. This is the CRITICAL sync gap fix pattern documented in STATE.md.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom write + rename | `write_atomic()` from `core/file_io.py` | Already handles temp file, fsync, os.replace, cleanup on failure |
| JSON artifact loading | Raw `json.loads()` + manual dict access | `Schema.model_validate_json(text)` | Type-safe, validated, field names match `schemas.py` exactly |
| State persistence | Direct JSON serialization | `save_state(state, path)` | Uses `write_atomic()` internally, handles model_dump_json |
| Issue accumulation | Custom result type | `list[CoherenceIssue]` with `extend()` | Simple, standard, testable |

---

## Common Pitfalls

### Pitfall 1: Missing `state.current_stage = Stage.ARCHIVE.value` sync
**What goes wrong:** `sm.transition(Stage.ARCHIVE)` updates `sm.current_stage` on the `StateMachine` object, but `state.current_stage` (on `ProjectState`) is NOT automatically synced. Saving state before this manual assignment leaves the state at "review".
**Why it happens:** StateMachine and ProjectState are separate objects with no binding.
**How to avoid:** Always follow: `sm.transition(Stage.ARCHIVE)` → `state.current_stage = Stage.ARCHIVE.value` → `save_state(state, ...)`. This is documented as CRITICAL in STATE.md [Phase 06-02] and repeated for every command.
**Warning signs:** Test asserting `state_data["current_stage"] == "archive"` fails while everything else passes.

### Pitfall 2: Coherence check raising on missing files
**What goes wrong:** `check_coherence()` attempts to read `RESEARCH.json`, but it doesn't exist (e.g. fast mode was used). Unhandled `FileNotFoundError` propagates up and crashes `archive`.
**Why it happens:** Coherence checks can run even when not all artifacts exist.
**How to avoid:** Wrap each artifact load in a helper that returns `None` on any error:
```python
def _load_json(path: Path, schema_cls):
    try:
        return schema_cls.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None
```
Then guard each check: `if research and design: issues.extend(...)`.
**Warning signs:** `archive` fails with `FileNotFoundError` or `ValidationError` when a JSON file is missing.

### Pitfall 3: COHR-01 check is too strict
**What goes wrong:** Check compares `recommended_focus_files` against ALL files in ALL components. But `component.files` might contain directory paths (e.g. `"minilegion/core/"`) while focus files are specific (e.g. `"minilegion/core/state.py"`). Exact string match fails.
**Why it happens:** The existing `DESIGN.json` fixtures in tests use `"minilegion/core/"` as a component file (see `test_cli_review.py:116`). Focus files are typically more specific.
**How to avoid:** COHR-01 checks that recommended_focus_files appear ANYWHERE in component files. Use a "contains or is prefix of" heuristic OR just check that the focus file is a substring of any component file path:
```python
# Check: is focus_file a substring of any component file entry?
all_component_files = [f for c in design.components for f in c.files]
for focus_file in research.recommended_focus_files:
    if not any(focus_file in cf or cf in focus_file for cf in all_component_files):
        issues.append(CoherenceIssue(
            check_name="research_design",
            severity="warning",
            message=f"Focus file '{focus_file}' not found in any design component"
        ))
```
**Warning signs:** COHR-01 always reports false positives when component files are directories.

### Pitfall 4: COHR-02 component name matching case-sensitivity
**What goes wrong:** `DesignSchema.components[*].name` is "Core" but `PlanSchema.tasks[*].component` might be "core" or "Core module". Exact match fails.
**Why it happens:** No case normalization exists in current schemas. LLMs produce inconsistent casing.
**How to avoid:** Normalize to lowercase for comparison:
```python
component_names = {c.name.lower() for c in design.components}
covered = {t.component.lower() for t in plan.tasks if t.component}
missing = component_names - covered
for name in missing:
    issues.append(CoherenceIssue(check_name="design_plan", severity="warning", ...))
```
**Warning signs:** COHR-02 reports false positives despite tasks clearly referencing components.

### Pitfall 5: Importing `check_coherence` in `archive()` without updating imports
**What goes wrong:** `commands.py` has explicit imports at the top. Adding `check_coherence` call without adding the import causes `NameError`.
**Why it happens:** Python's import section needs to include `from minilegion.core.coherence import check_coherence`.
**How to avoid:** Update the imports section of `commands.py` when wiring archive.

### Pitfall 6: DECISIONS.md rendered even when no architecture decisions exist
**What goes wrong:** `design_data.architecture_decisions` is an empty list. Renderer produces a near-empty file. This is still valid but should be handled gracefully.
**How to avoid:** The renderer should output a sensible placeholder. See Pattern 3 code example above.

---

## Code Examples

### Reading EXECUTION_LOG.json task IDs (ARCH-02)
```python
# Source: schemas.py — ExecutionLogSchema.tasks: list[TaskResult], TaskResult.task_id: str
execution_log = ExecutionLogSchema.model_validate_json(
    (project_dir / "EXECUTION_LOG.json").read_text(encoding="utf-8")
)
task_ids = [tr.task_id for tr in execution_log.tasks]
# e.g. ["T1", "T2", "T3"]
state.completed_tasks = task_ids
```

### Reading final_verdict from REVIEW.json (ARCH-02)
```python
# Source: schemas.py — ReviewSchema.verdict: Verdict (Verdict.PASS.value == "pass")
review_data = ReviewSchema.model_validate_json(
    (project_dir / "REVIEW.json").read_text(encoding="utf-8")
)
state.metadata["final_verdict"] = review_data.verdict.value  # "pass" | "revise"
```

### Coherence Check 1 — Research→Design (COHR-01)
```python
# Source: schemas.py — ResearchSchema.recommended_focus_files: list[str]
#                       DesignSchema.components[*].files: list[str]
def _check_research_design(research: ResearchSchema, design: DesignSchema) -> list[CoherenceIssue]:
    issues = []
    all_component_files = [f for c in design.components for f in c.files]
    for focus_file in research.recommended_focus_files:
        if not any(focus_file in cf or cf in focus_file for cf in all_component_files):
            issues.append(CoherenceIssue(
                check_name="research_design",
                severity="warning",
                message=f"Recommended focus file '{focus_file}' not covered by any design component",
            ))
    return issues
```

### Coherence Check 2 — Design→Plan (COHR-02)
```python
# Source: schemas.py — DesignSchema.components[*].name, PlanSchema.tasks[*].component
def _check_design_plan(design: DesignSchema, plan: PlanSchema) -> list[CoherenceIssue]:
    issues = []
    component_names = {c.name.lower() for c in design.components}
    covered = {t.component.lower() for t in plan.tasks if t.component}
    for missing in component_names - covered:
        issues.append(CoherenceIssue(
            check_name="design_plan",
            severity="warning",
            message=f"Component '{missing}' has no tasks in PLAN.json",
        ))
    return issues
```

### Coherence Check 3 — Plan→Execute (COHR-03)
```python
# Source: schemas.py — ExecutionLogSchema.tasks[*].changed_files[*].path
#                       PlanSchema.touched_files: list[str]
def _check_plan_execute(plan: PlanSchema, execution_log: ExecutionLogSchema) -> list[CoherenceIssue]:
    issues = []
    touched = set(plan.touched_files)
    for tr in execution_log.tasks:
        for cf in tr.changed_files:
            if cf.path not in touched:
                issues.append(CoherenceIssue(
                    check_name="plan_execute",
                    severity="error",
                    message=f"File '{cf.path}' was changed but not in PLAN.json touched_files",
                ))
    return issues
```

### Coherence Check 4 — Design→Review (COHR-04)
```python
# Source: schemas.py — ReviewSchema.design_conformity.conforms: bool
def _check_design_review(review: ReviewSchema) -> list[CoherenceIssue]:
    issues = []
    if not review.design_conformity.conforms:
        deviations = "; ".join(review.design_conformity.deviations) or "unspecified"
        issues.append(CoherenceIssue(
            check_name="design_review",
            severity="error",
            message=f"Design conformity failed: {deviations}",
        ))
    return issues
```

### Coherence Check 5 — Research→Review (COHR-05, soft)
```python
# Source: schemas.py — ResearchSchema.existing_conventions: list[str]
#                       ReviewSchema.convention_violations: list[str]
def _check_research_review(research: ResearchSchema, review: ReviewSchema) -> list[CoherenceIssue]:
    # Soft check: if there are convention violations, report as warning
    issues = []
    if review.convention_violations:
        issues.append(CoherenceIssue(
            check_name="research_review",
            severity="warning",
            message=f"Convention violations found: {'; '.join(review.convention_violations)}",
        ))
    return issues
```

### Printing coherence issues in archive command
```python
# Follow the "[WARNING] / [ERROR]" pattern from CONTEXT.md specifics
issues = check_coherence(project_dir)
for issue in issues:
    prefix = "[WARNING]" if issue.severity == "warning" else "[ERROR]"
    typer.echo(typer.style(
        f"{prefix} {issue.check_name}: {issue.message}",
        fg=typer.colors.YELLOW if issue.severity == "warning" else typer.colors.RED,
    ))
if issues:
    import json as _json
    state.metadata["coherence_issues"] = _json.dumps([
        {"check": i.check_name, "severity": i.severity, "message": i.message}
        for i in issues
    ])
```

### Archive command output (from CONTEXT.md specifics)
```python
# "N tasks completed. Verdict: pass/revise. DECISIONS.md written."
typer.echo(
    typer.style(
        f"Archiving... {len(task_ids)} tasks completed. "
        f"Verdict: {review_data.verdict.value}. DECISIONS.md written.",
        fg=typer.colors.GREEN,
    )
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_pipeline_stub` (all pipeline commands) | Full implementation (archive is the last stub) | Phase 6 through 10 — progressive replacement | archive is the last stub to replace |
| None (no coherence validation) | `check_coherence()` as first-class function | Phase 11 | Enables drift detection across all stage artifacts |
| All history entries by stage | `action="archive"` history entry with summary | Phase 11 | Marks pipeline completion in history |

**Deprecated/outdated:**
- `_pipeline_stub` for archive: still exists in commands.py (line 71), archive is the only command that still uses it — Phase 11 replaces this.

---

## Open Questions

1. **Should `archive` command work from `review` stage only, or also from `archive` (re-run)?**
   - What we know: `FORWARD_TRANSITIONS[Stage.REVIEW] = Stage.ARCHIVE` means `can_transition` only allows `review → archive`. Running archive twice would fail the transition guard.
   - What's unclear: Is re-running archive needed? CONTEXT.md doesn't mention it.
   - Recommendation: Leave as-is (forward only). If re-run is needed, user can check the `can_transition` guard message.

2. **COHR-01: How strict should the file matching be?**
   - What we know: Component files in tests use directory-like paths (`"minilegion/core/"`) while focus files are specific (`"minilegion/core/state.py"`). Exact match would always fail.
   - What's unclear: Was the CONTEXT.md intent for strict file-level matching or component-level coverage?
   - Recommendation: Use substring matching (either direction) as documented in Pitfall 3. Severity: "warning" not "error" — keeps it non-blocking and forgiving.

3. **Does `status` command need to display coherence issues from metadata?**
   - What we know: CONTEXT.md says "expose in status output". `state.metadata["coherence_issues"]` will contain JSON string.
   - What's unclear: Exactly how much status output formatting is needed.
   - Recommendation: If status change is in scope, add a simple block that parses and prints coherence_issues from metadata if present. If not needed for Phase 11 success criteria, defer.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, confirmed running) |
| Config file | `pyproject.toml` (test runner configured there) |
| Quick run command | `pytest tests/test_coherence.py tests/test_cli_archive.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | archive() makes zero LLM calls | unit | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_no_llm_calls -x` | ❌ Wave 0 |
| ARCH-02a | state.completed_tasks populated from EXECUTION_LOG task IDs | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_sets_completed_tasks -x` | ❌ Wave 0 |
| ARCH-02b | state.metadata["final_verdict"] set from REVIEW.json verdict | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_sets_final_verdict -x` | ❌ Wave 0 |
| ARCH-02c | history entry added with action="archive" | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_adds_history_entry -x` | ❌ Wave 0 |
| ARCH-02d | state.current_stage transitions to "archive" | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_transitions_state -x` | ❌ Wave 0 |
| ARCH-02e | preflight enforces review_approved=True | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_preflight_requires_review_approved -x` | ❌ Wave 0 |
| ARCH-03 | DECISIONS.md written with architecture decisions | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_writes_decisions_md -x` | ❌ Wave 0 |
| ARCH-03 | render_decisions_md() includes decision, rationale, alternatives | unit | `pytest tests/test_renderer.py::TestRenderDecisionsMd -x` | ❌ Wave 0 |
| COHR-01 | focus_file missing from component files → warning issue | unit | `pytest tests/test_coherence.py::TestCheckResearchDesign::test_missing_focus_file_reports_warning -x` | ❌ Wave 0 |
| COHR-01 | all focus files covered → no issues | unit | `pytest tests/test_coherence.py::TestCheckResearchDesign::test_all_focus_files_covered_no_issues -x` | ❌ Wave 0 |
| COHR-02 | component with no tasks → warning issue | unit | `pytest tests/test_coherence.py::TestCheckDesignPlan::test_component_without_task_reports_warning -x` | ❌ Wave 0 |
| COHR-02 | all components covered → no issues | unit | `pytest tests/test_coherence.py::TestCheckDesignPlan::test_all_components_covered_no_issues -x` | ❌ Wave 0 |
| COHR-03 | changed file not in touched_files → error issue | unit | `pytest tests/test_coherence.py::TestCheckPlanExecute::test_out_of_scope_file_reports_error -x` | ❌ Wave 0 |
| COHR-03 | all changed files in touched_files → no issues | unit | `pytest tests/test_coherence.py::TestCheckPlanExecute::test_in_scope_files_no_issues -x` | ❌ Wave 0 |
| COHR-04 | design_conformity.conforms=False → error issue | unit | `pytest tests/test_coherence.py::TestCheckDesignReview::test_nonconformity_reports_error -x` | ❌ Wave 0 |
| COHR-04 | design_conformity.conforms=True → no issues | unit | `pytest tests/test_coherence.py::TestCheckDesignReview::test_conformity_no_issues -x` | ❌ Wave 0 |
| COHR-05 | convention_violations non-empty → warning | unit | `pytest tests/test_coherence.py::TestCheckResearchReview::test_violations_reports_warning -x` | ❌ Wave 0 |
| COHR-01..05 | missing artifact file → check skipped, no exception | unit | `pytest tests/test_coherence.py::TestCheckCoherence::test_missing_artifact_skips_check -x` | ❌ Wave 0 |
| COHR-01..05 | all artifacts coherent → empty list returned | integration | `pytest tests/test_coherence.py::TestCheckCoherence::test_coherent_pipeline_returns_empty_list -x` | ❌ Wave 0 |
| ARCH-01..03 + COHR-01..05 | archive runs coherence and logs issues to metadata | integration | `pytest tests/test_cli_archive.py::TestArchiveCommand::test_archive_logs_coherence_issues -x` | ❌ Wave 0 |
| ARCH-02e | preflight for ARCHIVE stage in REQUIRED_FILES/REQUIRED_APPROVALS | unit | `pytest tests/test_preflight.py -k "archive" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_coherence.py tests/test_cli_archive.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green (≥ 490 + ~20-25 new) before `/gsd-verify-work`

### Wave 0 Gaps

All test files for Phase 11 are new:

- [ ] `tests/test_coherence.py` — covers COHR-01 through COHR-05 (unit tests per check + integration of `check_coherence()`)
- [ ] `tests/test_cli_archive.py` — covers ARCH-01, ARCH-02, ARCH-03 (CLI integration tests)
- [ ] `minilegion/core/coherence.py` — the module under test (must exist before tests can import it)
- Existing `tests/test_renderer.py` — add `TestRenderDecisionsMd` class OR create `tests/test_render_decisions.py`
- Existing `tests/test_preflight.py` — add tests for `Stage.ARCHIVE` entries in REQUIRED_FILES/REQUIRED_APPROVALS

Framework install: Not needed — pytest already installed and running.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection: `minilegion/core/schemas.py` — exact field names and types for all 5 artifact schemas
- Direct inspection: `minilegion/core/state.py` — `ProjectState` fields, `Stage` enum, `FORWARD_TRANSITIONS`, `StateMachine` API
- Direct inspection: `minilegion/core/preflight.py` — `REQUIRED_FILES` and `REQUIRED_APPROVALS` dicts, `check_preflight()` signature
- Direct inspection: `minilegion/core/renderer.py` — render function signatures, `_RENDERERS` dict, `save_dual()` pattern
- Direct inspection: `minilegion/cli/commands.py` — all pipeline command patterns including ApprovalError handling, state sync fix
- Direct inspection: `minilegion/core/file_io.py` — `write_atomic()` signature and behavior
- Direct inspection: `minilegion/core/exceptions.py` — exception hierarchy
- Direct inspection: `tests/test_cli_review.py` — full CLI test pattern including mock setup helpers
- Direct inspection: `tests/test_renderer.py` — renderer unit test patterns
- Direct inspection: `tests/test_preflight.py` — preflight test patterns
- Direct inspection: `tests/conftest.py` — shared fixtures
- Direct inspection: `.planning/phases/11-archivist-coherence/11-CONTEXT.md` — locked decisions
- Verified: `python -m pytest --collect-only -q` → 490 tests confirmed

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` accumulated decisions log — architectural patterns and critical pitfalls documented per-phase

### Tertiary (LOW confidence)
- None — all findings from codebase inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all from existing minilegion source code
- Architecture: HIGH — patterns verified from all 8 existing commands
- Pitfalls: HIGH — derived from explicit warnings in STATE.md decision log and test fixture inspection
- Coherence check logic: MEDIUM — field names verified from schemas.py; exact matching semantics are implementation choices to be decided in planning

**Research date:** 2026-03-10
**Valid until:** Until schemas.py, state.py, preflight.py, or renderer.py are modified (this is a stable, near-complete codebase)
