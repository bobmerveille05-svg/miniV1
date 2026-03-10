# Phase 1: Foundation & CLI - Research

**Researched:** 2026-03-10
**Domain:** Python CLI framework, state machines, atomic file I/O, config parsing
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield Python project establishing MiniLegion's foundation: a Typer-based CLI with 8 commands, a linear-with-backtrack state machine managing 8 pipeline stages, atomic file I/O via `os.replace()`, JSON config parsing via Pydantic BaseModel, and a custom exception hierarchy. No LLM calls, no schemas, no pipeline logic — purely scaffolding.

The stack is locked: **Typer 0.24.1** for CLI (comes with Rich + Click), **Pydantic v2.12** for config/state models, standard library for atomic I/O (`tempfile`, `os.replace()`). All three are mature, well-documented, MIT-licensed, and work on Python >=3.10.

**Primary recommendation:** Use Typer's `@app.command()` pattern with `@app.callback()` for `--verbose` global option, Pydantic `BaseModel` with `model_validate_json()` for config loading, a plain Python class for the state machine (no external library), and `tempfile.NamedTemporaryFile` + `os.replace()` for atomic writes.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Project Layout**: Nested package structure: `minilegion/` with sub-packages `core/`, `cli/`, `adapters/`, `prompts/`. Entry point: `run.py` at repo root — user runs `python run.py <command>`. Dependencies declared in `pyproject.toml`.
- **State Machine Design**: Linear with backtrack: init → brief → research → design → plan → execute → review → archive. Can go backward but cannot skip forward. Backtracking clears downstream approvals. Single STATE.json as source of truth.
- **CLI Behavior**: Framework: Typer. Error display: colored text (red errors, yellow warnings, green success). `--verbose` flag. Approval prompts: simple Y/n with `typer.confirm()`.
- **Config Structure**: Location: `project-ai/minilegion.config.json`. Per-role engine assignment with `model` default + `engines` dict. API key via configurable env var name (`api_key_env` field). Sensible defaults baked into code.
- `minilegion init <name>` creates full template set in `project-ai/`: STATE.json, minilegion.config.json, BRIEF.md template, prompts/ directory.

### OpenCode's Discretion
- Exact sub-package boundaries within `minilegion/` (which modules go in `core/` vs top-level)
- Exception class naming and hierarchy details
- Atomic write implementation specifics (temp file naming, fsync behavior)
- Help text wording for CLI commands

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | `minilegion init <name>` creates project directory with template files in `project-ai/` | Typer command pattern with `name` CLI argument; `os.makedirs()` + atomic write for template files |
| FOUND-02 | Config via `minilegion.config.json` — LLM provider, model, API key, timeouts, per-role engines | Pydantic BaseModel with defaults + `model_validate_json()` for loading |
| FOUND-03 | State machine with 8 stages and valid/invalid transition enforcement | Plain Python class with `TRANSITIONS` dict and `transition()` method |
| FOUND-04 | STATE.json written atomically via `os.replace()` only after human approval | Atomic write utility + state computed in-memory before write |
| FOUND-05 | All file I/O uses atomic write pattern (temp file → `os.replace()`) | `write_atomic()` utility in `core/file_io.py` |
| FOUND-06 | Custom exception hierarchy for distinct error categories | Base `MiniLegionError` + category subclasses |
| CLI-01 | 8 commands via `python run.py <command>`: init, brief, research, design, plan, execute, review, status | Typer app with `@app.command()` decorators |
| CLI-02 | `plan` command accepts `--fast` and `--skip-research-design` flags | Typer `Option(default=False)` boolean flags |
| CLI-03 | `execute` command accepts `--task N` and `--dry-run` flags | Typer `Option()` with `int | None` and `bool` types |
| CLI-04 | Running without arguments shows usage help | `typer.Typer(no_args_is_help=True)` |
| CLI-05 | `status` command reads STATE.json and displays current stage, approvals, tasks, risks | Pydantic model for STATE.json + Rich-formatted output |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | 0.24.1 | CLI framework | Type-hint-based CLI with auto-help, auto-completion, Rich error formatting. Built on Click. |
| pydantic | 2.12.5 | Data validation & config models | Type-safe JSON parsing with `model_validate_json()`, `model_dump_json()`, field defaults. |
| rich | (bundled with typer) | Colored output, tables | Typer auto-installs Rich. Use `rich.print()` for formatted output, `Console(stderr=True)` for errors. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| click | (bundled with typer) | CLI internals | Typer is built on Click — never import Click directly, use Typer's API. |
| shellingham | (bundled with typer) | Shell detection | Auto-installed with Typer for completion installation. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | argparse | Typer is locked decision. argparse has no auto-help formatting, no color, more boilerplate. |
| Pydantic | dataclasses + json | Pydantic gives validation, JSON schema generation (needed Phase 2), and `model_validate_json()`. |
| Custom state machine | transitions lib | 8-stage linear machine is too simple to justify a dependency. Plain Python is clearer. |

