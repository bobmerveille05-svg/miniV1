# Architecture Research — MiniLegion

**Project:** MiniLegion — File-centric, multi-engine, LLM-assisted work protocol
**Researched:** 2026-03-09
**Overall confidence:** HIGH (patterns verified across multiple real-world tools)

---

## Component Map

MiniLegion's 4-layer architecture (Protocol > Orchestrator > Adapters > Repo) maps onto 8 discrete components with well-defined boundaries.

### Layer 1: Protocol (Prompts + Schemas)

| Component | Responsibility | Owns |
|-----------|---------------|------|
| **Prompt Templates** | Role-specific system/user prompts for each pipeline stage | `prompts/` directory: one `.py` or `.txt` per role |
| **JSON Schemas** | Structural contracts for all 6 machine-readable artifacts | `schemas/` directory: one `.json` per artifact type |

**Boundary rule:** Protocol layer is pure data — no logic, no I/O, no imports of other layers. Prompt templates are string constants or Jinja2-like templates. Schemas are static JSON files loaded at startup.

### Layer 2: Orchestrator (CLI + State Machine + Guardrails)

| Component | Responsibility | Owns |
|-----------|---------------|------|
| **CLI Entrypoint** | Parses commands, routes to pipeline stages | `cli.py` — Typer app with 8 subcommands |
| **Pipeline Orchestrator** | Executes stage sequence: preflight > LLM call > validate > approve > write | `orchestrator.py` — single class or function per stage |
| **State Machine** | Manages STATE.json transitions, enforces legal moves | `state.py` — Enum-based states + transition table |
| **Guardrails** | Pre-flight checks, scope lock, retry logic, revise bounds | `guardrails.py` — pure functions, no side effects |

**Boundary rule:** Orchestrator imports Protocol (for prompts/schemas) and Adapters (for LLM calls). It never imports Repo directly — it receives file paths and content as data.

### Layer 3: Adapters (LLM Interface)

| Component | Responsibility | Owns |
|-----------|---------------|------|
| **Base Adapter** | Abstract interface defining `call(prompt, config) -> str` | `adapters/base.py` — ABC with `call()` method |
| **OpenAI Adapter** | Concrete implementation for OpenAI API | `adapters/openai_adapter.py` — uses `openai` package |

**Boundary rule:** Adapters know nothing about MiniLegion's domain. They accept a prompt string + config dict, return a raw response string. No schema validation, no state awareness.

### Layer 4: Repo (Local Filesystem)

| Component | Responsibility | Owns |
|-----------|---------------|------|
| **File I/O** | Read/write `project-ai/` artifacts, config loading | `repo.py` — thin wrapper around `pathlib` / `json` |
| **Deep Context** | Codebase scanning for research phase | `deep_context.py` — file tree, symbol extraction |

**Boundary rule:** Repo layer is the only component that touches the filesystem. All other layers receive/return data as Python objects.

### Component Interaction Diagram

```
                    USER
                      |
                      v
               +-----------+
               |    CLI    |  (Typer commands)
               +-----------+
                      |
                      v
            +------------------+
            |   Orchestrator   |  (pipeline stages)
            +------------------+
               /     |      \
              v      v       v
        +--------+ +-----+ +----------+
        |Guardrails| |State| | Prompts |  (Protocol)
        +--------+ +-----+ +----------+
              |      |          |
              v      v          v
         +------------------+
         |  LLM Adapter     |  (abstract → concrete)
         +------------------+
                   |
                   v
            +------------+
            |   Repo     |  (filesystem I/O)
            +------------+
                   |
                   v
             project-ai/
```

---

## Data Flow

### Per-Stage Pipeline (the core loop)

Every pipeline stage (research, design, plan, execute, review) follows the same 6-step data flow:

```
1. CLI DISPATCH
   User runs: `python run.py research`
   Typer routes to orchestrator.run_stage("research")

2. PREFLIGHT CHECK
   guardrails.preflight(stage, state) -> Result
   - Checks STATE.json for legal transition
   - Checks required prerequisite files exist
   - Checks required approvals are present
   - Returns OK or error with specific failure reason

3. PROMPT ASSEMBLY
   prompt = prompts.build("research", context)
   - Loads role-specific template
   - Injects context (brief content, config, prior artifacts)
   - Returns complete prompt string

4. LLM CALL + RETRY
   raw_response = adapter.call(prompt, config)
   - Adapter sends prompt to LLM API
   - Returns raw string response
   - On API error: retry up to 2 times with backoff

5. VALIDATION
   parsed = validate_response(raw_response, schema)
   - Strip any markdown wrapper (```json blocks)
   - json.loads() the response
   - jsonschema.validate() against stage schema
   - On parse failure: retry LLM call (max 2 retries)
   - On schema failure: retry with error feedback in prompt
   - Returns validated Python dict

