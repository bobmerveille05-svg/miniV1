# Phase 7: Design Stage - Research

**Researched:** 2026-03-10
**Domain:** Python CLI command wiring — replace `_pipeline_stub(Stage.DESIGN)` with full implementation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Design Command Flow
- `design()` command in `commands.py` follows the exact same pattern as `research()`:
  `find_project_dir()` → `load_config(project_dir.parent)` → `load_state()` → `StateMachine` → `can_transition(Stage.DESIGN)` guard → `check_preflight(Stage.DESIGN, project_dir)` → read inputs → render prompt → LLM call → `validate_with_retry` → `save_dual` → `approve_design` → transition state
- Artifact name for `validate_with_retry`: `"design"` (already in `SCHEMA_REGISTRY`)
- Output files: `DESIGN.json` and `DESIGN.md` in `project_dir/`
- On approval: `sm.transition(Stage.DESIGN)`, `state.current_stage = Stage.DESIGN.value`, `state.add_history("design", "Design completed and approved")`, `save_state()`
- Rejection: yellow message, exit 0 (same as brief/research pattern)
- LLM/preflight error: red message, exit 1

#### Prompt Variable Wiring
- Designer prompt (`designer.md`) uses three USER_TEMPLATE variables: `{{project_name}}`, `{{brief_content}}`, `{{research_json}}`
- `{{focus_files_content}}` is also present in the template but the actual files content is currently out of scope — Phase 7 passes a placeholder or empty string for `focus_files_content`
- `project_name = project_dir.parent.name` (same as research command)
- `brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")`
- `research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")` — raw JSON string passed as-is
- `focus_files_content = "(Focus file reading deferred to Phase 9)"` — placeholder string, not empty (avoids unresolved placeholder crash in render_prompt)

#### DesignSchema Validation
- `DesignSchema` already fully defined in `schemas.py` — no changes needed
- `ArchitectureDecision.alternatives_rejected` is `list[str]` with `default_factory=list` — schema does NOT enforce non-empty at the Pydantic level
- DSGN-03 requirement ("at least 1 rejected alternative per decision") is enforced by the designer prompt instruction, NOT by a schema validator
- Decision: do NOT add Pydantic validator for `alternatives_rejected` non-empty in Phase 7 — the prompt instruction is the enforcement mechanism; schema validator would be too strict for tests
- `DesignSchema` registry key: `"design"` — already registered in `registry.py`

#### Imports Needed in commands.py
- Add to imports: `approve_design` from `minilegion.core.approval`
- `save_dual`, `load_config`, `OpenAIAdapter`, `validate_with_retry`, `check_preflight`, `load_prompt`, `render_prompt` all already imported

#### No New Modules
- Phase 7 is purely a wiring phase, like Phase 6
- No new Python modules needed — all infrastructure is in place
- Only files modified: `minilegion/cli/commands.py` (replace stub), `tests/test_cli_design.py` (new test file)

#### Error Handling & UX
- `check_preflight(Stage.DESIGN, project_dir)` checks for `BRIEF.md`, `RESEARCH.json`, `brief_approved`, `research_approved` — already declared in `preflight.py`
- PreflightError → red message, exit 1
- ApprovalError caught before MiniLegionError (subclass ordering — same as brief/research)

### OpenCode's Discretion

- Test file is `tests/test_cli_design.py` (separate from `test_cli_brief_research.py`)
- Test setup helper `_write_research_state(project_ai_dir)` writes STATE.json at `research` stage with `brief_approved: True` and `research_approved: True`, plus creates `BRIEF.md` and `RESEARCH.json`
- Mock `validate_with_retry` at `minilegion.cli.commands.validate_with_retry`
- Mock `approve_design` at `minilegion.core.approval.typer.confirm`

### Deferred Ideas (OUT OF SCOPE)

