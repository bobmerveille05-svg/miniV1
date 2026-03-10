# Phase 4: Guardrails & Approval Gates - Research

**Researched:** 2026-03-10
**Domain:** Pre-flight validation, scope enforcement, path normalization, interactive approval gates
**Confidence:** HIGH

## Summary

Phase 4 builds three independent safety modules (`preflight.py`, `scope_lock.py`, `approval.py`) that sit between the adapter layer (Phase 3) and the pipeline stages (Phases 6-10). The codebase already provides all foundational primitives: `Stage` enum, `ProjectState` with `approvals` dict, `save_state()`/`load_state()` for atomic persistence, `APPROVAL_KEYS`, and the three exception types (`PreflightError`, `ApprovalError`, `ValidationError`). No new dependencies are needed — `typer` (already installed >=0.24.0) provides `typer.confirm()` for Y/N prompts.

The implementation is straightforward data-mapping and validation code — no LLM calls, no external APIs, no complex concurrency. The primary complexity lies in: (1) getting path normalization right cross-platform (Windows case-insensitivity, forward-slash normalization), (2) ensuring rejection leaves STATE.json byte-identical (APRV-06), and (3) designing the approval functions to be testable without real user input.

**Primary recommendation:** Build three focused modules with pure-function cores (declarative mappings, path normalization, scope comparison) that are trivially unit-testable, then thin `typer.confirm()` wrappers for the interactive approval layer. Test approval gates by mocking `typer.confirm` at the module level.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Pre-flight module in `minilegion/core/preflight.py` with `check_preflight(stage: Stage, project_dir: Path) -> None`
- Declarative mapping: stage -> required files and required approvals (exact mappings specified in CONTEXT.md)
- Missing file raises `PreflightError` naming the missing file; missing approval raises `PreflightError` naming the missing approval key
- All required files checked relative to `project-ai/` directory
- Pre-flight loads current `ProjectState` from `STATE.json` for approval checks
- Scope lock module in `minilegion/core/scope_lock.py` with `check_scope(changed_files: list[str], allowed_files: list[str]) -> list[str]`
- Returns list of out-of-scope files (empty = all in scope)
- Separate `validate_scope(changed_files, allowed_files) -> None` that raises `ValidationError` on violation
- `normalize_path(path: str) -> str` co-located in `scope_lock.py` — resolves `./`, strips trailing slashes, normalizes to forward slashes, lowercases on Windows
- Does NOT resolve symlinks or absolute paths — relative project paths only
- Approval module in `minilegion/core/approval.py` with `approve(gate_name, summary, state, state_path) -> bool`
- Uses `typer.confirm()` for Y/N prompts
- On approval: sets `state.approvals[gate_name] = True`, adds history entry, saves state atomically, returns `True`
- On rejection: does NOT modify state at all (byte-identical), raises `ApprovalError` with gate name
- 5 gate functions: `approve_brief`, `approve_research`, `approve_design`, `approve_plan`, `approve_patch`
- Each formats a human-readable summary before calling `approve()`

