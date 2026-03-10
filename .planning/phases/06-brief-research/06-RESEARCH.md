# Phase 6: Brief & Research Stage - Research

**Researched:** 2026-03-10
**Domain:** Python CLI command implementation, codebase scanning, LLM pipeline integration
**Confidence:** HIGH — all findings verified directly against existing codebase source code

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Brief Command Behavior**
- `minilegion brief "some text"` creates BRIEF.md from the provided text, replacing BRIEF_TEMPLATE content with the user's text as the `## Overview` section (structured: Overview heading + raw text)
- If no text argument provided, read from stdin via `typer.get_text_stream("stdin").read()` — supports piped input AND interactive multi-line entry (terminated by EOF / Ctrl+D)
- After BRIEF.md is created, call `approve_brief()` to gate state transition — rejection leaves STATE.json unchanged (APRV-06)
- On approval: call `sm.transition(Stage.BRIEF)` and `save_state()` to advance state, then print success
- State transitions: INIT → BRIEF (brief command advances to BRIEF stage)
- BRIEF.md written atomically via `write_atomic()` before approval gate (file exists even if rejected, per append-only artifact principle)

**Deep Context Scanner**
- Deep context module in `minilegion/core/context_scanner.py`
- Entry function: `scan_codebase(project_dir: Path, config: MiniLegionConfig) -> str` returning a formatted text blob
- Configurable limits via `MiniLegionConfig` extensions: `scan_max_depth: int = 5`, `scan_max_files: int = 200`, `scan_max_file_size_kb: int = 100`
- Tech stack detection: read config files at root — `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`
- Import extraction: Python (`import X`, `from X import Y`), JS/TS (`import ... from '...'`, `require('...')`), Go (`import "..."`)
- Naming convention detection: detect snake_case vs camelCase vs PascalCase from identifiers in source files
- Directory structure: top-level dirs + first 2 levels, filtered (ignore `.git`, `__pycache__`, `node_modules`, `.venv`, `dist`, `build`)
- Output: structured text blob with sections: `## Tech Stack`, `## Directory Structure`, `## Key Files`, `## Import Patterns`, `## Naming Conventions`

**Research Command Implementation**
- `research` command: load config → load state → `check_preflight(Stage.RESEARCH, project_dir)` → `scan_codebase` → load + render researcher prompt → call adapter → `validate_with_retry` → `save_dual` → `approve_research` → transition state
- On approval: `sm.transition(Stage.RESEARCH)` and `save_state()`
- Prompt rendering: `load_prompt("researcher")`, then `render_prompt(user_template, project_name=..., brief_content=..., codebase_context=...)`
- RESEARCH.json and RESEARCH.md saved to `project_dir/` using `save_dual(data, project_dir/"RESEARCH.json", project_dir/"RESEARCH.md")`

**Error Handling & UX**
- Pre-flight failure: print red error message and exit code 1
- Approval rejection: print yellow "Rejected" message and exit code 0 (not an error)
- LLM/API errors: print red error message with exception text, exit code 1
- All state mutations happen AFTER all I/O and LLM calls succeed

**Commands.py Refactoring**
- Replace `_pipeline_stub` call in `brief()` and `research()` with real implementations
- Keep `_pipeline_stub` for `design`, `plan`, `execute`, `review` (still stubs)
- No new CLI flags needed for Phase 6

### OpenCode's Discretion
- Exact format of the BRIEF.md output (heading structure, section titles)
- Scanner output format details (exact section headings, ordering of info)
- Whether to show a progress indicator during LLM call (`typer.echo("Running researcher...")` is sufficient)
- Test approach for scanner (unit tests with temp file trees vs integration tests)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BRIEF-01 | User can run `minilegion brief "<text>"` to create BRIEF.md from free-text input | `brief()` command stub exists in commands.py; `write_atomic()` and `BRIEF_TEMPLATE` already present |
| BRIEF-02 | If no text argument provided, user is prompted via stdin | `text: str \| None = None` signature already correct; `typer.get_text_stream("stdin")` is the pattern |
| BRIEF-03 | After BRIEF.md creation, `approve_brief()` is called before state transitions | `approve_brief(state, state_path, brief_content)` signature confirmed; raises `ApprovalError` on rejection |
| RSCH-01 | Deep context scans codebase: detects tech stack from config files | New module `context_scanner.py`; config file list locked in decisions |
| RSCH-02 | Deep context scans files up to configurable depth, max file count, and max file size | `MiniLegionConfig` needs 3 new fields with defaults (backward compatible) |
| RSCH-03 | Deep context extracts imports/exports from Python, JS/TS, and Go source files | Regex patterns needed for all 3 languages; Python and JS/TS are primary, Go required |
| RSCH-04 | Deep context detects naming conventions, directory structure patterns, and test patterns | Identifier regex to classify snake_case/camelCase/PascalCase; directory walk |
| RSCH-05 | Researcher role receives scanned context + BRIEF.md and produces RESEARCH.json + RESEARCH.md | `load_prompt("researcher")` + `render_prompt()` wires to `OpenAIAdapter` + `validate_with_retry` |
| RSCH-06 | RESEARCH.json contains all required fields | `ResearchSchema` already has all 11 required fields (confirmed in schemas.py) |
| RSCH-07 | Researcher prompt enforces "explore, don't design" | `prompts/researcher.md` already contains "explore, don't design" instruction (confirmed in file) |
</phase_requirements>