- Reading actual focus files from the filesystem (referenced in `recommended_focus_files` from RESEARCH.json) — deferred to Phase 9 (Execute stage)
- Adding a Pydantic validator that enforces `alternatives_rejected` is non-empty — deferred; prompt enforcement is sufficient for Phase 7
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSGN-01 | Designer role receives BRIEF.md + RESEARCH.json + recommended focus files and produces DESIGN.json + DESIGN.md | Wiring `research_json` + `brief_content` into designer prompt; `save_dual()` already dispatches to `render_design_md` |
| DSGN-02 | DESIGN.json contains: design_approach, architecture_decisions (with alternatives_rejected), components (with files), data_models, api_contracts, integration_points, design_patterns_used, conventions_to_follow, technical_risks, out_of_scope, test_strategy, estimated_complexity | `DesignSchema` (12 fields) already fully defined in `schemas.py` — validated by `validate_with_retry("design", ...)` |
| DSGN-03 | Each architecture decision must have at least 1 rejected alternative | Enforced by `designer.md` SYSTEM prompt instruction ("MUST include at least one entry in alternatives_rejected") — not by Pydantic validator (locked decision) |
| DSGN-04 | conventions_to_follow must reference conventions from RESEARCH.json | Enforced by `designer.md` USER_TEMPLATE injecting raw `{{research_json}}` — LLM reads `existing_conventions` and produces `conventions_to_follow` accordingly |
| DSGN-05 | Designer prompt enforces "design, don't plan" — no task decomposition | Already in `designer.md` SYSTEM: "Do NOT decompose into tasks or write implementation steps — design, don't plan" |
</phase_requirements>

---

## Summary

Phase 7 is a **pure wiring phase** — all infrastructure is already in place from Phases 1–6. The entire scope is replacing `_pipeline_stub(Stage.DESIGN)` (1 line in `commands.py`) with a ~50-line `design()` implementation that mirrors the `research()` command verbatim, substituting DESIGN-specific calls.

The `research()` command (lines 236–324 of `commands.py`) is the **canonical template**. Every structural element — config loading, transition guard, preflight, prompt rendering, LLM call, validate_with_retry, save_dual, approval gate, state transition — already exists and is battle-tested. Phase 7 applies the same assembly to the design slot.

The only non-trivial decision already resolved: `{{focus_files_content}}` placeholder receives a literal string `"(Focus file reading deferred to Phase 9)"` rather than empty string, because `render_prompt()` detects unresolved placeholders and crashes on empty.

**Primary recommendation:** Copy `research()` from `commands.py`, replace 6 strings (`RESEARCH`→`DESIGN`, `research`→`design`, `scan_codebase` call removed, `RESEARCH.json`→`DESIGN.json`, `RESEARCH.md`→`DESIGN.md`, `approve_research`→`approve_design`, add `focus_files_content` placeholder), and write 10 parallel tests in `test_cli_design.py` matching the `TestResearchCommand` structure.

---

## Standard Stack

### Core (all already installed — no new dependencies)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| typer | existing | CLI framework + `typer.confirm()` approval gate | Already used |
| pydantic | existing | `DesignSchema` validation via `validate_with_retry` | Already used |
| pytest | existing | Test framework | Already used |

### No new packages required
Phase 7 adds zero new dependencies. All imports already present in `commands.py` except `approve_design`.

**Installation:** None required.

---

## Architecture Patterns

### The Research() Template (canonical pattern for design())

The `research()` command (lines 236–324 of `commands.py`) is the **exact template** to follow:

```python
# Source: minilegion/cli/commands.py lines 236-324

@app.command()
def research() -> None:
    """Run the research stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.RESEARCH):
            typer.echo(typer.style(f"Cannot transition ...", fg=typer.colors.RED))
            raise typer.Exit(code=1)

        config = load_config(project_dir.parent)          # ← PARENT, not project_dir
        check_preflight(Stage.RESEARCH, project_dir)

        # ... read inputs, render prompt ...

        adapter = OpenAIAdapter(config)                   # ← full config object

        def llm_call(prompt: str) -> str:
            response = adapter.call_for_json(system_prompt, prompt)
            return response.content

        research_data = validate_with_retry(              # ← 5 positional args
            llm_call, user_message, "research", config, project_dir
        )

        save_dual(research_data, project_dir / "RESEARCH.json", project_dir / "RESEARCH.md")
        typer.echo(typer.style("RESEARCH.json + RESEARCH.md saved.", fg=typer.colors.GREEN))

        research_md = (project_dir / "RESEARCH.md").read_text(encoding="utf-8")
        approve_research(state, project_dir / "STATE.json", research_md)  # ← WRITE BEFORE GATE

        sm.transition(Stage.RESEARCH)
        state.current_stage = Stage.RESEARCH.value        # ← MANUAL SYNC (critical)
        state.add_history("research", "Research completed and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(typer.style("Research approved. Stage: research", fg=typer.colors.GREEN))

    except ApprovalError:                                  # ← BEFORE MiniLegionError
        typer.echo(typer.style("Research rejected. Stage unchanged.", fg=typer.colors.YELLOW))
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

### Design Command Delta from Research

```python
# What changes when adapting research() → design():

# 1. Stage references:  Stage.RESEARCH  →  Stage.DESIGN
# 2. Config load:       SAME (load_config(project_dir.parent))
# 3. Preflight:         check_preflight(Stage.DESIGN, project_dir)  ← same call, different stage
# 4. No scan_codebase:  REMOVED (design reads files, not scanner output)
# 5. Prompt load:       load_prompt("designer")  ← was "researcher"
# 6. Prompt variables:  project_name, brief_content, research_json, focus_files_content
#    research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")
#    focus_files_content = "(Focus file reading deferred to Phase 9)"
# 7. LLM artifact:      "design"  ← was "research"
# 8. Output files:      DESIGN.json + DESIGN.md  ← was RESEARCH.json + RESEARCH.md
# 9. Approval gate:     approve_design(state, state_path, design_md)  ← was approve_research
# 10. History entry:    "Design completed and approved"
# 11. State messages:   "Design approved. Stage: design"
# 12. Rejection msg:    "Design rejected. Stage unchanged."
```

### Prompt Variable Wiring (designer.md)
```python
# Source: minilegion/prompts/designer.md USER_TEMPLATE variables

system_prompt, user_template = load_prompt("designer")
project_name = project_dir.parent.name
brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")
focus_files_content = "(Focus file reading deferred to Phase 9)"

user_message = render_prompt(
    user_template,
    project_name=project_name,
    brief_content=brief_content,
    research_json=research_json,
    focus_files_content=focus_files_content,
)
```

### Import Change Required
```python
# BEFORE (line 15 of commands.py):
from minilegion.core.approval import ApprovalError, approve_brief, approve_research