### OpenCode's Discretion
- Exact summary formatting for each approval gate display
- Internal helper functions for path normalization edge cases
- Test fixture organization for approval gate testing (mocking typer.confirm)
- Whether to use a dataclass or plain dict for the pre-flight requirements mapping

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUARD-01 | Pre-flight check validates required files exist before each LLM call | Declarative `REQUIRED_FILES` mapping per stage; `check_preflight()` checks file existence in `project-ai/` |
| GUARD-02 | Pre-flight check validates required approvals in STATE.json before each LLM call | Declarative `REQUIRED_APPROVALS` mapping per stage; loads `ProjectState` and checks `approvals` dict |
| GUARD-03 | In safe mode, `design` refuses without `RESEARCH.json`; `plan` refuses without `DESIGN.json` | Covered by GUARD-01 file checks — these are specific cases of the general pre-flight check |
| GUARD-04 | Scope lock checks `changed_files` against `files_allowed` using normalized paths | `check_scope()` normalizes both lists then computes set difference |
| GUARD-05 | Path normalization applied to all file paths before scope lock comparison | `normalize_path()` handles `./`, trailing slashes, OS separators, Windows case |
| APRV-01 | CLI-based human approval gate after brief creation | `approve_brief(state, state_path, brief_content)` formats brief summary and calls `approve()` |
| APRV-02 | CLI-based human approval gate after research with summary display | `approve_research(state, state_path, research_summary)` |
| APRV-03 | CLI-based human approval gate after design with design display | `approve_design(state, state_path, design_summary)` |
| APRV-04 | CLI-based human approval gate after plan with plan display | `approve_plan(state, state_path, plan_summary)` |
| APRV-05 | CLI-based human approval gate before each patch with diff display | `approve_patch(state, state_path, diff_text)` |
| APRV-06 | Rejection at any gate leaves STATE.json unchanged — no partial state mutation | `approve()` only calls `save_state()` on confirmation; rejection raises `ApprovalError` without touching state |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | >=0.24.0 | `typer.confirm()` for Y/N prompts | Already a project dependency; provides confirm with `[y/N]` prompt |
| pydantic | >=2.12.0 | `ProjectState` model for state loading/saving | Already used; `load_state()`/`save_state()` handle serialization |
| pathlib | stdlib | Path manipulation in pre-flight and scope lock | Standard for cross-platform path handling |
| sys | stdlib | `sys.platform` check for Windows case normalization | Reliable platform detection |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Unit testing with `monkeypatch` for mocking `typer.confirm` | All test files |
| typer.testing | bundled | `CliRunner` for CLI integration tests | Testing approval flows end-to-end |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `typer.confirm()` | `input()` / `click.confirm()` | typer wraps click; using typer directly is consistent with project |
| Plain dict mapping | dataclass/NamedTuple | Dict is simpler for stage->list mapping; dataclass adds overhead without benefit |
| `sys.platform` | `os.name` | Both work; `sys.platform == "win32"` is the canonical Python idiom |

**Installation:**
```bash
# No new dependencies needed — all already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/core/
├── preflight.py     # check_preflight(), REQUIRED_FILES, REQUIRED_APPROVALS mappings
├── scope_lock.py    # normalize_path(), check_scope(), validate_scope()
├── approval.py      # approve(), approve_brief/research/design/plan/patch()
├── state.py         # (existing) ProjectState, save_state, load_state, Stage, APPROVAL_KEYS
├── exceptions.py    # (existing) PreflightError, ApprovalError, ValidationError
└── file_io.py       # (existing) write_atomic
```

### Pattern 1: Declarative Requirements Mapping
**What:** Static dict mapping `Stage` values to lists of required files/approvals. The `check_preflight()` function is a pure validator that reads this mapping.
**When to use:** Any time validation rules are stage-dependent.
**Example:**
```python
# minilegion/core/preflight.py
from minilegion.core.state import Stage

REQUIRED_FILES: dict[Stage, list[str]] = {
    Stage.RESEARCH: ["BRIEF.md"],
    Stage.DESIGN: ["BRIEF.md", "RESEARCH.json"],
    Stage.PLAN: ["BRIEF.md", "RESEARCH.json", "DESIGN.json"],
    Stage.EXECUTE: ["BRIEF.md", "RESEARCH.json", "DESIGN.json", "PLAN.json"],
    Stage.REVIEW: ["BRIEF.md", "RESEARCH.json", "DESIGN.json", "PLAN.json", "EXECUTION_LOG.json"],
}

REQUIRED_APPROVALS: dict[Stage, list[str]] = {
    Stage.RESEARCH: ["brief_approved"],
    Stage.DESIGN: ["brief_approved", "research_approved"],
    Stage.PLAN: ["brief_approved", "research_approved", "design_approved"],
    Stage.EXECUTE: ["brief_approved", "research_approved", "design_approved", "plan_approved"],
    Stage.REVIEW: ["brief_approved", "research_approved", "design_approved", "plan_approved", "execute_approved"],
}
```

