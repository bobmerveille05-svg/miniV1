# Phase 7: Design Stage - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the `design` CLI command: replace the `_pipeline_stub(Stage.DESIGN)` call with a full implementation that reads `RESEARCH.json` + `BRIEF.md`, scans focus files from the filesystem, renders the designer prompt, calls the LLM via `OpenAIAdapter`, validates and saves `DESIGN.json` + `DESIGN.md`, and gates state transition on `approve_design()`. This phase does NOT implement the plan or execute stages.

</domain>

<decisions>
## Implementation Decisions

### Design Command Flow
- `design()` command in `commands.py` follows the exact same pattern as `research()`:
  `find_project_dir()` → `load_config(project_dir.parent)` → `load_state()` → `StateMachine` → `can_transition(Stage.DESIGN)` guard → `check_preflight(Stage.DESIGN, project_dir)` → read inputs → render prompt → LLM call → `validate_with_retry` → `save_dual` → `approve_design` → transition state
- Artifact name for `validate_with_retry`: `"design"` (already in `SCHEMA_REGISTRY`)
- Output files: `DESIGN.json` and `DESIGN.md` in `project_dir/`
- On approval: `sm.transition(Stage.DESIGN)`, `state.current_stage = Stage.DESIGN.value`, `state.add_history("design", "Design completed and approved")`, `save_state()`
- Rejection: yellow message, exit 0 (same as brief/research pattern)
- LLM/preflight error: red message, exit 1

### Prompt Variable Wiring
- Designer prompt (`designer.md`) uses three USER_TEMPLATE variables: `{{project_name}}`, `{{brief_content}}`, `{{research_json}}`
- `{{focus_files_content}}` is also present in the template but the actual files content is currently out of scope — Phase 7 passes a placeholder or empty string for `focus_files_content`
- `project_name = project_dir.parent.name` (same as research command)
- `brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")`
- `research_json = (project_dir / "RESEARCH.json").read_text(encoding="utf-8")` — raw JSON string passed as-is
- `focus_files_content = "(Focus file reading deferred to Phase 9)"` — placeholder string, not empty (avoids unresolved placeholder crash in render_prompt)

### DesignSchema Validation
- `DesignSchema` already fully defined in `schemas.py` — no changes needed
- `ArchitectureDecision.alternatives_rejected` is `list[str]` with `default_factory=list` — schema does NOT enforce non-empty at the Pydantic level
- DSGN-03 requirement ("at least 1 rejected alternative per decision") is enforced by the designer prompt instruction, NOT by a schema validator
- Decision: do NOT add Pydantic validator for `alternatives_rejected` non-empty in Phase 7 — the prompt instruction is the enforcement mechanism; schema validator would be too strict for tests
- `DesignSchema` registry key: `"design"` — already registered in `registry.py`

### Imports Needed in commands.py
- Add to imports: `approve_design` from `minilegion.core.approval`
- `save_dual`, `load_config`, `OpenAIAdapter`, `validate_with_retry`, `check_preflight`, `load_prompt`, `render_prompt` all already imported

### No New Modules
- Phase 7 is purely a wiring phase, like Phase 6
- No new Python modules needed — all infrastructure is in place
- Only files modified: `minilegion/cli/commands.py` (replace stub), `tests/test_cli_design.py` (new test file)

### Error Handling & UX
- `check_preflight(Stage.DESIGN, project_dir)` checks for `BRIEF.md`, `RESEARCH.json`, `brief_approved`, `research_approved` — already declared in `preflight.py`
- PreflightError → red message, exit 1
- ApprovalError caught before MiniLegionError (subclass ordering — same as brief/research)

</decisions>

<code_context>
## Existing Code Insights

### Already In Place (no changes needed)
- `DesignSchema` in `schemas.py` — 12 fields, fully defined
- `approve_design(state, state_path, design_summary)` in `approval.py` — ready to use
- `render_design_md(data: DesignSchema)` in `renderer.py` — fully implemented
- `save_dual()` dispatches to `render_design_md` via `_RENDERERS["DesignSchema"]`
- `check_preflight(Stage.DESIGN, ...)` in `preflight.py` — requires BRIEF.md + RESEARCH.json + brief_approved + research_approved
- `validate_with_retry(..., "design", ...)` — "design" key in SCHEMA_REGISTRY
- `designer.md` prompt in `prompts/` — SYSTEM + USER_TEMPLATE sections present
- `load_prompt("designer")` works via `importlib.resources.files()`

### Critical Patterns (from Phase 6)
- `load_config(project_dir.parent)` — parent of project-ai, NOT project-ai itself
- `OpenAIAdapter(config)` — full config object, not kwargs
- `validate_with_retry(llm_call, user_message, "design", config, project_dir)` — 5 args, 4th is MiniLegionConfig
- `state.current_stage = Stage.DESIGN.value` before `save_state()` — sync gap fix
- `ApprovalError` caught before `MiniLegionError`

### designer.md Variables
- `{{project_name}}` → `project_dir.parent.name`
- `{{brief_content}}` → `(project_dir / "BRIEF.md").read_text(encoding="utf-8")`
- `{{research_json}}` → `(project_dir / "RESEARCH.json").read_text(encoding="utf-8")`
- `{{focus_files_content}}` → placeholder string (deferred — no file reading in Phase 7)

</code_context>

<specifics>
## Specific Ideas

- The test file should be `tests/test_cli_design.py` (separate from `test_cli_brief_research.py`)
- Test setup helper `_write_research_state(project_ai_dir)` writes STATE.json at `research` stage with `brief_approved: True` and `research_approved: True`, plus creates `BRIEF.md` and `RESEARCH.json` in `project_ai_dir`
- Mock `validate_with_retry` at `minilegion.cli.commands.validate_with_retry` for test isolation
- Mock `approve_design` at `minilegion.core.approval.typer.confirm` (same pattern as brief/research tests)
- Valid DesignSchema dict for test mocks:
  ```python
  VALID_DESIGN = {
      "design_approach": "Modular architecture",
      "architecture_decisions": [{"decision": "Use Pydantic", "rationale": "Type safety", "alternatives_rejected": ["dataclasses"]}],
      "components": [{"name": "Core", "description": "Core logic", "files": ["minilegion/core/"]}],
      "data_models": ["ProjectState"],
      "api_contracts": [],
      "integration_points": [],
      "design_patterns_used": ["Repository"],
      "conventions_to_follow": ["snake_case"],
      "technical_risks": [],
      "out_of_scope": [],
      "test_strategy": "pytest unit tests",
      "estimated_complexity": "medium"
  }
  ```

</specifics>

<deferred>
## Deferred Ideas

- Reading actual focus files from the filesystem (referenced in `recommended_focus_files` from RESEARCH.json) — deferred to Phase 9 (Execute stage)
- Adding a Pydantic validator that enforces `alternatives_rejected` is non-empty — deferred; prompt enforcement is sufficient for Phase 7

</deferred>

---

*Phase: 07-design-stage*
*Context gathered: 2026-03-10*