# AFTER:
from minilegion.core.approval import ApprovalError, approve_brief, approve_research, approve_design
```

### Anti-Patterns to Avoid
- **Calling `load_config(project_dir)` instead of `load_config(project_dir.parent)`:** `load_config()` internally appends `project-ai/` — passing `project_dir` (already `…/project-ai/`) results in path `…/project-ai/project-ai/minilegion.config.json` which doesn't exist.
- **Catching `MiniLegionError` before `ApprovalError`:** `ApprovalError` is a subclass of `MiniLegionError` — wrong order silently catches rejections as errors (exit 1 instead of exit 0).
- **`approve_design()` before `save_dual()`:** Write-before-gate principle — artifacts must be persisted before the approval prompt so they exist on disk even on rejection.
- **Missing `state.current_stage = Stage.DESIGN.value`:** The `sm.transition()` call updates the StateMachine internal state, but NOT the `ProjectState.current_stage` field. Manual sync is required before `save_state()`.
- **Empty `focus_files_content`:** `render_prompt()` detects unresolved `{{placeholder}}` patterns and raises. Pass the placeholder string, not `""`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON validation with retry | Custom loop | `validate_with_retry(llm_call, prompt, "design", config, project_dir)` | Already handles fixup pipeline, retry feedback, RAW_DEBUG capture |
| Dual file save (JSON + MD) | Two `write_atomic()` calls | `save_dual(design_data, project_dir / "DESIGN.json", project_dir / "DESIGN.md")` | Already dispatches to `render_design_md` via `_RENDERERS["DesignSchema"]` |
| Preflight validation | Custom file/approval checks | `check_preflight(Stage.DESIGN, project_dir)` | Already declares BRIEF.md + RESEARCH.json + both approvals as requirements |
| Approval gate with state persistence | Custom `typer.confirm()` + state write | `approve_design(state, project_dir / "STATE.json", design_md)` | Already handles confirm + state.approvals mutation + save_state |
| Prompt loading and variable injection | String formatting | `load_prompt("designer")` + `render_prompt(template, **vars)` | Already handles `<!-- SYSTEM -->` / `<!-- USER_TEMPLATE -->` splitting and `{{placeholder}}` substitution |

---

## Common Pitfalls

### Pitfall 1: `load_config(project_dir)` vs `load_config(project_dir.parent)`
**What goes wrong:** `FileNotFoundError` or `ConfigError` at startup — config file not found.
**Why it happens:** `find_project_dir()` returns `…/myproject/project-ai/`. `load_config()` appends `project-ai/minilegion.config.json` internally, so the correct call is `load_config(project_dir.parent)` → `…/myproject/project-ai/minilegion.config.json`.
**How to avoid:** Always pass `.parent` of the path returned by `find_project_dir()`.
**Warning signs:** Test output contains "config" or "json" in error + exit code 1.

### Pitfall 2: Exception Ordering (`MiniLegionError` before `ApprovalError`)
**What goes wrong:** Rejection exits with code 1 and shows red error text instead of yellow "rejected" message with exit 0.
**Why it happens:** `ApprovalError` subclasses `MiniLegionError`. Python `except` clauses match the first compatible handler — if `MiniLegionError` is listed first, it catches `ApprovalError` before the dedicated handler.
**How to avoid:** Always `except ApprovalError:` FIRST, then `except MiniLegionError:`.
**Warning signs:** `test_design_rejection_exits_0` fails with exit code 1.

### Pitfall 3: Missing Manual `state.current_stage` Sync
**What goes wrong:** `STATE.json` written to disk has `current_stage` = old value (e.g., `"research"`) instead of `"design"`.
**Why it happens:** `sm.transition()` updates the `StateMachine` internal state object, but `state: ProjectState` is a separate object. Only `save_state(state, ...)` writes to disk, and `state.current_stage` is not automatically updated by the StateMachine.
**How to avoid:** `state.current_stage = Stage.DESIGN.value` immediately after `sm.transition(Stage.DESIGN)`, before `save_state()`.
**Warning signs:** `test_design_state_current_stage_is_design_after_approval` fails.

### Pitfall 4: `approve_design()` Called Before `save_dual()`
**What goes wrong:** Rejection leaves no `DESIGN.json`/`DESIGN.md` artifacts on disk.
**Why it happens:** Write-before-gate principle — artifacts should persist even when the user rejects at the approval prompt (for debugging, re-review etc.).
**How to avoid:** `save_dual(...)` → `typer.echo(...)` → then `approve_design(...)`.
**Warning signs:** `test_design_writes_atomically_before_approval` fails.

### Pitfall 5: Empty `focus_files_content`
**What goes wrong:** `render_prompt()` raises an error about unresolved placeholders.
**Why it happens:** `render_prompt()` uses `re.sub` with detection of remaining `{{…}}` patterns after substitution. An empty string passed for `focus_files_content` still leaves `{{focus_files_content}}` in the template if not explicitly substituted.
**How to avoid:** Pass `focus_files_content="(Focus file reading deferred to Phase 9)"` — a non-empty placeholder string.
**Warning signs:** `ValidationError` or `render_prompt` exception in test output.

### Pitfall 6: Mocking `validate_with_retry` at Wrong Namespace
**What goes wrong:** Mock doesn't intercept calls — real LLM call attempted, tests fail with API errors or import errors.
**Why it happens:** `commands.py` does `from minilegion.core.retry import validate_with_retry` — the name is bound in the `minilegion.cli.commands` namespace. Mocking `minilegion.core.retry.validate_with_retry` patches the origin but not the already-imported name.
**How to avoid:** Always mock at `minilegion.cli.commands.validate_with_retry` (where the name is used), not at the source module.
**Warning signs:** Tests try to make real HTTP calls or raise `ConfigError` about missing API key.

---

## Code Examples

### Complete design() Command
```python
# Source: adapted from research() at minilegion/cli/commands.py lines 236-324