### Pattern 2: Fail-Fast Validation with Named Errors
**What:** Pre-flight checks iterate over requirements and raise on the FIRST missing item, naming it explicitly.
**When to use:** When the user needs to know exactly what's missing to fix it.
**Example:**
```python
def check_preflight(stage: Stage, project_dir: Path) -> None:
    """Validate all prerequisites for a stage. Raises PreflightError on first failure."""
    # Check files
    for filename in REQUIRED_FILES.get(stage, []):
        filepath = project_dir / filename
        if not filepath.exists():
            raise PreflightError(f"Missing required file: {filename}")

    # Check approvals
    state = load_state(project_dir / "STATE.json")
    for approval_key in REQUIRED_APPROVALS.get(stage, []):
        if not state.approvals.get(approval_key, False):
            raise PreflightError(f"Missing required approval: {approval_key}")
```

### Pattern 3: Mutate-Only-On-Success for Approval Gates
**What:** The `approve()` function only modifies and saves state AFTER confirmation. Rejection raises immediately without touching state.
**When to use:** APRV-06 compliance — rejection must leave STATE.json byte-identical.
**Example:**
```python
def approve(gate_name: str, summary: str, state: ProjectState, state_path: Path) -> bool:
    """Prompt user for approval. Mutates state only on confirmation."""
    typer.echo(summary)
    if not typer.confirm(f"Approve {gate_name}?"):
        raise ApprovalError(f"Rejected: {gate_name}")
    # Only reached on approval
    state.approvals[gate_name] = True
    state.add_history("approval", f"Approved: {gate_name}")
    save_state(state, state_path)
    return True
```

### Pattern 4: Normalize-Then-Compare for Scope Lock
**What:** Normalize all paths before comparison using set operations.
**When to use:** Cross-platform file path comparison.
**Example:**
```python
import sys

def normalize_path(path: str) -> str:
    """Normalize a relative project path for cross-platform comparison."""
    # Remove ./ prefix
    if path.startswith("./"):
        path = path[2:]
    # Strip trailing slashes
    path = path.rstrip("/\\")
    # Normalize OS separators to forward slashes
    path = path.replace("\\", "/")
    # Lowercase on Windows for case-insensitive comparison
    if sys.platform == "win32":
        path = path.lower()
    return path

def check_scope(changed_files: list[str], allowed_files: list[str]) -> list[str]:
    """Return list of changed files that are NOT in allowed_files."""
    allowed_set = {normalize_path(f) for f in allowed_files}
    return [f for f in changed_files if normalize_path(f) not in allowed_set]
```

### Anti-Patterns to Avoid
- **Mutating state before confirmation:** Never set `state.approvals[key] = True` before `typer.confirm()` returns `True`. This violates APRV-06.
- **Using `os.path.normpath()` for normalization:** On Windows, `normpath` converts to backslashes, which breaks cross-platform path storage. Use manual forward-slash normalization.
- **Catching `typer.Abort` in approval:** `typer.confirm()` with `abort=True` raises `typer.Abort`. Instead, use `typer.confirm()` WITHOUT `abort=True` and check the return value, then raise `ApprovalError` manually.
- **Loading state inside the approval gate function:** State should be passed in, not loaded internally. The caller (pipeline stage) owns the state lifecycle. This keeps approval functions pure and testable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Y/N prompts | Custom `input()` parsing | `typer.confirm()` | Handles edge cases (EOF, ctrl-C), consistent UX with rest of CLI |
| Atomic file writes | Manual temp file + rename | `save_state()` which uses `write_atomic()` | Already proven pattern in codebase, handles error cleanup |
| Path separator normalization | Regex-based path parsing | `str.replace("\\", "/")` | Simple, predictable, no regex overhead |
| State serialization | Manual JSON construction | `ProjectState.model_dump_json()` + `model_validate_json()` | Pydantic handles validation, serialization, and type coercion |

**Key insight:** All infrastructure primitives already exist. Phase 4 is glue code that composes existing primitives (`Stage`, `ProjectState`, `save_state`, `PreflightError`, etc.) into three focused modules. Resist the urge to build new infrastructure.

## Common Pitfalls

### Pitfall 1: State Mutation Before Confirmation
**What goes wrong:** Setting `state.approvals[key] = True` before calling `typer.confirm()`, then trying to "roll back" on rejection.
**Why it happens:** Natural code flow puts mutation before the prompt.
**How to avoid:** Structure `approve()` so mutation ONLY happens after `typer.confirm()` returns `True`. The rejection path raises `ApprovalError` immediately — no state object is ever modified.
**Warning signs:** Any code that sets approval to True, then has a conditional that tries to undo it.