**Installation:**
```bash
pip install typer pydantic
```

**pyproject.toml dependencies:**
```toml
[project]
name = "minilegion"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "typer>=0.24.0",
    "pydantic>=2.12.0",
]
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── __init__.py           # Package init, version
├── cli/
│   ├── __init__.py       # Typer app creation
│   └── commands.py       # All 8 command functions
├── core/
│   ├── __init__.py
│   ├── state.py          # State machine class + STATE.json model
│   ├── config.py         # Config Pydantic model + load/save
│   ├── file_io.py        # Atomic write utility
│   └── exceptions.py     # Exception hierarchy
├── adapters/
│   └── __init__.py       # Empty — populated in Phase 3
└── prompts/
    └── __init__.py       # Empty — populated in Phase 5
run.py                    # Entry point: imports and runs Typer app
pyproject.toml            # Project metadata + dependencies
```

### Pattern 1: Typer App with Commands
**What:** Create a `typer.Typer()` app, register 8 commands via `@app.command()`, add global `--verbose` via `@app.callback()`.
**When to use:** This is the ONLY pattern for CLI command registration.
**Example:**
```python
# Source: https://typer.tiangolo.com/tutorial/commands/callback/
import typer
from typing import Annotated

app = typer.Typer(
    name="minilegion",
    no_args_is_help=True,  # CLI-04: shows help when no command given
    help="MiniLegion — AI-assisted work protocol",
)

# Global state for --verbose
state = {"verbose": False}

@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose output")] = False,
):
    """MiniLegion — AI-assisted work protocol."""
    if verbose:
        state["verbose"] = True

@app.command()
def init(name: Annotated[str, typer.Argument(help="Project name")]):
    """Initialize a new MiniLegion project."""
    # Implementation here
    typer.echo(typer.style(f"Created project: {name}", fg=typer.colors.GREEN))

@app.command()
def status():
    """Show current project status."""
    # Load STATE.json, display with Rich tables
    pass

@app.command()
def plan(
    fast: Annotated[bool, typer.Option("--fast", help="Use basic context only")] = False,
    skip_research_design: Annotated[bool, typer.Option("--skip-research-design", help="Skip research and design stages")] = False,
):
    """Generate execution plan."""
    pass  # Stub for Phase 1

@app.command()
def execute(
    task: Annotated[int | None, typer.Option("--task", help="Execute specific task N")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show changes without applying")] = False,
):
    """Execute the plan."""
    pass  # Stub for Phase 1
```

### Pattern 2: Pydantic Config Model
**What:** Define config as a Pydantic BaseModel with defaults, load from JSON file with `model_validate_json()`.
**When to use:** For `minilegion.config.json` loading and STATE.json parsing.
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/models/
from pydantic import BaseModel, Field
from pathlib import Path
import json

class MiniLegionConfig(BaseModel):
    """Configuration for a MiniLegion project."""
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    timeout: int = 120
    max_retries: int = 2
    engines: dict[str, str] = Field(default_factory=dict)
    # engines example: {"researcher": "gpt-4o", "builder": "gpt-4o-mini"}

    def get_engine(self, role: str) -> str:
        """Get engine for a role, falling back to default model."""
        return self.engines.get(role, self.model)

def load_config(project_dir: Path) -> MiniLegionConfig:
    """Load config from project-ai/minilegion.config.json."""
    config_path = project_dir / "project-ai" / "minilegion.config.json"
    if not config_path.exists():
        return MiniLegionConfig()  # All defaults
    raw = config_path.read_text(encoding="utf-8")
    return MiniLegionConfig.model_validate_json(raw)