6. APPROVAL GATE
   approved = prompt_user_approval(parsed, stage)
   - Display summary to user (or full content)
   - Wait for y/n input
   - If approved: write artifacts + update STATE.json
   - If rejected: state unchanged (safety invariant)
```

### Data Objects Flowing Through Pipeline

```
                    Config (minilegion.config.json)
                         |
Brief (input)  -->  [Prompt Template]  -->  Prompt String
                         |
                    [LLM Adapter]
                         |
                    Raw Response String
                         |
                    [JSON Parser + Schema Validator]
                         |
                    Validated Dict
                         |
                    [Approval Gate]
                         |
              +----------+-----------+
              |                      |
         Approved                Rejected
              |                      |
    [Write .md + .json]        [No state change]
    [Update STATE.json]
```

### State Data Flow (STATE.json)

```json
{
  "task_id": "T001",
  "current_phase": "research",
  "status": "approved",
  "approvals": {
    "brief": true,
    "research": true,
    "design": false
  },
  "changed_files": [],
  "files_allowed": []
}
```

**Critical invariant:** STATE.json is only written when `approved == true`. The write is atomic — read current state, compute new state, write entire file. No partial updates.

---

## State Machine Design

### States (Enum-based)

```python
from enum import StrEnum

class Phase(StrEnum):
    INIT = "init"
    BRIEF = "brief"
    RESEARCH = "research"
    DESIGN = "design"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    ARCHIVE = "archive"

