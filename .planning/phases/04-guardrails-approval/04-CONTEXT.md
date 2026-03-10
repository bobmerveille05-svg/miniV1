# Phase 4: Guardrails & Approval Gates - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Pre-flight checks that validate required files and approvals exist before any LLM call, scope lock that mechanically checks patch file lists against allowed files, path normalization for cross-platform safety, and 5 human approval gates (brief, research, design, plan, patch) that block state transitions on rejection. This phase delivers the safety layer between the adapter (Phase 3) and the pipeline stages (Phases 6-10). It does NOT implement pipeline stages — it builds the guardrail functions and approval prompts that pipeline stages will call.

</domain>

<decisions>
## Implementation Decisions

### Pre-flight Check Architecture
- Pre-flight module in `minilegion/core/preflight.py` with a `check_preflight(stage: Stage, project_dir: Path) -> None` function
- Uses a declarative mapping: each stage maps to a list of required files and required approvals
- Required files mapping:
  - `research`: requires `BRIEF.md`
  - `design`: requires `BRIEF.md`, `RESEARCH.json`
  - `plan`: requires `BRIEF.md`, `RESEARCH.json`, `DESIGN.json`
  - `execute`: requires `BRIEF.md`, `RESEARCH.json`, `DESIGN.json`, `PLAN.json`
  - `review`: requires `BRIEF.md`, `RESEARCH.json`, `DESIGN.json`, `PLAN.json`, `EXECUTION_LOG.json`
- Required approvals mapping:
  - `research`: requires `brief_approved`
  - `design`: requires `brief_approved`, `research_approved`
  - `plan`: requires `brief_approved`, `research_approved`, `design_approved`
  - `execute`: requires `brief_approved`, `research_approved`, `design_approved`, `plan_approved`
  - `review`: requires `brief_approved`, `research_approved`, `design_approved`, `plan_approved`, `execute_approved`
- Missing file raises `PreflightError` naming the missing file
- Missing approval raises `PreflightError` naming the missing approval key
- All required files are checked relative to `project-ai/` directory
- Pre-flight check loads current `ProjectState` from `STATE.json` for approval checks

### Scope Lock
- Scope lock module in `minilegion/core/scope_lock.py` with `check_scope(changed_files: list[str], allowed_files: list[str]) -> list[str]` function
- Returns list of out-of-scope files (empty = all in scope)
- All paths are normalized before comparison using `normalize_path()`
- Raises `ValidationError` if any files are out of scope (with list of violating files)
- Separate convenience function `validate_scope(changed_files, allowed_files) -> None` that raises on violation

### Path Normalization
- `normalize_path(path: str) -> str` function in `minilegion/core/scope_lock.py` (co-located with scope lock)
- Resolves `./` prefix, strips trailing slashes, normalizes OS separators to forward slashes
- Lowercases on Windows for case-insensitive comparison
- Does NOT resolve symlinks or absolute paths — works with relative project paths only

### Approval Gates
- Approval module in `minilegion/core/approval.py`
- `approve(gate_name: str, summary: str, state: ProjectState, state_path: Path) -> bool` function
- Displays summary text, then prompts user with Y/N via `typer.confirm()`
- On approval: sets `state.approvals[gate_name] = True`, adds history entry, saves state atomically, returns `True`
- On rejection: does NOT modify state at all (byte-identical), raises `ApprovalError` with gate name
- 5 gate functions that call `approve()` with appropriate summaries:
  - `approve_brief(state, state_path, brief_content) -> bool`
  - `approve_research(state, state_path, research_summary) -> bool`
  - `approve_design(state, state_path, design_summary) -> bool`
  - `approve_plan(state, state_path, plan_summary) -> bool`
  - `approve_patch(state, state_path, diff_text) -> bool`
- Each gate function formats a human-readable summary from the artifact content before calling `approve()`

### Integration Pattern
- Pipeline stages (Phases 6-10) will call `check_preflight()` before making any LLM call
- Pipeline stages will call `approve_*()` after producing each artifact
- Scope lock is called by the execute stage after builder produces patches, before applying them
- Pre-flight and approval are independent — pre-flight is a passive check, approval is an interactive gate

### OpenCode's Discretion
- Exact summary formatting for each approval gate display
- Internal helper functions for path normalization edge cases
- Test fixture organization for approval gate testing (mocking typer.confirm)
- Whether to use a dataclass or plain dict for the pre-flight requirements mapping

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ProjectState` (core/state.py): Has `approvals` dict with 6 keys (brief_approved, research_approved, etc.)
- `save_state()` / `load_state()` (core/state.py): Atomic state persistence
- `Stage` enum (core/state.py): Pipeline stages for pre-flight mapping
- `PreflightError` (core/exceptions.py): Already exists for pre-flight check failures
- `ApprovalError` (core/exceptions.py): Already exists for approval gate rejections
- `ValidationError` (core/exceptions.py): For scope lock violations
- `write_atomic()` (core/file_io.py): For any file writes needed
- `StateMachine` (core/state.py): Can check `can_transition()` — pre-flight is a more granular check
- `APPROVAL_KEYS` (core/state.py): List of approval key names

### Established Patterns
- Exception wrapping: `raise PreflightError(...) from exc` or direct raises
- `Stage(str, Enum)` for stage values — can use stage.value for file/approval mapping keys
- Pydantic `BaseModel` for data models
- `write_atomic()` for all file writes

### Integration Points
- `core/state.py` provides ProjectState, save_state, load_state, Stage, APPROVAL_KEYS
- `core/exceptions.py` provides PreflightError, ApprovalError, ValidationError
- `cli/commands.py` has `_pipeline_stub()` — future phases will replace stubs with preflight+LLM+approval
- `typer` already a dependency — `typer.confirm()` available for Y/N prompts

</code_context>

<specifics>
## Specific Ideas

- GUARD-01 through GUARD-05 specify pre-flight checks and scope lock
- APRV-01 through APRV-06 specify approval gates and rejection behavior
- Scope lock uses normalized paths to handle cross-platform differences
- `project-ai/` is the standard directory for all artifact files
- STATE.json is in `project-ai/STATE.json`
- Approval gates must be testable without real user input — mock `typer.confirm()`
- APRV-06 is critical: rejection must leave STATE.json byte-identical

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-guardrails-approval*
*Context gathered: 2026-03-10*