```

### Pattern 3: State Machine (Plain Python)
**What:** Dict-based transition table defining valid stage transitions. `transition()` validates and optionally clears downstream approvals on backtrack.
**When to use:** For managing the 8-stage pipeline.
**Example:**
```python
from enum import Enum

class Stage(str, Enum):
    INIT = "init"
    BRIEF = "brief"
    RESEARCH = "research"
    DESIGN = "design"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    ARCHIVE = "archive"

# Ordered stages for backtrack detection
STAGE_ORDER = list(Stage)

# Valid forward transitions (backward always allowed to any previous stage)
FORWARD_TRANSITIONS: dict[Stage, Stage] = {
    Stage.INIT: Stage.BRIEF,
    Stage.BRIEF: Stage.RESEARCH,
    Stage.RESEARCH: Stage.DESIGN,
    Stage.DESIGN: Stage.PLAN,
    Stage.PLAN: Stage.EXECUTE,
    Stage.EXECUTE: Stage.REVIEW,
    Stage.REVIEW: Stage.ARCHIVE,
}

APPROVAL_KEYS = [
    "brief_approved", "research_approved", "design_approved",
    "plan_approved", "execute_approved", "review_approved",
]

class StateMachine:
    def __init__(self, current_stage: Stage, approvals: dict[str, bool]):
        self.current_stage = current_stage
        self.approvals = approvals

    def can_transition(self, target: Stage) -> bool:
        """Check if transition is valid (forward by one, or backward)."""
        current_idx = STAGE_ORDER.index(self.current_stage)
        target_idx = STAGE_ORDER.index(target)

        if target_idx == current_idx + 1:
            return True  # Forward by one step
        if target_idx < current_idx:
            return True  # Backward (any previous stage)
        return False

    def transition(self, target: Stage) -> None:
        """Transition to target stage, clearing downstream approvals on backtrack."""
        if not self.can_transition(target):
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_stage} to {target}"
            )
        target_idx = STAGE_ORDER.index(target)
        # Clear downstream approvals on backtrack
        for key in APPROVAL_KEYS:
            stage_name = key.replace("_approved", "")
            try:
                stage = Stage(stage_name)
            except ValueError:
                continue
            if STAGE_ORDER.index(stage) >= target_idx:
                self.approvals[key] = False
        self.current_stage = target
```

### Pattern 4: Atomic File Write
**What:** Write to a temp file in the same directory, then atomically replace the target file using `os.replace()`.
**When to use:** ALL file writes in MiniLegion (FOUND-05).
**Example:**
```python
import os
import tempfile
from pathlib import Path