---

## Summary

Phase 6 is purely an **integration and new-module** phase. All infrastructure is in place from Phases 1–5. The work has three distinct concerns:

1. **Brief command** — replace the `_pipeline_stub` call with real logic: read text or stdin, write BRIEF.md atomically, call `approve_brief()`, transition state on approval.
2. **Context scanner** — new stdlib-only module `context_scanner.py` that walks the filesystem and produces a human-readable text blob for prompt injection. No external dependencies. Designed for testability with `tmp_path`.
3. **Research command** — orchestrate existing infrastructure: preflight → scan → prompt render → LLM call → validate+retry → save_dual → approve → transition state.

The most complex new piece is the context scanner, which must implement per-language import regex, configurable depth/file/size limits, and naming convention detection — all without introducing new dependencies.

**Primary recommendation:** Implement in 3 focused plans: (1) config extensions + context scanner, (2) brief command, (3) research command orchestration. Scanner is the largest standalone unit and should be Plan 1 with heavy unit tests using synthetic `tmp_path` trees.

---

## Standard Stack

### Core (all already installed/available)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Python stdlib | 3.10+ | `os.walk`, `re`, `pathlib.Path` | Scanner uses only stdlib — no new deps |
| `typer` | ≥0.24.0 | CLI input, colored output, stdin | `typer.get_text_stream("stdin")` for stdin input |
| `pydantic` | ≥2.12.0 | Config model extension, ResearchSchema validation | Add 3 fields to `MiniLegionConfig` |
| `openai` | ≥1.0 | LLM calls via `OpenAIAdapter` | Already wired; `call_for_json()` is the method to use |

### Key Existing Infrastructure (reuse without modification)

| Asset | Location | How Used in Phase 6 |
|-------|----------|---------------------|
| `write_atomic()` | `core/file_io.py` | BRIEF.md write, RESEARCH.json + RESEARCH.md write (via `save_dual`) |
| `approve_brief()` | `core/approval.py` | Post-brief approval gate |
| `approve_research()` | `core/approval.py` | Post-research approval gate |
| `check_preflight()` | `core/preflight.py` | Research needs BRIEF.md + `brief_approved` — already declared |
| `validate_with_retry()` | `core/retry.py` | LLM output validation with retry loop |
| `save_dual()` | `core/renderer.py` | Saves RESEARCH.json + RESEARCH.md atomically |
| `load_prompt()` / `render_prompt()` | `prompts/loader.py` | Loads researcher.md, injects `{{project_name}}`, `{{brief_content}}`, `{{codebase_context}}` |
| `OpenAIAdapter(config)` | `adapters/openai_adapter.py` | LLM calls — takes full `MiniLegionConfig`, NOT individual fields |
| `StateMachine`, `Stage` | `core/state.py` | State transition after approval |
| `ResearchSchema` | `core/schemas.py` | All 11 fields already defined; no schema changes needed |
| `MiniLegionConfig` | `core/config.py` | Needs 3 new scanner limit fields added |

**Installation:** No new packages required. All dependencies already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended New Module Structure

```
minilegion/
├── core/
│   ├── context_scanner.py   # NEW — scan_codebase() entry point
│   ├── config.py            # MODIFY — add scan_max_depth/files/size fields
│   └── ...                  # (all other core modules unchanged)
├── cli/
│   └── commands.py          # MODIFY — replace brief()/research() stubs
└── ...
tests/
├── test_context_scanner.py  # NEW
└── test_cli_brief_research.py  # NEW (or extend test_cli.py)
```

### Pattern 1: Brief Command — Atomic Write Then Gate

The brief command follows the **write-before-gate** pattern established in CONTEXT.md (append-only artifacts):

```python
# Source: commands.py pattern + CONTEXT.md decisions
@app.command()
def brief(text: Annotated[str | None, typer.Argument(help="Brief text")] = None) -> None:
    """Run the brief stage."""
    try:
        project_dir = find_project_dir()
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.BRIEF):
            typer.echo(typer.style(
                f"Cannot transition from {state.current_stage} to {Stage.BRIEF.value}",
                fg=typer.colors.RED,
            ))
            raise typer.Exit(code=1)

        # Read text or stdin
        if text is None:
            text = typer.get_text_stream("stdin").read().strip()

        brief_content = f"# Project Brief\n\n## Overview\n\n{text}\n"

        # Write atomically BEFORE approval gate (append-only artifact principle)
        write_atomic(project_dir / "BRIEF.md", brief_content)
        typer.echo(typer.style("BRIEF.md created.", fg=typer.colors.GREEN))

        # Approval gate — raises ApprovalError on rejection
        approve_brief(state, project_dir / "STATE.json", brief_content)

        # Mutation ONLY after confirmed approval
        sm.transition(Stage.BRIEF)
        state.current_stage = Stage.BRIEF.value
        state.add_history("brief", "Brief created and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(typer.style("Brief approved. Stage: brief", fg=typer.colors.GREEN))

    except ApprovalError:
        typer.echo(typer.style("Brief rejected. Stage unchanged.", fg=typer.colors.YELLOW))
        # exit code 0 — rejection is not an error
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

**Critical note on StateMachine + state sync:** After `sm.transition(Stage.BRIEF)`, the `StateMachine` updates `sm.current_stage` but the `ProjectState.current_stage` string field still holds the old value. You must also set `state.current_stage = Stage.BRIEF.value` before calling `save_state()`. This is a subtle sync requirement.

### Pattern 2: Context Scanner — Configurable Walk

```python
# Source: CONTEXT.md decisions + stdlib os.walk pattern
# minilegion/core/context_scanner.py

IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}

TECH_STACK_FILES = [
    "package.json", "requirements.txt", "pyproject.toml",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile",
]

def scan_codebase(project_dir: Path, config: MiniLegionConfig) -> str:
    """Scan codebase and return formatted text blob for LLM prompt injection."""
    parts = []
    parts.append(_scan_tech_stack(project_dir))
    parts.append(_scan_directory_structure(project_dir, config.scan_max_depth))
    files = _collect_files(project_dir, config)
    parts.append(_scan_imports(files))
    parts.append(_scan_naming_conventions(files))
    return "\n\n".join(p for p in parts if p)
```

### Pattern 3: Research Command — Full Orchestration

```python
# Source: CONTEXT.md decisions + existing infrastructure patterns
@app.command()
def research() -> None:
    """Run the research stage."""
    try:
        project_dir = find_project_dir()
        config = load_config(project_dir.parent)  # config is at parent of project-ai/
        state = load_state(project_dir / "STATE.json")
        sm = StateMachine(Stage(state.current_stage), state.approvals)

        if not sm.can_transition(Stage.RESEARCH):
            typer.echo(typer.style(..., fg=typer.colors.RED))
            raise typer.Exit(code=1)

        # Preflight (requires BRIEF.md + brief_approved)
        check_preflight(Stage.RESEARCH, project_dir)

        # Scan codebase
        typer.echo("Scanning codebase...")
        codebase_context = scan_codebase(project_dir, config)

        # Load and render researcher prompt
        system_prompt, user_template = load_prompt("researcher")
        brief_content = (project_dir / "BRIEF.md").read_text(encoding="utf-8")
        project_name = project_dir.parent.name  # or read from config
        user_message = render_prompt(
            user_template,
            project_name=project_name,
            brief_content=brief_content,
            codebase_context=codebase_context,
        )

        # LLM call
        typer.echo("Running researcher...")
        adapter = OpenAIAdapter(config)  # Takes full config, NOT individual fields

        def llm_call(prompt: str) -> str:
            # NOTE: system_prompt is fixed; prompt is the user message (with retry feedback appended)
            response = adapter.call_for_json(system_prompt, prompt)
            return response.content

        # validate_with_retry signature: (llm_call, prompt, artifact_name, config, project_dir)
        research_data = validate_with_retry(
            llm_call, user_message, "research", config, project_dir
        )

        # Save dual output
        save_dual(research_data, project_dir / "RESEARCH.json", project_dir / "RESEARCH.md")
        typer.echo(typer.style("RESEARCH.json + RESEARCH.md saved.", fg=typer.colors.GREEN))

        # Approval gate
        research_md = (project_dir / "RESEARCH.md").read_text(encoding="utf-8")
        approve_research(state, project_dir / "STATE.json", research_md)

        # State mutation after approval
        sm.transition(Stage.RESEARCH)
        state.current_stage = Stage.RESEARCH.value
        state.add_history("research", "Research completed and approved")
        save_state(state, project_dir / "STATE.json")
        typer.echo(typer.style("Research approved. Stage: research", fg=typer.colors.GREEN))

    except ApprovalError:
        typer.echo(typer.style("Research rejected. Stage unchanged.", fg=typer.colors.YELLOW))
    except MiniLegionError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
```

### Pattern 4: Import Extraction Regex (all 3 languages)

```python
# Source: CONTEXT.md decisions — all 3 languages required (RSCH-03)

# Python: "import X" and "from X import Y"
PYTHON_IMPORT_RE = re.compile(
    r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))',
    re.MULTILINE
)

# JS/TS: "import ... from '...'" and "require('...')"
JS_IMPORT_RE = re.compile(
    r'''(?:import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))''',
    re.MULTILINE
)