### Pitfall 2: Windows Path Case Sensitivity
**What goes wrong:** `check_scope()` reports false violations because `src/App.py` != `src/app.py` on Windows.
**Why it happens:** Windows filesystem is case-insensitive but Python string comparison is case-sensitive.
**How to avoid:** `normalize_path()` lowercases on Windows (`sys.platform == "win32"`). Always normalize BOTH sides before comparison.
**Warning signs:** Tests pass on Linux CI but fail on Windows dev machines.

### Pitfall 3: `os.path.normpath()` Converting to Backslashes
**What goes wrong:** On Windows, `os.path.normpath("src/foo/bar.py")` returns `"src\\foo\\bar.py"`, breaking forward-slash based path comparison.
**Why it happens:** `normpath` uses OS-native separators.
**How to avoid:** Don't use `os.path.normpath()`. Do manual normalization: `path.replace("\\", "/")`.
**Warning signs:** Scope lock passes on Linux but fails on Windows.

### Pitfall 4: `typer.confirm()` with `abort=True`
**What goes wrong:** Using `typer.confirm(abort=True)` raises `typer.Abort` (a `click.exceptions.Abort`), which is NOT an `ApprovalError`. The CLI framework catches `Abort` and prints "Aborted!" instead of our custom error handling.
**Why it happens:** `abort=True` is convenient but bypasses our exception hierarchy.
**How to avoid:** Use `typer.confirm()` WITHOUT `abort=True`. Check return value, raise `ApprovalError` manually.
**Warning signs:** Rejection prints "Aborted!" instead of the expected error message.

### Pitfall 5: Testing `typer.confirm()` in Unit Tests
**What goes wrong:** Tests hang waiting for interactive input, or `CliRunner` input simulation doesn't reach `typer.confirm()`.
**Why it happens:** `typer.confirm()` reads from stdin; unit tests don't provide stdin by default.
**How to avoid:** Two approaches:
1. **Unit tests:** Mock `typer.confirm` using `monkeypatch.setattr("minilegion.core.approval.typer.confirm", lambda *a, **kw: True)` — tests the logic without interaction.
2. **CLI integration tests:** Use `CliRunner(mix_stderr=False)` with `input="y\n"` — tests the full interactive flow.
**Warning signs:** Tests that import `typer` and call functions directly without mocking.

### Pitfall 6: Pre-flight Loading State Redundantly
**What goes wrong:** Pipeline stage loads state, then `check_preflight()` loads state again from disk, potentially seeing stale data if the caller has modified state in memory.
**Why it happens:** `check_preflight()` was designed to be self-contained.
**How to avoid:** Per CONTEXT.md, `check_preflight()` takes `project_dir` and loads state internally. This is acceptable because pre-flight runs BEFORE any in-memory state modifications. The state on disk IS the source of truth at pre-flight time.
**Warning signs:** None — this is the correct design per CONTEXT.md decisions.

## Code Examples

Verified patterns from the existing codebase:

### Loading and Checking State (existing pattern from state.py)
```python
# Source: minilegion/core/state.py
state = load_state(project_dir / "STATE.json")
# Check approval: state.approvals["brief_approved"] -> bool
# Save state: save_state(state, project_dir / "STATE.json") -> uses write_atomic
```

### Exception Raising (existing pattern from exceptions.py)
```python
# Source: minilegion/core/exceptions.py — all three needed exceptions exist
from minilegion.core.exceptions import PreflightError, ApprovalError, ValidationError

# Pre-flight failure:
raise PreflightError("Missing required file: RESEARCH.json")
raise PreflightError("Missing required approval: brief_approved")

# Approval rejection:
raise ApprovalError("Rejected: research_approved")

# Scope violation:
raise ValidationError("Out-of-scope files: ['src/unauthorized.py']")
```

### typer.confirm() Usage (from Typer docs)
```python
# Source: https://typer.tiangolo.com/tutorial/prompt/#confirm
import typer

# Without abort=True — returns bool
approved = typer.confirm("Approve research?")
# approved is True or False

# DO NOT use abort=True — it raises typer.Abort instead of returning False
```