class Status(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISING = "revising"
```

**Why StrEnum:** States serialize directly to JSON strings. Python 3.11+ StrEnum is ideal because `Phase.BRIEF == "brief"` is `True`, eliminating `.value` boilerplate everywhere. For Python 3.9/3.10 compat, use a simple string Enum with `str` mixin.

### Transition Table (dict-based, not class hierarchy)

```python
# Legal transitions: (current_phase, current_status) -> [allowed_next_states]
TRANSITIONS: dict[tuple[Phase, Status], list[tuple[Phase, Status]]] = {
    (Phase.INIT, Status.PENDING):        [(Phase.BRIEF, Status.PENDING)],
    (Phase.BRIEF, Status.PENDING):       [(Phase.BRIEF, Status.IN_PROGRESS)],
    (Phase.BRIEF, Status.IN_PROGRESS):   [(Phase.BRIEF, Status.AWAITING_APPROVAL)],
    (Phase.BRIEF, Status.AWAITING_APPROVAL): [
        (Phase.BRIEF, Status.APPROVED),
        (Phase.BRIEF, Status.REJECTED),
    ],
    (Phase.BRIEF, Status.APPROVED):      [(Phase.RESEARCH, Status.PENDING)],
    (Phase.BRIEF, Status.REJECTED):      [(Phase.BRIEF, Status.PENDING)],
    # ... pattern repeats for each phase
}

def can_transition(current: tuple[Phase, Status], target: tuple[Phase, Status]) -> bool:
    allowed = TRANSITIONS.get(current, [])
    return target in allowed
```

**Why dict-based, not class hierarchy:** The transition table is data, not behavior. A dict is:
- Inspectable at runtime (can dump all legal transitions)
- Testable without mocking (pure function checks)
- Serializable (can write transition table to docs)
- Extensible without touching class hierarchy

**Why not a state machine library (transitions, statemachine):** MiniLegion's state machine is linear with approval gates — not a complex graph. A library would add a dependency for ~20 lines of dict + validation logic. The dict approach is more transparent and easier to debug.

### Fast Mode State Skipping

```python
FAST_MODE_SKIP = {Phase.RESEARCH, Phase.DESIGN}

def resolve_next_phase(current: Phase, fast_mode: bool) -> Phase:
    """Return next phase, skipping research/design in fast mode."""
    order = list(Phase)
    idx = order.index(current) + 1
    while idx < len(order):
        candidate = order[idx]
        if fast_mode and candidate in FAST_MODE_SKIP:
            idx += 1
            continue
        return candidate
    raise ValueError("No next phase available")
```

### Revise Loop (bounded)

```python
MAX_REVISE_ITERATIONS = 2

def run_with_revise(stage_fn, max_iter=MAX_REVISE_ITERATIONS):
    """Run a stage with bounded revision loop."""
    for attempt in range(max_iter + 1):
        result = stage_fn()
        if result.approved:
            return result
        if attempt < max_iter:
            # Feed rejection reason back for revision
            stage_fn = partial(stage_fn, revision_context=result.feedback)
        else:
            raise EscalationError(
                f"Stage failed after {max_iter} revisions. Human intervention required."
            )
```

---

## Python Project Layout

### Recommended: Flat layout (not src/)

For MiniLegion specifically, use flat layout because:
1. **`run.py` entrypoint** — project is run as `python run.py <command>`, not installed as a package
2. **No PyPI distribution** — this is an application, not a library
3. **Simpler development** — no editable install required for testing
4. **Matches PROJECT.md** — spec already references `run.py` and `core/` directly

The src/ layout is better for distributable libraries. MiniLegion is an application tool.

### File Structure

```
minilegion/
|-- run.py                          # CLI entrypoint: `python run.py <command>`
|-- minilegion.config.json          # User-editable configuration
|-- NO_ADD.md                       # Sprint 1 scope lock contract
|
|-- core/                           # Application logic (Layer 2: Orchestrator)
|   |-- __init__.py
|   |-- cli.py                      # Typer app with 8 subcommands
|   |-- orchestrator.py             # Pipeline stage runner
|   |-- state.py                    # Phase/Status enums + transition table + STATE I/O
|   |-- guardrails.py               # Preflight checks, scope lock, retry logic
|   |-- validator.py                # JSON parse + schema validation + retry
|   |-- approval.py                 # User approval prompts (y/n gates)
|   |-- config.py                   # Config file loading + defaults
|   |-- deep_context.py             # Codebase scanning for research
|   |-- repo.py                     # Filesystem I/O for project-ai/
|   |-- exceptions.py               # Custom exception hierarchy
|
|-- adapters/                       # LLM adapters (Layer 3)
|   |-- __init__.py
|   |-- base.py                     # ABC: BaseLLMAdapter
|   |-- openai_adapter.py           # OpenAI implementation
|
|-- prompts/                        # Prompt templates (Layer 1: Protocol)
|   |-- __init__.py
|   |-- researcher.py               # Researcher role prompt builder
|   |-- designer.py                 # Designer role prompt builder
|   |-- planner.py                  # Planner role prompt builder
|   |-- builder.py                  # Builder role prompt builder
|   |-- reviewer.py                 # Reviewer role prompt builder
|
|-- schemas/                        # JSON Schemas (Layer 1: Protocol)
|   |-- research.schema.json
|   |-- design.schema.json
|   |-- plan.schema.json
|   |-- execution_log.schema.json
|   |-- review.schema.json
|   |-- state.schema.json
|
|-- project-ai/                     # Runtime artifacts (Layer 4: Repo output)
|   |-- STATE.json                  # Pipeline state (auto-managed)
|   |-- BRIEF.md                    # User-written brief
|   |-- RESEARCH.md / RESEARCH.json
|   |-- DESIGN.md / DESIGN.json
|   |-- PLAN.md / PLAN.json
|   |-- EXECUTION_LOG.json
|   |-- REVIEW.md / REVIEW.json
|   |-- DECISIONS.md                # Archivist-maintained
|
|-- tests/                          # (Sprint 2+, out of scope for Sprint 1)
    |-- ...
```

### Why This Layout

| Decision | Rationale |
|----------|-----------|
| `core/` not `src/minilegion/` | Application, not library. Run directly with `python run.py` |
| `adapters/` separate from `core/` | Clear layer boundary. Adapters have zero knowledge of core domain |
| `prompts/` as Python modules | Templates need dynamic context injection (f-strings/format), not static text |
| `schemas/` as static JSON files | Schemas are data, not code. Loadable by any tool. Validatable by standard tooling |
| `project-ai/` at root | Matches spec. User-visible output directory. Not inside package |
| `run.py` at root | Single-file entrypoint. `python run.py brief` is discoverable |
| No `__main__.py` | Not a package to be run with `python -m`. `run.py` is more explicit |

---

## Suggested Build Order

Build order is driven by dependency chains. You cannot test component B until component A exists.

### Phase 1: Foundation (must exist before anything else)

```
1. core/state.py        — Phase/Status enums + transition table
2. schemas/state.schema.json — STATE.json schema
3. core/repo.py         — Read/write JSON files to project-ai/
4. core/config.py       — Load minilegion.config.json
5. core/exceptions.py   — Custom exception types
```

**Rationale:** Everything downstream depends on state representation and file I/O. Build these first and you can test them in isolation with no LLM calls.

### Phase 2: Guardrails + Validation (safety before LLM)

```
6. core/guardrails.py   — Preflight checks (pure functions)
7. core/validator.py    — JSON parse + jsonschema validate
8. schemas/*.json       — All 6 artifact schemas
9. core/approval.py     — User prompt (y/n with display)
```

**Rationale:** Guardrails and validation are the safety net. They must be solid before any LLM output flows through the system. These are all testable without LLM calls.

### Phase 3: LLM Adapter (the external dependency)

```
10. adapters/base.py           — ABC definition
11. adapters/openai_adapter.py — Concrete implementation
```

**Rationale:** Keep adapter minimal. The ABC defines the contract; the OpenAI adapter is a thin wrapper around `openai.ChatCompletion.create()`. Test with mock responses.

### Phase 4: Protocol Layer (prompts)

```
12. prompts/planner.py   — Start with Plan (simplest useful role)
13. prompts/builder.py   — Builder prompts
14. prompts/reviewer.py  — Reviewer prompts
15. prompts/researcher.py — Researcher prompts
16. prompts/designer.py  — Designer prompts
```

**Rationale:** Build prompts for the core pipeline first (plan > execute > review), then the extended pipeline (research > design). Prompts depend on schema knowledge — schemas must exist first.

### Phase 5: Orchestrator + CLI (assembly)

```
17. core/orchestrator.py — Wire pipeline stages together
18. core/cli.py          — Typer commands routing to orchestrator
19. run.py               — Entrypoint importing cli
```

**Rationale:** The orchestrator is pure composition — it wires together guardrails, prompts, adapter, validator, approval, and repo. It should be the last piece because it imports everything else.

### Phase 6: Extended Features

```
20. core/deep_context.py — Codebase scanning
21. Fast mode flag       — --fast / --skip-research-design
22. Archivist logic      — Deterministic state+decisions update
```

### Build Order Dependency Graph

```
                  state.py
                 /    |    \
                v     v     v
           repo.py  config.py  exceptions.py
              |       |
              v       v
         guardrails.py
              |
              v
         validator.py  <--  schemas/*.json
              |
              v
         approval.py
              |
              v
         base.py (adapter ABC)
              |
              v
         openai_adapter.py
              |
              v
         prompts/*.py
              |
              v
         orchestrator.py
              |
              v
           cli.py
              |
              v
           run.py
```

---

## Integration Patterns

### Pattern 1: Adapter Pattern (ABC + Concrete)

**What:** Abstract base class defining the LLM interface contract. Concrete implementations per provider.

**Why:** PROJECT.md mandates "runtime portability" — must work with any LLM, not just OpenAI. The adapter pattern isolates the LLM dependency behind a stable interface.

```python
# adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 120

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict  # token counts

class BaseLLMAdapter(ABC):
    @abstractmethod
    def call(self, prompt: str, config: LLMConfig) -> LLMResponse:
        """Send prompt to LLM, return response. Raise on API error."""
        ...
```

```python
# adapters/openai_adapter.py
import openai
from .base import BaseLLMAdapter, LLMConfig, LLMResponse

class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    def call(self, prompt: str, config: LLMConfig) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        )
```

### Pattern 2: Validated Response Pipeline

**What:** A composable pipeline for handling LLM responses: strip wrappers > parse JSON > validate schema > return typed dict.

**Why:** LLMs frequently wrap JSON in markdown code fences, return partial JSON, or produce structurally valid but schema-invalid output. A dedicated pipeline handles all failure modes with bounded retry.

```python
# core/validator.py
import json
import re
from pydantic import BaseModel, ValidationError as PydanticValidationError

MAX_RETRIES = 2

def strip_json_wrapper(raw: str) -> str:
    """Remove markdown ```json ... ``` wrappers if present."""
    match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', raw, re.DOTALL)
    return match.group(1) if match else raw.strip()

def parse_and_validate(raw: str, model_class: type[BaseModel]) -> BaseModel:
    """Parse JSON string and validate against Pydantic model. Raises on failure."""
    cleaned = strip_json_wrapper(raw)
    parsed = json.loads(cleaned)  # Raises json.JSONDecodeError
    return model_class.model_validate(parsed)  # Raises PydanticValidationError

def call_with_validation(adapter, prompt, config, model_class, max_retries=MAX_RETRIES):
    """Call LLM and validate response with bounded retry."""
    last_error = None
    for attempt in range(max_retries + 1):
        response = adapter.call(prompt, config)
        try:
            return parse_and_validate(response.content, model_class)
        except (json.JSONDecodeError, PydanticValidationError) as e:
            last_error = e
            if attempt < max_retries:
                # Augment prompt with error feedback for retry
                prompt = f"{prompt}\n\nPrevious attempt failed: {e}\nPlease return valid JSON."
    raise last_error
```

### Pattern 3: Preflight Check as Pure Function

**What:** Each preflight check is a pure function: `(state, config) -> Result`. No side effects, no I/O within the check itself.

**Why:** Testable without mocking. Composable. Clear error messages.

```python
# core/guardrails.py
from dataclasses import dataclass

@dataclass
class PreflightResult:
    ok: bool
    errors: list[str]

def check_phase_transition(state: dict, target_phase: str) -> PreflightResult:
    """Check if transitioning to target_phase is legal."""
    errors = []
    current = (state["current_phase"], state["status"])
    if not can_transition(current, (target_phase, "in_progress")):
        errors.append(
            f"Cannot move from {current} to {target_phase}. "
            f"Current phase must be approved first."
        )
    return PreflightResult(ok=len(errors) == 0, errors=errors)

def check_prerequisites(state: dict, target_phase: str, project_dir: Path) -> PreflightResult:
    """Check that required files from prior phases exist."""
    errors = []
    required = PREREQUISITES.get(target_phase, [])
    for filename in required:
        if not (project_dir / filename).exists():
            errors.append(f"Missing prerequisite: {filename}")
    return PreflightResult(ok=len(errors) == 0, errors=errors)

def check_scope_lock(changed_files: list[str], allowed_files: list[str]) -> PreflightResult:
    """Mechanical check: changed_files must be subset of allowed_files."""
    violations = set(changed_files) - set(allowed_files)
    if violations:
        return PreflightResult(ok=False, errors=[
            f"Scope violation: {f} not in allowed files" for f in violations
        ])
    return PreflightResult(ok=True, errors=[])

def run_preflight(state: dict, target_phase: str, project_dir: Path) -> PreflightResult:
    """Compose all preflight checks."""
    checks = [
        check_phase_transition(state, target_phase),
        check_prerequisites(state, target_phase, project_dir),
    ]
    all_errors = [e for c in checks for e in c.errors]
    return PreflightResult(ok=len(all_errors) == 0, errors=all_errors)
```

### Pattern 4: Typer CLI with Shared State

**What:** Use Typer's callback and context to share config and flags across commands.

```python
# core/cli.py
import typer
from .config import load_config
from .orchestrator import Orchestrator

app = typer.Typer(help="MiniLegion — LLM-assisted work protocol.")

# Shared state via module-level or context
_state: dict = {}

@app.callback()
def main(
    fast: bool = typer.Option(False, "--fast", help="Skip research and design phases"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen without executing"),
):
    _state['config'] = load_config()
    _state['fast'] = fast
    _state['dry_run'] = dry_run

@app.command()
def research():
    """Run the research phase."""
    orch = Orchestrator(_state['config'], fast=_state['fast'])
    orch.run_stage("research", dry_run=_state['dry_run'])

# ... repeat for each command
```

### Pattern 5: Dual Output Writer

**What:** Every stage produces both `.md` and `.json`. The writer handles both atomically.

```python
# core/repo.py
from pathlib import Path
import json

def write_stage_output(
    project_dir: Path,
    stage: str,
    json_data: dict,
    markdown: str,
) -> None:
    """Write both .md and .json for a stage atomically."""
    json_path = project_dir / f"{stage.upper()}.json"
    md_path = project_dir / f"{stage.upper()}.md"

    # Write JSON first (machine artifact)
    json_path.write_text(json.dumps(json_data, indent=2) + "\n", encoding="utf-8")

    # Then markdown (human artifact)
    md_path.write_text(markdown, encoding="utf-8")
```

### Pattern 6: Config-Driven Role-to-Engine Mapping

**What:** `minilegion.config.json` maps each role to a specific LLM engine + model.

```json
{
  "engines": {
    "default": {
      "adapter": "openai",
      "model": "gpt-4o",
      "temperature": 0.0,
      "max_tokens": 4096,
      "timeout": 120
    }
  },
  "roles": {
    "researcher": { "engine": "default" },
    "designer":   { "engine": "default" },
    "planner":    { "engine": "default" },
    "builder":    { "engine": "default" },
    "reviewer":   { "engine": "default" }
  },
  "project_dir": "project-ai"
}
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: God Orchestrator
**What:** Putting all logic (prompting, validation, state, I/O) into one giant `orchestrator.py`.
**Why bad:** Untestable, impossible to understand, every change risks breaking everything.
**Instead:** Orchestrator is a thin composition layer. Each concern (validation, guardrails, prompts, I/O) lives in its own module.

### Anti-Pattern 2: State Mutation Without Approval
**What:** Updating STATE.json during LLM call or validation, then rolling back on rejection.
**Why bad:** Crashes during rollback leave corrupted state. Violates the safety invariant.
**Instead:** Compute new state as a Python dict. Only write to disk after approval gate passes.

### Anti-Pattern 3: Schema Inside Prompt Templates
**What:** Embedding JSON schema definitions inside prompt strings.
**Why bad:** Schemas change independently of prompts. Duplication leads to drift.
**Instead:** Load schema from `schemas/` directory. Reference in prompt by description, pass as structured context.

### Anti-Pattern 4: Adapter-Aware Orchestrator
**What:** Orchestrator contains `if adapter == "openai": ... elif adapter == "anthropic": ...`
**Why bad:** Defeats the purpose of the adapter pattern. Adding a new LLM requires modifying orchestrator.
**Instead:** Orchestrator calls `adapter.call()`. Adapter selection happens once at startup in `config.py`.

### Anti-Pattern 5: Untyped State
**What:** Using raw dicts for state with string keys everywhere: `state["current_phase"]`.
**Why bad:** Typos cause silent bugs. No IDE autocomplete. No validation at boundaries.
**Instead:** Use dataclasses or TypedDicts for state representation in Python. Serialize to/from JSON at the repo boundary.

---

## Key Architectural Decisions for Roadmap

| Decision | Impact on Build Order |
|----------|----------------------|
| State machine is dict-based, not library | No external dependency; build in Phase 1 |
| Adapter ABC before concrete impl | Define contract first; OpenAI adapter is Phase 3 |
| Guardrails as pure functions | Testable immediately; build in Phase 2 before any LLM work |
| Flat layout with `run.py` | No packaging infrastructure needed; just `python run.py` |
| jsonschema for validation | Pydantic is primary validator; jsonschema optional for standalone schema files |
| Typer for CLI | Standard choice; build CLI last (Phase 5) since it's just routing |
| Prompts as Python modules | Can unit test prompt construction without LLM calls |
| Dual output (md+json) in separate calls | Sprint 1 keeps it simple; one LLM call produces JSON, markdown is generated from JSON |

## Sources

- Python Enum/StrEnum: https://docs.python.org/3/library/enum.html (HIGH confidence, official docs)
- Typer CLI framework: https://typer.tiangolo.com/ (HIGH confidence, official docs; wraps Click internally)
- Click CLI framework: https://click.palletsprojects.com/en/stable/ (HIGH confidence, underlying engine for Typer)
- OpenAI Python SDK: https://github.com/openai/openai-python (HIGH confidence, official repo, v2.26.0)
- jsonschema: https://pypi.org/project/jsonschema/ (HIGH confidence, v4.26.0, Production/Stable)
- Python packaging src vs flat layout: https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ (HIGH confidence, official PyPA)
- Aider architecture reference: https://github.com/Aider-AI/aider (MEDIUM confidence, real-world LLM CLI tool pattern analysis)