def write_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to path atomically using temp file + os.replace().

    Guarantees: if the write is interrupted, the original file is untouched.
    The temp file is created in the same directory to ensure same-filesystem rename.
    """
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (required for os.replace on same filesystem)
    fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data hits disk
        os.replace(tmp_path, str(path))  # Atomic on POSIX; near-atomic on Windows
    except BaseException:
        # Clean up temp file on any error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Pattern 5: Exception Hierarchy
**What:** Custom exception tree with a base class and category subclasses.
**When to use:** All error handling in MiniLegion.
**Example:**
```python
class MiniLegionError(Exception):
    """Base exception for all MiniLegion errors."""
    pass

class StateError(MiniLegionError):
    """Invalid state transition or state corruption."""
    pass

class InvalidTransitionError(StateError):
    """Attempted an invalid stage transition."""
    pass

class ConfigError(MiniLegionError):
    """Configuration loading or validation failure."""
    pass

class ValidationError(MiniLegionError):
    """Schema or data validation failure."""
    pass

class LLMError(MiniLegionError):
    """LLM API call failure."""
    pass

class PreflightError(MiniLegionError):
    """Pre-flight check failure (missing files, missing approvals)."""
    pass

class ApprovalError(MiniLegionError):
    """Approval gate rejection."""
    pass

class FileIOError(MiniLegionError):
    """File read/write failure."""
    pass
```

### Anti-Patterns to Avoid
- **Don't use `click` directly:** Typer wraps Click. Importing Click bypasses Typer's type-hint system and creates inconsistent behavior.
- **Don't use `json.loads()` for config:** Use `Pydantic.model_validate_json()` — it validates fields, applies defaults, and gives clear error messages.
- **Don't mutate STATE.json without going through the state machine:** Every state change must go through `StateMachine.transition()`.
- **Don't use `open().write()` directly:** All writes must use `write_atomic()` to prevent corruption.
- **Don't store state as globals:** Use the `state` dict pattern from Typer callback for CLI state; pass state objects explicitly for business logic.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI parsing | Custom argparse wrapper | Typer `@app.command()` | Auto-help, auto-completion, type validation, color formatting |
| JSON config validation | Manual `json.loads()` + key checks | Pydantic `BaseModel.model_validate_json()` | Type coercion, defaults, validation errors with field paths |
| Colored terminal output | ANSI escape codes | `typer.style()` / `rich.print()` | Cross-platform, respects NO_COLOR, handles terminal capabilities |
| Confirmation prompts | Custom `input()` loop | `typer.confirm()` | Handles Y/n/Enter defaults, integrates with Typer testing |
| JSON serialization | Manual `json.dumps()` | Pydantic `model.model_dump_json(indent=2)` | Consistent with validation models, handles nested objects |

**Key insight:** Typer + Pydantic handle 90% of the I/O and validation plumbing. The only custom code should be the state machine logic and the atomic write utility.

## Common Pitfalls

### Pitfall 1: os.replace() Cross-Filesystem Failure
**What goes wrong:** `os.replace()` fails if temp file and target are on different filesystems.
**Why it happens:** Using system temp directory instead of target's directory for temp file.
**How to avoid:** Always create temp file in the same directory as the target: `tempfile.mkstemp(dir=path.parent)`.
**Warning signs:** `OSError: Invalid cross-device link` on Linux.

### Pitfall 2: Windows os.replace() Non-Atomicity
**What goes wrong:** On Windows, `os.replace()` is not truly atomic — there's a brief window where neither file exists.
**Why it happens:** Windows filesystem semantics differ from POSIX.
**How to avoid:** Accept this limitation for Sprint 1. The window is extremely brief (microseconds). Document it. For critical production use, could use `ctypes` to call `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`, but this is overkill for Sprint 1.
**Warning signs:** Only relevant under extreme concurrent access (not a concern for single-user CLI).

### Pitfall 3: Typer --verbose Flag Placement
**What goes wrong:** User runs `python run.py init --verbose myproject` and gets "Error: No such option: --verbose".
**Why it happens:** Global options from `@app.callback()` must come BEFORE the command name, not after.
**How to avoid:** Document clearly: `python run.py --verbose init myproject`. Add help text explaining this. This is fundamental to how Click/Typer works and cannot be changed.
**Warning signs:** User confusion in error messages.

### Pitfall 4: Pydantic Strict vs Lax Mode
**What goes wrong:** Config string `"120"` for timeout gets silently coerced to int `120`.
**Why it happens:** Pydantic v2 coerces by default in Python mode.
**How to avoid:** This is actually desirable for config files parsed from JSON (JSON has proper types). `model_validate_json()` uses JSON mode which is stricter.
**Warning signs:** Only problematic if someone constructs config from Python dicts — not an issue for JSON file loading.

### Pitfall 5: Forgetting to Handle Missing project-ai/ Directory
**What goes wrong:** Commands other than `init` crash with FileNotFoundError when `project-ai/` doesn't exist.
**Why it happens:** No guard checking project directory exists before command execution.
**How to avoid:** Add a helper that checks for `project-ai/` existence and raises a clear `ConfigError` with message "No MiniLegion project found. Run `minilegion init <name>` first."
**Warning signs:** Raw Python tracebacks instead of user-friendly error messages.

### Pitfall 6: State Machine Backtrack Doesn't Clear Enough
**What goes wrong:** User backtracks from `design` to `research`, but `design_approved` is still `True`.
**Why it happens:** Only clearing the target stage's approval instead of all downstream approvals.
**How to avoid:** When backtracking to stage N, clear approvals for stage N and ALL stages after N.
**Warning signs:** Pipeline proceeds with stale approvals from a previous run.

## Code Examples

### run.py Entry Point
```python
# Source: Typer official docs pattern
"""MiniLegion CLI entry point."""
from minilegion.cli import app

if __name__ == "__main__":
    app()
```

### CLI App Creation (minilegion/cli/__init__.py)
```python
# Source: https://typer.tiangolo.com/tutorial/commands/callback/
import typer

app = typer.Typer(
    name="minilegion",
    no_args_is_help=True,
    help="MiniLegion — AI-assisted work protocol",
)

# Import commands to register them
from minilegion.cli.commands import *  # noqa: F401, F403
```

### Testing CLI Commands
```python
# Source: https://typer.tiangolo.com/tutorial/testing/
from typer.testing import CliRunner
from minilegion.cli import app

runner = CliRunner()

def test_init_creates_project():
    result = runner.invoke(app, ["init", "myproject"])
    assert result.exit_code == 0
    assert "myproject" in result.output

def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output

def test_invalid_transition_rejected():
    # After init, trying to run design should fail
    result = runner.invoke(app, ["design"])
    assert result.exit_code != 0
    assert "Cannot transition" in result.output or "error" in result.output.lower()

def test_status_reads_state():
    # After init, status should show "init" stage
    runner.invoke(app, ["init", "testproject"])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "init" in result.output

def test_approval_prompt():
    # Test interactive input with typer.confirm
    result = runner.invoke(app, ["brief"], input="y\n")
    # Verify Y/n prompt was shown
```

### STATE.json Pydantic Model
```python
# Source: Pydantic BaseModel docs
from pydantic import BaseModel, Field
from datetime import datetime

class HistoryEntry(BaseModel):
    timestamp: str
    action: str
    details: str = ""

class ProjectState(BaseModel):
    """STATE.json schema."""
    current_stage: str = "init"
    approvals: dict[str, bool] = Field(default_factory=lambda: {
        "brief_approved": False,
        "research_approved": False,
        "design_approved": False,
        "plan_approved": False,
        "execute_approved": False,
        "review_approved": False,
    })
    completed_tasks: list[str] = Field(default_factory=list)
    history: list[HistoryEntry] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    def add_history(self, action: str, details: str = "") -> None:
        self.history.append(HistoryEntry(
            timestamp=datetime.now().isoformat(),
            action=action,
            details=details,
        ))
```

### Config Template (minilegion.config.json)
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key_env": "OPENAI_API_KEY",
  "timeout": 120,
  "max_retries": 2,
  "engines": {}
}
```

### Init Command Template Files
```python
# Template content for minilegion init <name>
BRIEF_TEMPLATE = """# Brief