# Go: import "..." (single) and import ( "..." ) (multi-line block)
GO_IMPORT_RE = re.compile(
    r'import\s+(?:"([^"]+)"|(?:\(\s*((?:[^)]*"[^"]*"[^)]*)*)\s*\)))',
    re.MULTILINE | re.DOTALL
)
```

### Pattern 5: Naming Convention Detection

```python
# Source: CONTEXT.md — detect snake_case, camelCase, PascalCase
SNAKE_CASE_RE = re.compile(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b')
CAMEL_CASE_RE = re.compile(r'\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b')
PASCAL_CASE_RE = re.compile(r'\b[A-Z][a-zA-Z0-9]+\b')

def detect_naming_convention(text: str) -> str:
    """Return dominant naming convention from source file content."""
    snake = len(SNAKE_CASE_RE.findall(text))
    camel = len(CAMEL_CASE_RE.findall(text))
    pascal = len(PASCAL_CASE_RE.findall(text))
    counts = {"snake_case": snake, "camelCase": camel, "PascalCase": pascal}
    return max(counts, key=counts.get)
```

### Anti-Patterns to Avoid

- **Calling `OpenAIAdapter(model=..., api_key_env=..., timeout=...)`:** The actual constructor takes `OpenAIAdapter(config: MiniLegionConfig)` — one argument only. The CONTEXT.md description of the adapter call is slightly simplified; check the actual signature.
- **Calling `validate_with_retry(llm_call, "research", config.max_retries, project_dir)`:** The actual signature is `validate_with_retry(llm_call, prompt, artifact_name, config, project_dir)` — takes full `MiniLegionConfig`, not `max_retries` int. `prompt` is the 2nd positional arg.
- **Reading state into StateMachine but not syncing back:** After `sm.transition(target)`, the `StateMachine` updates `sm.current_stage` but `state.current_stage` (ProjectState string) still holds the old value. Always set `state.current_stage = target.value` before `save_state()`.
- **Mutating state before approval:** Never call `sm.transition()` or `save_state()` before `approve_*()` returns True. The `ApprovalError` exception is the mechanism that prevents mutation.
- **Scanner circular import risk:** `context_scanner.py` imports from `config.py`. `config.py` imports from `exceptions.py`. This chain is fine. Do NOT import from `commands.py` or `cli/` from scanner.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom temp+rename | `write_atomic()` already in `core/file_io.py` | Already handles temp file creation, fsync, os.replace, cleanup |
| Approval Y/N prompt | `input()` or `typer.prompt()` | `approve_brief()` / `approve_research()` in `core/approval.py` | Already implements APRV-06 byte-identical rejection guarantee |
| LLM retry with error feedback | Custom retry loop | `validate_with_retry()` in `core/retry.py` | Already handles fixups, error summarization, RAW_DEBUG capture |
| JSON + MD dual output | Custom write pair | `save_dual()` in `core/renderer.py` | Already dispatches to `render_research_md()` atomically |
| Prompt variable injection | `str.format()` or f-strings | `render_prompt()` in `prompts/loader.py` | Already detects unresolved `{{placeholders}}` and raises ConfigError |
| Pre-flight validation | Manual file existence checks | `check_preflight(Stage.RESEARCH, project_dir)` | Already declares BRIEF.md + brief_approved requirements for RESEARCH stage |
| State transition validation | Manual stage comparison | `StateMachine.can_transition()` / `sm.transition()` | Already enforces valid/invalid transitions with clear errors |

**Key insight:** Phase 6 is primarily a wiring phase. 80% of the hard infrastructure was built in Phases 1–5. The main new code is: (1) the context scanner module (~150–200 lines), (2) the brief command body (~30 lines replacing the stub call), and (3) the research command body (~40 lines replacing the stub call).

---

## Common Pitfalls

### Pitfall 1: Signature Mismatch — OpenAIAdapter Constructor

**What goes wrong:** CONTEXT.md says `OpenAIAdapter(model=config.get_engine("researcher"), api_key_env=config.api_key_env, timeout=config.timeout)` but the real constructor is `OpenAIAdapter(config: MiniLegionConfig)`. Passing keyword args will cause TypeError.

**Why it happens:** The CONTEXT.md simplified the call pattern for readability.

**How to avoid:** Always call `OpenAIAdapter(config)` with the full config object. The adapter calls `config.get_engine()` and `config.api_key_env` internally.

**Verification:** `inspect.signature(OpenAIAdapter.__init__)` → `(self, config: MiniLegionConfig) -> None`

---

### Pitfall 2: validate_with_retry Prompt vs. Artifact Name Position

**What goes wrong:** Calling `validate_with_retry(llm_call, "research", config, project_dir)` skips the `prompt` argument, causing the artifact_name to be used as the prompt string.

**Why it happens:** CONTEXT.md described the call as `validate_with_retry(llm_call, "research", config.max_retries, project_dir)` which doesn't match the actual signature.

**How to avoid:** Full signature: `validate_with_retry(llm_call, prompt, artifact_name, config, project_dir)`. The `prompt` arg (user_message string) is required as 2nd positional. Pass full `MiniLegionConfig` as 4th arg (not `max_retries` int).

**Verification:** `inspect.signature(validate_with_retry)` → `(llm_call, prompt: str, artifact_name: str, config: MiniLegionConfig, project_dir: Path)`

---

### Pitfall 3: StateMachine/ProjectState Sync Gap

**What goes wrong:** After `sm.transition(Stage.BRIEF)`, the `StateMachine.current_stage` is updated in memory, but `state.current_stage` (the ProjectState Pydantic model string field) still holds `"init"`. `save_state(state, ...)` then writes `"init"` to disk.

**Why it happens:** `StateMachine` and `ProjectState` are separate objects. The existing `_pipeline_stub` only calls `sm.can_transition()` — it doesn't demonstrate the full transition pattern.

**How to avoid:** After `sm.transition(target)`, always set `state.current_stage = target.value` explicitly before calling `save_state()`.

**Warning signs:** Tests that check `load_state(...)["current_stage"]` after `brief`/`research` command still show `"init"`.

---

### Pitfall 4: File Encoding on Windows (Scanner)

**What goes wrong:** `open(path).read()` uses the system default encoding (cp1252 on Windows) and raises `UnicodeDecodeError` on UTF-8 source files with non-ASCII characters.

**Why it happens:** Python's default `open()` uses `locale.getpreferredencoding()` which is not UTF-8 on Windows.

**How to avoid:** Always pass `encoding="utf-8", errors="replace"` (or `"ignore"`) when reading source files in the scanner. The `errors="replace"` strategy lets the scanner continue past problematic files without crashing.

**Code:**
```python
try:
    content = path.read_text(encoding="utf-8", errors="replace")
except OSError:
    continue  # Skip unreadable files
```

---

### Pitfall 5: Scanner Depth Counting Off-By-One

**What goes wrong:** Depth is measured as number of directory levels below `project_dir`. A file at `project_dir/a/b/file.py` is at depth 2. A common bug: comparing depth against `scan_max_depth` with the wrong comparison (≤ vs. <) resulting in scanning one level too deep or too shallow.

**Why it happens:** Off-by-one in walk depth calculation.

**How to avoid:** Compute depth as `len(Path(dirpath).relative_to(project_dir).parts)`. A root file is depth 0. Use `if depth >= config.scan_max_depth: dirs[:] = []` to prune `os.walk` in-place (the standard pattern for limiting depth in os.walk).

```python
for dirpath, dirs, files in os.walk(project_dir):
    depth = len(Path(dirpath).relative_to(project_dir).parts)
    # Prune ignored dirs in-place (modifies dirs to control os.walk traversal)
    dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
    if depth >= config.scan_max_depth:
        dirs[:] = []  # Don't recurse deeper
```

---

### Pitfall 6: Stdin in Tests

**What goes wrong:** Tests that invoke the CLI `brief` command without text arg hang waiting for stdin input, because `typer.get_text_stream("stdin").read()` blocks.

**Why it happens:** The CliRunner doesn't automatically close stdin.

**How to avoid:** Use `runner.invoke(app, ["brief"], input="my brief text\n")` in CliRunner — the `input` parameter provides stdin content and closes it. Test the stdin path explicitly with `input="..."`.

---

### Pitfall 7: File Count Exhaustion Before max_files

**What goes wrong:** Scanner iterates all files and reads them, tracking count globally across the entire walk, but the count check happens after reading. Large codebases may read slightly more files than `scan_max_files` before the count check triggers.

**How to avoid:** Check the running count BEFORE reading each file:

```python
files_read = 0
for dirpath, dirs, files in os.walk(project_dir):
    for fname in files:
        if files_read >= config.scan_max_files:
            break  # Inner loop break
        fpath = Path(dirpath) / fname
        # size check before reading
        if fpath.stat().st_size > config.scan_max_file_size_kb * 1024:
            continue
        content = fpath.read_text(encoding="utf-8", errors="replace")
        files_read += 1
```

---

### Pitfall 8: Circular Import — context_scanner → commands

**What goes wrong:** If `context_scanner.py` imports anything from `minilegion.cli`, it creates a circular import because `cli/commands.py` imports from `core/`.

**Why it happens:** Easy to accidentally add `from minilegion.cli.commands import find_project_dir` in scanner.

**How to avoid:** `context_scanner.py` must only import from `minilegion.core.config` and stdlib. The `scan_codebase(project_dir, config)` signature takes `project_dir` as an argument — no need to import `find_project_dir` from commands.

---

### Pitfall 9: Researcher Prompt load_config Path

**What goes wrong:** `load_config(project_dir)` passes the `project-ai/` path directly, but `load_config` builds the path as `project_dir / "project-ai" / "minilegion.config.json"` — double-nesting `project-ai/`.

**Why it happens:** `find_project_dir()` returns the `project-ai/` subdirectory, but `load_config()` expects the **parent** directory (the root containing `project-ai/`).

**How to avoid:** Call `load_config(project_dir.parent)` where `project_dir` is the result of `find_project_dir()`.

**Verification:** `load_config` in `config.py` line 41: `config_path = project_dir / "project-ai" / "minilegion.config.json"`.

---

## Code Examples

### MiniLegionConfig Extension

```python
# Source: minilegion/core/config.py — add 3 fields with defaults
class MiniLegionConfig(BaseModel):
    """Configuration for a MiniLegion project."""
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    timeout: int = 120
    max_retries: int = 2
    engines: dict[str, str] = Field(default_factory=dict)
    # New scanner limits (Phase 6) — all have defaults for backward compatibility
    scan_max_depth: int = 5
    scan_max_files: int = 200
    scan_max_file_size_kb: int = 100
```

### Scanner Tech Stack Detection

```python
# Source: CONTEXT.md decisions
TECH_STACK_FILES = [
    "package.json", "requirements.txt", "pyproject.toml",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile",
]

def _scan_tech_stack(project_dir: Path) -> str:
    """Detect tech stack from root-level config files."""
    found = []
    for filename in TECH_STACK_FILES:
        fpath = project_dir / filename
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                found.append(f"### {filename}\n\n```\n{content[:500]}\n```")
            except OSError:
                found.append(f"### {filename}\n\n(unreadable)")
    if not found:
        return ""
    return "## Tech Stack\n\n" + "\n\n".join(found)
```

### Scanner Directory Structure

```python
# Source: CONTEXT.md — top-level dirs + first 2 levels, filtered
def _scan_directory_structure(project_dir: Path, max_depth: int) -> str:
    """Build directory tree (max 2 levels, filtered)."""
    lines = [f"{project_dir.name}/"]
    display_depth = min(2, max_depth)  # Never show more than 2 levels for structure

    for dirpath, dirs, files in os.walk(project_dir):
        depth = len(Path(dirpath).relative_to(project_dir).parts)
        dirs[:] = [d for d in sorted(dirs) if d not in IGNORED_DIRS]
        if depth >= display_depth:
            dirs[:] = []
        indent = "  " * (depth + 1)
        for d in dirs:
            lines.append(f"{indent}{d}/")
        for f in sorted(files)[:10]:  # Limit files listed per dir
            lines.append(f"{indent}{f}")

    return "## Directory Structure\n\n```\n" + "\n".join(lines) + "\n```"
```

### test_context_scanner.py Pattern

```python
# Source: CONTEXT.md — scanner designed for testability with tmp_path
def test_scan_respects_max_depth(tmp_path):
    """Scanner stops at configured depth."""
    deep = tmp_path / "a" / "b" / "c" / "deep.py"
    deep.parent.mkdir(parents=True)
    deep.write_text("import os", encoding="utf-8")
    shallow = tmp_path / "a" / "shallow.py"
    shallow.write_text("import sys", encoding="utf-8")

    config = MiniLegionConfig(scan_max_depth=2, scan_max_files=200, scan_max_file_size_kb=100)
    result = scan_codebase(tmp_path, config)

    assert "shallow.py" in result or "sys" in result
    assert "deep.py" not in result  # Beyond depth 2
```

### CLI Brief Test Pattern with Stdin

```python
# Source: typer.testing.CliRunner pattern
from typer.testing import CliRunner
runner = CliRunner()

def test_brief_reads_stdin(tmp_project_dir, monkeypatch):
    monkeypatch.chdir(tmp_project_dir)
    # Set up STATE.json at init stage
    _write_init_state(tmp_project_dir / "project-ai")
    # Mock approval
    monkeypatch.setattr("minilegion.core.approval.typer.confirm", lambda *a, **kw: True)

    result = runner.invoke(app, ["brief"], input="my brief text\n")  # stdin via input=

    assert result.exit_code == 0
    assert (tmp_project_dir / "project-ai" / "BRIEF.md").exists()
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `_pipeline_stub` (validates transition, prints stub msg) | Real implementation (reads/writes files, calls LLM, manages state) | Phase 6 replaces 2 of 6 stub calls |
| Manual LLM call + manual JSON parse | `validate_with_retry()` + `save_dual()` + approval gates | All infrastructure exists; Phase 6 just wires it up |
| `MiniLegionConfig` with 6 fields | 9 fields (3 scanner limits added) | Backward compatible — all new fields have defaults |

---

## Open Questions

1. **`load_config` path — project_dir vs. parent**
   - What we know: `find_project_dir()` returns `cwd/project-ai/`. `load_config()` appends `"project-ai"` to the path it receives.
   - What's unclear: The research command must call `load_config(project_dir.parent)` (i.e., the CWD), not `load_config(project_dir)`. This is confirmed by reading config.py line 41.
   - Recommendation: Always call `load_config(Path.cwd())` or `load_config(project_dir.parent)` where `project_dir = find_project_dir()`.

2. **project_name for prompt rendering**
   - What we know: `render_prompt(user_template, project_name=..., ...)` requires a project_name. The researcher.md USER_TEMPLATE has `{{project_name}}`.
   - What's unclear: There's no `name` field in `MiniLegionConfig` or `ProjectState`.
   - Recommendation: Use `project_dir.parent.name` (the directory name the user chose in `minilegion init <name>`). This is pragmatic and requires no new state.

3. **Scanner output when codebase is empty (no source files)**
   - What we know: The scanner MUST return a non-empty string (it feeds `{{codebase_context}}` in the prompt; empty string would confuse the LLM).
   - Recommendation: Return a minimal placeholder string `"No source files found."` for each section that has no content. The `render_prompt()` unresolved placeholder check ensures `codebase_context` is always populated.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥ 8.0 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` `testpaths = ["tests"]` |
| Quick run command | `python -m pytest tests/test_context_scanner.py tests/test_cli_brief_research.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRIEF-01 | `brief "text"` creates BRIEF.md with Overview section | unit + CLI | `pytest tests/test_cli_brief_research.py::TestBriefCommand::test_brief_creates_brief_md -x` | ❌ Wave 0 |
| BRIEF-02 | `brief` with no arg reads from stdin | CLI | `pytest tests/test_cli_brief_research.py::TestBriefCommand::test_brief_stdin_input -x` | ❌ Wave 0 |
| BRIEF-03 | Approval gate called; rejection leaves STATE.json unchanged | CLI | `pytest tests/test_cli_brief_research.py::TestBriefCommand::test_brief_rejection_no_state_change -x` | ❌ Wave 0 |
| RSCH-01 | Tech stack detection finds package.json/requirements.txt/pyproject.toml | unit | `pytest tests/test_context_scanner.py::TestTechStackDetection -x` | ❌ Wave 0 |
| RSCH-02 | Scanner respects max_depth, max_files, max_file_size_kb | unit | `pytest tests/test_context_scanner.py::TestScannerLimits -x` | ❌ Wave 0 |
| RSCH-03 | Import extraction for Python, JS/TS, Go | unit | `pytest tests/test_context_scanner.py::TestImportExtraction -x` | ❌ Wave 0 |
| RSCH-04 | Naming convention detection (snake_case, camelCase, PascalCase) | unit | `pytest tests/test_context_scanner.py::TestNamingConventions -x` | ❌ Wave 0 |
| RSCH-05 | `research` command produces RESEARCH.json + RESEARCH.md (mocked LLM) | CLI | `pytest tests/test_cli_brief_research.py::TestResearchCommand::test_research_produces_output -x` | ❌ Wave 0 |
| RSCH-06 | RESEARCH.json contains all 11 required ResearchSchema fields | unit (schema) | Already covered by `test_schemas.py` — ResearchSchema validates at import time | ✅ Existing |
| RSCH-07 | Researcher prompt contains "explore, don't design" | unit | `pytest tests/test_prompt_loader.py` (existing test covers prompt loading) | ✅ Existing |

### What to Unit Test — Scanner Behavior

```
test_context_scanner.py:
  TestTechStackDetection:
    - test_detects_pyproject_toml
    - test_detects_package_json
    - test_detects_requirements_txt
    - test_returns_empty_string_when_no_tech_files
    - test_truncates_large_config_files (file content capped at 500 chars)

  TestScannerLimits:
    - test_respects_max_depth: files below depth are excluded
    - test_respects_max_files: stops after N files collected
    - test_respects_max_file_size_kb: skips files larger than limit
    - test_default_config_values: MiniLegionConfig defaults are sane

  TestImportExtraction:
    - test_python_import_statement
    - test_python_from_import_statement
    - test_js_import_from_syntax
    - test_js_require_syntax
    - test_ts_import_syntax
    - test_go_import_single
    - test_go_import_block
    - test_empty_file_no_imports
    - test_mixed_language_files

  TestDirectoryStructure:
    - test_filters_ignored_dirs (.git, __pycache__, node_modules, .venv, dist, build)
    - test_shows_max_two_levels_only
    - test_empty_project_dir

  TestNamingConventions:
    - test_detects_snake_case_dominant
    - test_detects_camel_case_dominant
    - test_detects_pascal_case_dominant
    - test_empty_file_no_conventions

  TestScanCodebase:
    - test_returns_non_empty_string
    - test_output_has_required_sections (Tech Stack, Directory Structure, etc.)
    - test_unicode_files_dont_crash (encoding="utf-8", errors="replace")
    - test_empty_codebase_returns_placeholder
    - test_uses_configurable_limits (integration of all limits)
```

### What to Unit Test — Brief Creation

```
test_cli_brief_research.py:
  TestBriefCommand:
    - test_brief_creates_brief_md_with_text_arg
    - test_brief_content_contains_overview_heading
    - test_brief_writes_atomically (BRIEF.md exists even if approval rejected)
    - test_brief_stdin_input (runner.invoke input="...")
    - test_brief_stdin_empty_shows_error_or_creates_empty
    - test_brief_approval_accepted_transitions_state
    - test_brief_rejection_leaves_state_json_unchanged (byte-identical)
    - test_brief_rejection_exits_0 (not an error)
    - test_brief_without_project_dir_exits_1
    - test_brief_from_wrong_stage_exits_1 (e.g., already at RESEARCH)
```

### What to Unit Test — Research Command

```
test_cli_brief_research.py:
  TestResearchCommand:
    - test_research_calls_preflight (mock check_preflight raises PreflightError)
    - test_research_preflight_failure_exits_1
    - test_research_runs_scanner (mock scan_codebase, verify called)
    - test_research_calls_llm (mock adapter, verify call_for_json invoked)
    - test_research_saves_dual_output (RESEARCH.json + RESEARCH.md created)
    - test_research_approval_accepted_transitions_state
    - test_research_rejection_leaves_state_unchanged
    - test_research_rejection_exits_0
    - test_research_llm_error_exits_1 (LLMError raised)
    - test_research_missing_api_key_exits_1
    - test_research_validation_failure_saves_raw_debug (validation retry exhausted)
```

### Integration Tests

```
TestBriefResearchIntegration:
  - test_full_brief_then_research_flow: brief → approve → research → approve → state = "research"
    (Requires real temp file tree, mocked LLM call returning valid ResearchSchema JSON)
  - test_state_after_brief_is_brief_stage: current_stage == "brief" after approved brief
  - test_state_after_research_is_research_stage: current_stage == "research" after approved research
```

### Key Edge Cases to Cover

| Edge Case | Test Approach |
|-----------|--------------|
| Empty codebase (no source files) | `tmp_path` with only a README, verify no crash |
| `scan_max_files=1` hit immediately | Verify scanner exits after 1 file, not 0 or 2 |
| `scan_max_file_size_kb=0` — all files skipped | Verify graceful empty output |
| `scan_max_depth=0` — root files only | Verify subdirectory files excluded |
| File with non-UTF-8 bytes | Write `b"\xff\xfe"` to a .py file; verify no UnicodeDecodeError |
| `brief` with empty stdin (Ctrl+D immediately) | `runner.invoke(app, ["brief"], input="")` → verify behavior |
| Missing API key in environment | `monkeypatch.delenv("OPENAI_API_KEY")` → verify LLMError message |
| LLM returns invalid JSON (validation failure) | Mock `llm_call` to always return `"{}"` → verify RAW_DEBUG saved |
| research command without BRIEF.md present | Verify PreflightError → red message, exit 1 |
| research command without `brief_approved` | Verify PreflightError → red message, exit 1 |

### Pitfalls to Avoid in Tests

1. **Testing LLM calls without mocking:** Never call the real OpenAI API in tests. Use `unittest.mock.patch` on `adapter.call_for_json` or pass a mock `llm_call` callable to `validate_with_retry`. The existing pattern in `test_retry.py` and `test_openai_adapter.py` shows the standard mock approach.

2. **Windows encoding in test files:** When creating test source files with `tmp_path`, always use `path.write_text("content", encoding="utf-8")`. Do not rely on system default encoding.

3. **Mocking `typer.confirm` globally:** When testing the brief/research approval flow end-to-end via CliRunner, monkeypatch `minilegion.core.approval.typer.confirm` (not the generic `typer.confirm`). The existing `test_approval.py` demonstrates this pattern.

4. **CliRunner isolation:** Typer's CliRunner does NOT set a working directory. Always `monkeypatch.chdir(tmp_path)` before invoking commands that call `find_project_dir()` (which calls `Path.cwd()`).

5. **Checking file content vs. file existence:** For BRIEF.md and RESEARCH.json tests, always assert both that the file EXISTS and that it CONTAINS the expected content. File existence alone doesn't prove correct content.

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_context_scanner.py tests/test_cli_brief_research.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green (`379 + N new tests`) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_context_scanner.py` — covers RSCH-01, RSCH-02, RSCH-03, RSCH-04
- [ ] `tests/test_cli_brief_research.py` — covers BRIEF-01, BRIEF-02, BRIEF-03, RSCH-05

*(All other test infrastructure in place — `conftest.py`, `tmp_project_dir` fixture, CliRunner, monkeypatch patterns all established in existing tests)*

---

## Sources

### Primary (HIGH confidence)

- **Direct codebase inspection** — All patterns, signatures, and behaviors verified by reading actual source files:
  - `minilegion/adapters/openai_adapter.py` — `OpenAIAdapter(config: MiniLegionConfig)` constructor confirmed
  - `minilegion/core/retry.py` — `validate_with_retry(llm_call, prompt, artifact_name, config, project_dir)` signature confirmed
  - `minilegion/core/config.py` — Current 6 fields confirmed; load_config path behavior confirmed (line 41)
  - `minilegion/core/schemas.py` — `ResearchSchema` 11 fields confirmed; no changes needed
  - `minilegion/core/preflight.py` — RESEARCH stage requirements confirmed: `["BRIEF.md"]` + `["brief_approved"]`
  - `minilegion/core/approval.py` — `approve_brief(state, state_path, brief_content)` signature confirmed
  - `minilegion/core/renderer.py` — `save_dual(data, json_path, md_path)` confirmed; ResearchSchema renderer exists
  - `minilegion/prompts/loader.py` — `load_prompt("researcher")` + `render_prompt()` with `{{project_name}}`, `{{brief_content}}`, `{{codebase_context}}`
  - `minilegion/prompts/researcher.md` — "explore, don't design" instruction confirmed in SYSTEM section
  - `minilegion/cli/commands.py` — `brief()` stub signature `text: str | None = None` confirmed; `find_project_dir()` confirmed

- **Runtime verification** — Python subprocess used to confirm:
  - `OpenAIAdapter.__init__` signature: `(self, config: MiniLegionConfig) -> None`
  - `validate_with_retry` signature: `(llm_call, prompt: str, artifact_name: str, config: MiniLegionConfig, project_dir: Path)`
  - All 379 existing tests pass (`python -m pytest tests/ -q`)

### Secondary (MEDIUM confidence)

- **CONTEXT.md decisions** — User-confirmed implementation decisions from discussion phase. Note: CONTEXT.md contains minor simplifications of adapter/retry call patterns that don't match actual signatures — corrected in this research document.

### Tertiary (LOW confidence)

None — all critical claims are HIGH confidence from direct source code inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by reading actual source files
- Architecture patterns: HIGH — derived from existing patterns in codebase + locked CONTEXT.md decisions
- Pitfalls: HIGH — several discovered by directly comparing CONTEXT.md descriptions against actual source code signatures
- Test mapping: HIGH — existing test patterns (conftest, CliRunner, monkeypatch approval) all confirmed

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable codebase — no external dependency risk)