### Mocking typer.confirm in Tests (pytest monkeypatch)
```python
# Pattern for unit testing approval gates
def test_approve_research_accepted(monkeypatch, tmp_path):
    monkeypatch.setattr("minilegion.core.approval.typer.confirm", lambda *a, **kw: True)

    state = ProjectState()
    state_path = tmp_path / "STATE.json"
    save_state(state, state_path)

    result = approve_research(state, state_path, "Research summary here")
    assert result is True
    assert state.approvals["research_approved"] is True

def test_approve_research_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("minilegion.core.approval.typer.confirm", lambda *a, **kw: False)

    state = ProjectState()
    state_path = tmp_path / "STATE.json"
    save_state(state, state_path)

    # Read file before rejection
    before = state_path.read_bytes()

    with pytest.raises(ApprovalError, match="research"):
        approve_research(state, state_path, "Research summary here")

    # STATE.json must be byte-identical (APRV-06)
    after = state_path.read_bytes()
    assert before == after
```

### CliRunner with Input for Integration Tests
```python
# Source: https://typer.tiangolo.com/tutorial/testing/#testing-input
from typer.testing import CliRunner
runner = CliRunner()

# Simulate user typing "y" then Enter
result = runner.invoke(app, ["research"], input="y\n")
assert result.exit_code == 0
```

### Path Normalization Comprehensive Examples
```python
# Comprehensive normalize_path behavior:
assert normalize_path("./src/foo.py") == "src/foo.py"        # Resolve ./
assert normalize_path("src/foo.py/") == "src/foo.py"          # Strip trailing /
assert normalize_path("src\\foo\\bar.py") == "src/foo/bar.py"  # Backslash -> forward
assert normalize_path("src/foo.py") == "src/foo.py"            # No-op
assert normalize_path("") == ""                                 # Empty string

# Windows only (sys.platform == "win32"):
assert normalize_path("SRC/Foo.py") == "src/foo.py"            # Lowercase
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `input("y/n?")` | `typer.confirm()` | Typer 0.x+ | Consistent CLI UX, handles edge cases |
| `os.path.normpath()` | Manual string normalization | N/A — project convention | Avoids backslash conversion on Windows |
| State loaded per-function | State passed as parameter (approval) / loaded once (preflight) | Phase 4 design decision | Reduces disk I/O, enables testability |

**Deprecated/outdated:**
- None — all libraries in use are current and stable.

## Open Questions

1. **Should `check_preflight()` check ALL missing files/approvals or fail on the first?**
   - What we know: CONTEXT.md says "raises PreflightError naming the missing file" (singular). The fail-fast pattern (stop on first) is simpler and consistent with the singular error message.
   - What's unclear: Users might want to see ALL issues at once to fix them in one pass.
   - Recommendation: Fail on first missing item. Simpler, consistent with CONTEXT.md language. If users need "show all," it can be added later without breaking the API.

2. **What `gate_name` string should `approve_patch` use?**
   - What we know: `APPROVAL_KEYS` has `"execute_approved"` as the approval key for the execute stage. But `approve_patch` is called per-patch, not per-stage.
   - What's unclear: Should `approve_patch` set `state.approvals["execute_approved"]`? Or is it a per-patch gate that doesn't persist to state?
   - Recommendation: `approve_patch` uses `"execute_approved"` as the gate name. Per CONTEXT.md, it calls `approve()` with appropriate summary — the gate function handles it. However, since there are multiple patches, `approve_patch` may need special handling: only the LAST approved patch (or a separate `approve_execution` call) should set `execute_approved = True`. The planner should clarify this in the task description. For now, implement `approve_patch` to use `"execute_approved"` but let the pipeline stage (Phase 9) decide when to call it.

3. **Summary formatting for each gate**
   - What we know: CONTEXT.md leaves this to OpenCode's discretion. Each gate formats artifact content into a human-readable summary.
   - Recommendation: Keep summaries concise. Brief: show full content (usually short). Research: show `project_overview` + `tech_stack`. Design: show `design_approach` + component names. Plan: show `objective` + task count + file count. Patch: show full diff text.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `testpaths = ["tests"]` |
| Quick run command | `python -m pytest tests/test_preflight.py tests/test_scope_lock.py tests/test_approval.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUARD-01 | Pre-flight validates required files exist | unit | `python -m pytest tests/test_preflight.py::TestPreflightFiles -x` | ❌ Wave 0 |
| GUARD-02 | Pre-flight validates required approvals | unit | `python -m pytest tests/test_preflight.py::TestPreflightApprovals -x` | ❌ Wave 0 |
| GUARD-03 | Design refuses without RESEARCH.json; plan refuses without DESIGN.json | unit | `python -m pytest tests/test_preflight.py::TestSafeModeGuards -x` | ❌ Wave 0 |
| GUARD-04 | Scope lock checks changed_files against allowed_files | unit | `python -m pytest tests/test_scope_lock.py::TestCheckScope -x` | ❌ Wave 0 |
| GUARD-05 | Path normalization on all paths before comparison | unit | `python -m pytest tests/test_scope_lock.py::TestNormalizePath -x` | ❌ Wave 0 |
| APRV-01 | Approval gate after brief creation | unit | `python -m pytest tests/test_approval.py::TestApproveBrief -x` | ❌ Wave 0 |
| APRV-02 | Approval gate after research | unit | `python -m pytest tests/test_approval.py::TestApproveResearch -x` | ❌ Wave 0 |
| APRV-03 | Approval gate after design | unit | `python -m pytest tests/test_approval.py::TestApproveDesign -x` | ❌ Wave 0 |
| APRV-04 | Approval gate after plan | unit | `python -m pytest tests/test_approval.py::TestApprovePlan -x` | ❌ Wave 0 |
| APRV-05 | Approval gate before patch application | unit | `python -m pytest tests/test_approval.py::TestApprovePatch -x` | ❌ Wave 0 |
| APRV-06 | Rejection leaves STATE.json byte-identical | unit | `python -m pytest tests/test_approval.py::TestRejectionByteIdentical -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_preflight.py tests/test_scope_lock.py tests/test_approval.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_preflight.py` — covers GUARD-01, GUARD-02, GUARD-03
- [ ] `tests/test_scope_lock.py` — covers GUARD-04, GUARD-05
- [ ] `tests/test_approval.py` — covers APRV-01 through APRV-06
- No framework install needed — pytest >=8.0 already in dev dependencies
- No new conftest fixtures needed beyond existing `tmp_project_dir`, `default_approvals`, `all_approved` — but a `mock_confirm` fixture would be useful