@app.command()
def design() -> None:
    """Run the design stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.DESIGN):
            typer.echo(
                typer.style(
                    f"Cannot transition from {state.current_stage} to {Stage.DESIGN.value}",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(code=1)

        config = load_config(project_dir.parent)
        check_preflight(Stage.DESIGN, project_dir)

        system_prompt, user_template = load_prompt("designer")
        project_name = project_dir.parent.name
        brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
        research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")
        focus_files_content = "(Focus file reading deferred to Phase 9)"
        user_message = render_prompt(
            user_template,
            project_name=project_name,
            brief_content=brief_content,
            research_json=research_json,
            focus_files_content=focus_files_content,
        )

        typer.echo("Running designer...")
        adapter = OpenAIAdapter(config)

        def llm_call(prompt: str) -> str:
            response = adapter.call_for_json(system_prompt, prompt)
            return response.content

        design_data = validate_with_retry(
            llm_call, user_message, "design", config, project_dir
        )

        save_dual(
            design_data, project_dir / "DESIGN.json", project_dir / "DESIGN.md"
        )
        typer.echo(
            typer.style("DESIGN.json + DESIGN.md saved.", fg=typer.colors.GREEN)
        )

        design_md = (project_dir / "DESIGN.md").read_text(encoding="utf-8")
        approve_design(state, project_dir / "STATE.json", design_md)

        sm.transition(Stage.DESIGN)
        state.current_stage = Stage.DESIGN.value  # CRITICAL: sync ProjectState manually
        state.add_history("design", "Design completed and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(
            typer.style("Design approved. Stage: design", fg=typer.colors.GREEN)
        )

    except ApprovalError:
        typer.echo(
            typer.style("Design rejected. Stage unchanged.", fg=typer.colors.YELLOW)
        )
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

### Test Setup Helper (`_write_research_state`)
```python
# Source: derived from _write_brief_state pattern in test_cli_brief_research.py

VALID_DESIGN = {
    "design_approach": "Modular architecture",
    "architecture_decisions": [
        {
            "decision": "Use Pydantic",
            "rationale": "Type safety",
            "alternatives_rejected": ["dataclasses"],
        }
    ],
    "components": [
        {"name": "Core", "description": "Core logic", "files": ["minilegion/core/"]}
    ],
    "data_models": ["ProjectState"],
    "api_contracts": [],
    "integration_points": [],
    "design_patterns_used": ["Repository"],
    "conventions_to_follow": ["snake_case"],
    "technical_risks": [],
    "out_of_scope": [],
    "test_strategy": "pytest unit tests",
    "estimated_complexity": "medium",
}


def _write_research_state(project_ai: Path) -> None:
    """Create STATE.json at research stage with both approvals True."""
    state_data = {
        "current_stage": "research",
        "approvals": {
            "brief_approved": True,
            "research_approved": True,
            "design_approved": False,
            "plan_approved": False,
            "execute_approved": False,
            "review_approved": False,
        },
        "completed_tasks": [],
        "history": [],
        "metadata": {},
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
    (project_ai / "BRIEF.md").write_text(
        "# Project Brief\n\n## Overview\n\nTest brief.\n", encoding="utf-8"
    )
    (project_ai / "RESEARCH.json").write_text(
        '{"project_overview": "test", "tech_stack": [], "architecture_patterns": [],'
        ' "relevant_files": [], "existing_conventions": [], "dependencies_map": {},'
        ' "potential_impacts": [], "constraints": [], "assumptions_verified": [],'
        ' "open_questions": [], "recommended_focus_files": []}',
        encoding="utf-8",
    )
```

### Test Mocking Pattern (10 tests — mirrors TestResearchCommand exactly)
```python
# Source: adapted from TestResearchCommand in test_cli_brief_research.py

class TestDesignCommand:
    def _mock_all(self, monkeypatch, *, approve=True, fail_llm=False):
        """Shared mock setup for design command tests."""
        from minilegion.core.schemas import DesignSchema
        mock_design = DesignSchema(**VALID_DESIGN)

        monkeypatch.setattr("minilegion.cli.commands.check_preflight", lambda s, pd: None)
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Design {{project_name}} {{brief_content}} {{research_json}} {{focus_files_content}}",
            ),
        )
        if fail_llm:
            from minilegion.core.exceptions import LLMError
            monkeypatch.setattr(
                "minilegion.cli.commands.validate_with_retry",
                lambda *a, **kw: (_ for _ in ()).throw(LLMError("API error")),
            )
        else:
            monkeypatch.setattr(
                "minilegion.cli.commands.validate_with_retry",
                lambda *a, **kw: mock_design,
            )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm",
            lambda *a, **kw: approve,
        )
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed) |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `python -m pytest tests/test_cli_design.py -v` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test ID | Test Type | Automated Command |
|--------|----------|---------|-----------|-------------------|
| DSGN-01 | design() calls check_preflight(Stage.DESIGN, ...) | `test_design_calls_preflight` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_calls_preflight -v` |
| DSGN-01 | design() calls validate_with_retry with "design" artifact name | `test_design_calls_llm` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_calls_llm -v` |
| DSGN-01 | design() writes DESIGN.json + DESIGN.md to project-ai/ | `test_design_saves_dual_output` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_saves_dual_output -v` |
| DSGN-01 | PreflightError exits with code 1 and red message | `test_design_preflight_failure_exits_1` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_preflight_failure_exits_1 -v` |
| DSGN-01 | LLM error exits with code 1 | `test_design_llm_error_exits_1` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_llm_error_exits_1 -v` |
| DSGN-01 | design() writes files BEFORE approval gate | `test_design_writes_atomically_before_approval` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_writes_atomically_before_approval -v` |
| DSGN-02 | Approved design transitions STATE.json to "design" with design_approved=True | `test_design_approval_accepted_transitions_state` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_approval_accepted_transitions_state -v` |
| DSGN-02 | state.current_stage is "design" in STATE.json after approval (sync gap) | `test_design_state_current_stage_is_design_after_approval` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_state_current_stage_is_design_after_approval -v` |
| APRV-03 | Rejection exits 0, yellow message, stage unchanged | `test_design_rejection_exits_0` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_rejection_exits_0 -v` |
| APRV-06 | Rejected design leaves STATE.json current_stage as "research" | `test_design_rejection_leaves_state_unchanged` | unit | `python -m pytest tests/test_cli_design.py::TestDesignCommand::test_design_rejection_leaves_state_unchanged -v` |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_cli_design.py -v`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green (431 + 10 = 441 expected) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli_design.py` — covers DSGN-01..05 + APRV-03/06 (10 tests)

*(All other infrastructure exists. No framework install needed — pytest already configured.)*

---

## Implementation Plan Structure

### Single-Wave Approach (Phase 7 = 1 Plan, 2 Tasks)

Phase 7 is small enough for a **single plan file** with 2 tightly coupled tasks:

**Task 1: Wire `design()` command in `commands.py`**
- Add `approve_design` to imports on line 15
- Replace `_pipeline_stub(Stage.DESIGN)` stub body with full implementation
- Files: `minilegion/cli/commands.py`

**Task 2: Write `tests/test_cli_design.py`**
- 10 tests mirroring `TestResearchCommand` structure from `test_cli_brief_research.py`
- Uses `_write_research_state()` helper, `VALID_DESIGN` fixture, `monkeypatch`-based mocks
- Files: `tests/test_cli_design.py`

**Verification:** `python -m pytest tests/ -v` → 441 tests GREEN (431 existing + 10 new)

**Rationale for single plan:** Both tasks are interdependent (tests validate the command), and the delta is small (~60 lines of production code + ~200 lines of tests). No need to split across waves.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `_pipeline_stub(Stage.DESIGN)` | Full `design()` implementation | Phase 7 replaces the stub |
| `approve_brief, approve_research` imported | Add `approve_design` to same import | One import line edit |

---

## Open Questions

1. **Does `minilegion.config.json` need to exist for tests?**
   - What we know: `load_config(project_dir.parent)` is called in the real command, but tests mock it out with `monkeypatch`
   - What's unclear: Does the CliRunner `tmp_path` setup need a `minilegion.config.json` file for `load_config` to succeed, or is it mocked via the entire command flow?
   - Recommendation: Looking at `_write_brief_state()` pattern in `test_cli_brief_research.py` — it does NOT create `minilegion.config.json`. The `validate_with_retry` mock is applied at `minilegion.cli.commands.validate_with_retry`, which means `OpenAIAdapter` and `load_config` are still called. However, the research tests pass without a config file — this means either `load_config` has a default fallback or tests mock more broadly. **Verdict:** Follow the exact same mock pattern as research tests (mock `check_preflight` and `validate_with_retry`, let `load_config` use defaults) — the research tests work this way at 431 passing.

2. **Does `DESIGN.md` need to exist for `approve_design()` to work in tests?**
   - What we know: `approve_design(state, state_path, design_md)` takes the design summary as a string parameter (not a path). The actual MD text is read from `DESIGN.md` after `save_dual()` writes it.
   - Recommendation: For tests that use real `save_dual()` (not mocked), `DESIGN.md` will be created by `save_dual()` before `approve_design()` is called. For tests mocking `save_dual`, manually create `DESIGN.md` in the test (same pattern as research tests: `(project_ai / "RESEARCH.md").write_text(...)`).

---

## Sources

### Primary (HIGH confidence)
- `minilegion/cli/commands.py` lines 236–324 — `research()` canonical template, directly inspected
- `minilegion/core/approval.py` — `approve_design` signature verified: `(state, state_path, design_summary) -> bool`
- `minilegion/core/schemas.py` — `DesignSchema` 12 fields confirmed, `ArchitectureDecision.alternatives_rejected` = `list[str]` with `default_factory=list`
- `minilegion/core/preflight.py` — `REQUIRED_FILES[Stage.DESIGN]` = `["BRIEF.md", "RESEARCH.json"]`, `REQUIRED_APPROVALS[Stage.DESIGN]` = `["brief_approved", "research_approved"]`
- `minilegion/prompts/designer.md` — 4 template variables confirmed: `{{project_name}}`, `{{brief_content}}`, `{{research_json}}`, `{{focus_files_content}}`
- `minilegion/core/renderer.py` — `render_design_md` + `_RENDERERS["DesignSchema"]` dispatch confirmed
- `tests/test_cli_brief_research.py` — `TestResearchCommand` (11 tests) is the direct analog; mock patterns extracted

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — confirms 431 tests GREEN at Phase 6 completion
- `.planning/phases/07-design-stage/07-CONTEXT.md` — all implementation decisions already resolved

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all infrastructure already in codebase, directly verified
- Architecture: HIGH — `research()` template read directly, all function signatures confirmed
- Pitfalls: HIGH — derived from `STATE.md` documented decisions + code inspection of actual exception hierarchy
- Test strategy: HIGH — directly modeled on existing 11 `TestResearchCommand` tests

**Research date:** 2026-03-10
**Valid until:** 2026-06-10 (stable — pure internal pattern replication, no external dependencies)