## What do you want to build?

[Describe your project here]

## Constraints

[Any constraints or requirements]
"""

STATE_TEMPLATE = {
    "current_stage": "init",
    "approvals": {
        "brief_approved": False,
        "research_approved": False,
        "design_approved": False,
        "plan_approved": False,
        "execute_approved": False,
        "review_approved": False,
    },
    "completed_tasks": [],
    "history": [
        {
            "timestamp": "",  # Set at creation time
            "action": "init",
            "details": "Project initialized",
        }
    ],
    "metadata": {},
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Typer `typer.echo()` for output | `rich.print()` or `print()` | Typer 0.12+ | `typer.echo()` still works but Rich is preferred for formatted output |
| `typer.Option(default=None)` | `Annotated[type, typer.Option()]` | Typer 0.9+ | Annotated syntax is preferred, cleaner type hints |
| Pydantic v1 `class Config:` | Pydantic v2 `model_config = ConfigDict(...)` | Pydantic 2.0 | v1 syntax still works via compat layer but v2 is proper |
| `model.dict()` | `model.model_dump()` | Pydantic 2.0 | Old method deprecated |
| `model.json()` | `model.model_dump_json()` | Pydantic 2.0 | Old method deprecated |
| `Model.parse_raw()` | `Model.model_validate_json()` | Pydantic 2.0 | Old method removed in v2 |

**Deprecated/outdated:**
- `typer.secho()`: Still works but `rich.print("[bold red]text[/]")` is more powerful
- `typer-slim`: Discontinued since Typer 0.22.0, now just installs full Typer
- Pydantic v1 API: Available via `from pydantic import v1` but should never be used in new code

## Open Questions

1. **Working directory detection**
   - What we know: Commands need to find `project-ai/` relative to CWD
   - What's unclear: Should we search parent directories (like git does) or only check CWD?
   - Recommendation: Start with CWD-only. Simpler, avoids ambiguity. Can add parent traversal later.

2. **Command stubs for unimplemented phases**
   - What we know: CLI-01 requires all 8 commands to exist, but most are stubs in Phase 1
   - What's unclear: Should stubs check state machine or just print "not yet implemented"?
   - Recommendation: Stubs should still validate state transitions (so FOUND-03 is testable on all commands), then print "Not yet implemented" with a green "would run X" message. This tests the state machine for free.

3. **fsync on Windows**
   - What we know: `os.fsync()` works on Windows but `os.replace()` is not POSIX-atomic
   - What's unclear: Whether to add NTFS-specific handling
   - Recommendation: Use the same cross-platform code. The microsecond window on Windows is acceptable for a single-user CLI tool.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest) |
| Config file | none — Wave 0 will create `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | `init` creates project-ai/ with template files | integration | `pytest tests/test_init.py -x` | ❌ Wave 0 |
| FOUND-02 | Config loads from JSON with defaults | unit | `pytest tests/test_config.py -x` | ❌ Wave 0 |
| FOUND-03 | State machine enforces valid transitions | unit | `pytest tests/test_state.py -x` | ❌ Wave 0 |
| FOUND-04 | STATE.json written atomically after approval | unit | `pytest tests/test_state.py::test_atomic_write -x` | ❌ Wave 0 |
| FOUND-05 | All file writes use atomic pattern | unit | `pytest tests/test_file_io.py -x` | ❌ Wave 0 |
| FOUND-06 | Exception hierarchy exists | unit | `pytest tests/test_exceptions.py -x` | ❌ Wave 0 |
| CLI-01 | 8 commands registered and routable | integration | `pytest tests/test_cli.py -x` | ❌ Wave 0 |
| CLI-02 | plan accepts --fast and --skip-research-design | integration | `pytest tests/test_cli.py::test_plan_flags -x` | ❌ Wave 0 |
| CLI-03 | execute accepts --task N and --dry-run | integration | `pytest tests/test_cli.py::test_execute_flags -x` | ❌ Wave 0 |
| CLI-04 | No args shows help | integration | `pytest tests/test_cli.py::test_no_args_help -x` | ❌ Wave 0 |
| CLI-05 | status reads and displays STATE.json | integration | `pytest tests/test_cli.py::test_status -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — test package init
- [ ] `tests/conftest.py` — shared fixtures (tmp_path for project dirs, sample configs)
- [ ] `tests/test_state.py` — state machine unit tests
- [ ] `tests/test_config.py` — config loading unit tests
- [ ] `tests/test_file_io.py` — atomic write unit tests
- [ ] `tests/test_exceptions.py` — exception hierarchy tests
- [ ] `tests/test_cli.py` — CLI integration tests using CliRunner
- [ ] `tests/test_init.py` — init command integration tests
- [ ] Framework install: `pip install pytest` — add to dev dependencies in pyproject.toml

## Sources

### Primary (HIGH confidence)
- [Typer official docs](https://typer.tiangolo.com/) — commands, callbacks, testing, printing, exceptions, prompts
- [Typer PyPI](https://pypi.org/project/typer/) — v0.24.1, Python >=3.10, released Feb 21 2026
- [Pydantic official docs](https://docs.pydantic.dev/latest/concepts/models/) — BaseModel, model_validate_json, model_dump
- [Pydantic PyPI](https://pypi.org/project/pydantic/) — v2.12.5, Python >=3.9, released Nov 26 2025
- Python stdlib docs — `os.replace()`, `tempfile.mkstemp()`, `os.fsync()`

### Secondary (MEDIUM confidence)
- Python atomic write patterns — standard pattern documented across multiple sources, well-established

### Tertiary (LOW confidence)
- None — all findings verified with official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified on PyPI, APIs verified in official docs
- Architecture: HIGH — patterns taken directly from official Typer/Pydantic documentation
- Pitfalls: HIGH — documented gotchas from official docs (Typer callback ordering, os.replace() cross-device)
- State machine: HIGH — simple enough that no external source needed; Python stdlib Enum + dict

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable libraries, 30-day validity)