## Sources

### Primary (HIGH confidence)
- **Codebase source code:** `minilegion/core/state.py` — `Stage`, `ProjectState`, `APPROVAL_KEYS`, `save_state`, `load_state`, `StateMachine`
- **Codebase source code:** `minilegion/core/exceptions.py` — `PreflightError`, `ApprovalError`, `ValidationError` (all exist)
- **Codebase source code:** `minilegion/core/schemas.py` — `PlanSchema.touched_files`, `ExecutionLogSchema.tasks[].changed_files`, `ChangedFile.path`
- **Codebase source code:** `minilegion/core/file_io.py` — `write_atomic()` (used by `save_state`)
- **Codebase source code:** `minilegion/cli/commands.py` — `_pipeline_stub()`, `find_project_dir()`
- **Codebase source code:** `tests/conftest.py` — existing fixtures (`tmp_project_dir`, `default_approvals`, `all_approved`)
- **Codebase source code:** `tests/test_state.py`, `tests/test_cli.py` — testing patterns (class-based, parametrize, CliRunner)
- **Typer docs:** https://typer.tiangolo.com/tutorial/prompt/#confirm — `typer.confirm()` behavior
- **Typer docs:** https://typer.tiangolo.com/tutorial/testing/#testing-input — `CliRunner` with `input=` for testing prompts
- **Python stdlib:** `sys.platform` returns `"win32"` on Windows (verified on this machine)

### Secondary (MEDIUM confidence)
- None needed — all findings from primary sources.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies
- Architecture: HIGH — CONTEXT.md prescribes exact function signatures, module locations, and behavior
- Pitfalls: HIGH — identified from direct codebase analysis and Typer docs; path normalization pitfall verified on actual Windows platform
- Code examples: HIGH — derived from existing codebase patterns and official Typer documentation

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain — path normalization, typer.confirm, pydantic are all mature)
