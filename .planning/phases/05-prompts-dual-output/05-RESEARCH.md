# Phase 5: Prompts & Dual Output - Research

**Researched:** 2026-03-10
**Domain:** Prompt template infrastructure + programmatic Markdown rendering from Pydantic models
**Confidence:** HIGH

## Summary

Phase 5 delivers two independent subsystems: (1) a prompt loading and variable injection layer that reads role-specific Markdown template files from the `minilegion/prompts/` package using `importlib.resources`, and (2) a dual-output renderer that converts validated Pydantic models into human-readable Markdown alongside their JSON serialization.

Both subsystems are pure Python with zero external dependencies beyond what's already in the project. The prompt loader uses `importlib.resources.files()` (Python 3.9+, stable in 3.12) to read `.md` files from the prompts package, and a simple `re.sub` regex to replace `{{placeholder}}` variables. The renderer uses Pydantic's `model_dump_json(indent=2)` for JSON output and hand-crafted string formatting for Markdown output, saved via the existing `write_atomic()` function.

The implementation surface is well-bounded: 5 prompt `.md` files, 1 loader module, 1 renderer module, and their tests. There are no LLM calls, no network I/O, no complex state — this phase is entirely deterministic string processing and file I/O.

**Primary recommendation:** Keep it simple — `re.sub` for templates (no Jinja2), `importlib.resources.files()` for loading, hand-crafted f-string Markdown renderers per schema type, `write_atomic()` for all saves.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Prompts stored as plain Markdown files in `minilegion/prompts/` directory (package-level, importable)
- One file per role: `researcher.md`, `designer.md`, `planner.md`, `builder.md`, `reviewer.md`
- Each file has two sections delimited by markers: `<!-- SYSTEM -->` and `<!-- USER_TEMPLATE -->`
- SYSTEM section contains the system prompt (role definition, constraints, output format)
- USER_TEMPLATE section contains the user message template with `{{placeholder}}` variables
- Files read at runtime via `load_prompt(role: str) -> tuple[str, str]` returning `(system_prompt, user_template)`
- `minilegion/prompts/loader.py` module with `load_prompt()` and `render_prompt(template, **variables)`
- Uses `importlib.resources` (Python 3.9+) to load prompt files from the package
- Raises `ConfigError` if prompt file not found, missing sections, or unresolved placeholders
- All 5 prompts include JSON anchoring at START and END of system prompt
- User template does NOT repeat JSON instructions
- Placeholder variables per role are fixed (see CONTEXT.md for full list)
- Markdown renderer module in `minilegion/core/renderer.py`
- One render function per artifact type: `render_research_md(data: ResearchSchema) -> str`, etc.
- Convenience function: `save_dual(data: BaseModel, json_path: Path, md_path: Path) -> None`
- Markdown uses headers, bullet lists, tables — human-readable, not raw JSON dump
- Role behavioral constraints: Researcher="explore, don't design", Designer="design, don't plan", Planner="decompose, don't design", Builder="build, don't redesign", Reviewer="identify, don't correct"

### OpenCode's Discretion
- Exact wording of system prompts and user templates (following behavioral constraints)
- Internal structure of each prompt file (section ordering within SYSTEM block)
- Markdown rendering formatting details (table widths, heading levels, bullet styles)
- Whether `render_review_md()` uses a table or bullet list for findings
- Helper functions for common rendering patterns (list-to-bullets, dict-to-table)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRMT-01 | 5 role prompts (researcher, designer, planner, builder, reviewer) each with SYSTEM and USER_TEMPLATE sections | Prompt file format with `<!-- SYSTEM -->` / `<!-- USER_TEMPLATE -->` delimiters, loaded via `importlib.resources.files()` |
| PRMT-02 | All prompts enforce JSON-only output with anchoring instructions at start and end | JSON anchoring pattern at start+end of SYSTEM section; user template does not repeat |
| PRMT-03 | Prompts stored as markdown files in `prompts/` directory | Files stored in `minilegion/prompts/` package; `importlib.resources` handles both editable and installed access |
| PRMT-04 | USER_TEMPLATE uses `{{placeholder}}` syntax for variable injection | `re.sub(r'\{\{(\w+)\}\}', ...)` regex replacement in `render_prompt()` with missing-variable detection |
| DUAL-01 | Every LLM-produced artifact is saved in both .json and .md formats | `save_dual()` convenience function using `model_dump_json(indent=2)` + per-type render function + `write_atomic()` |
| DUAL-02 | Markdown is generated programmatically from parsed JSON — not by the LLM | Per-schema render functions accept Pydantic model instances and produce Markdown strings using Python string formatting |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `importlib.resources` | stdlib (3.12) | Load prompt `.md` files from package | Standard way to access package data files; works in editable installs, wheels, and zip imports |
| `re` | stdlib | `{{placeholder}}` regex replacement | Simple regex sufficient for mustache-like variable syntax; no external dependency needed |
| `pydantic` | >=2.12.0 | `model_dump_json(indent=2)` for JSON serialization | Already in project; `model_dump_json()` produces clean, deterministic JSON output |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `minilegion.core.file_io.write_atomic` | project | Atomic file writes for both JSON and MD | Every file save in `save_dual()` |
| `minilegion.core.exceptions.ConfigError` | project | Error handling for prompt loading | Missing prompt files, missing sections, unresolved placeholders |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `re.sub` for templates | Jinja2 | Jinja2 adds a dependency for trivial string replacement; `re.sub` is 5 lines of code and has no edge cases for this use case |
| `importlib.resources` | `pathlib.Path(__file__).parent` | `__file__`-relative paths fail in zip imports and some packaging scenarios; `importlib.resources` is the standard solution |
| Hand-crafted Markdown | Markdown library | No markdown library is needed — we're generating strings, not parsing them |

**Installation:**
```bash
# No new dependencies required — all stdlib + existing project deps
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── prompts/
│   ├── __init__.py          # Package marker (already exists)
│   ├── loader.py            # load_prompt() + render_prompt()
│   ├── researcher.md        # Researcher role prompt
│   ├── designer.md          # Designer role prompt
│   ├── planner.md           # Planner role prompt
│   ├── builder.md           # Builder role prompt
│   └── reviewer.md          # Reviewer role prompt
├── core/
│   ├── renderer.py          # render_*_md() + save_dual()
│   └── ...existing modules
```

### Pattern 1: Prompt File Format
**What:** Each `.md` file contains two sections separated by HTML comment markers.
**When to use:** Every role prompt file.
**Example:**
```markdown
<!-- SYSTEM -->
You MUST respond with valid JSON only. No markdown, no explanations, no code fences.

You are the Researcher role. Your job is to explore the codebase...
[role-specific instructions]
[output schema description]

CRITICAL: Your entire response must be a single valid JSON object. Nothing else.

<!-- USER_TEMPLATE -->
Project: {{project_name}}

## Brief
{{brief_content}}

## Codebase Context
{{codebase_context}}
```

### Pattern 2: Prompt Loader with importlib.resources
**What:** Load prompt files from the package using `importlib.resources.files()`, split on markers, return tuple.
**When to use:** `load_prompt()` function.
**Example:**
```python
# Source: Python 3.12 importlib.resources docs
from importlib import resources
from minilegion.core.exceptions import ConfigError

SYSTEM_MARKER = "<!-- SYSTEM -->"
USER_TEMPLATE_MARKER = "<!-- USER_TEMPLATE -->"

def load_prompt(role: str) -> tuple[str, str]:
    """Load a role prompt file and return (system_prompt, user_template)."""
    filename = f"{role}.md"
    try:
        content = (
            resources.files("minilegion.prompts")
            .joinpath(filename)
            .read_text("utf-8")
        )
    except FileNotFoundError:
        raise ConfigError(f"Prompt file not found: {filename}")

    if SYSTEM_MARKER not in content:
        raise ConfigError(f"Missing {SYSTEM_MARKER} in {filename}")
    if USER_TEMPLATE_MARKER not in content:
        raise ConfigError(f"Missing {USER_TEMPLATE_MARKER} in {filename}")

    # Split on markers and extract sections
    parts = content.split(USER_TEMPLATE_MARKER, 1)
    system_section = parts[0].split(SYSTEM_MARKER, 1)[1].strip()
    user_section = parts[1].strip()

    return system_section, user_section
```

### Pattern 3: Template Variable Injection
**What:** Replace `{{key}}` placeholders with provided variables, raising on missing.
**When to use:** `render_prompt()` function.
**Example:**
```python
import re
from minilegion.core.exceptions import ConfigError

def render_prompt(template: str, **variables: str) -> str:
    """Replace {{key}} placeholders with variable values."""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            raise ConfigError(
                f"Unresolved placeholder: {{{{{key}}}}} — "
                f"available variables: {sorted(variables.keys())}"
            )
        return variables[key]

    return re.sub(r"\{\{(\w+)\}\}", replacer, template)
```

### Pattern 4: Per-Schema Markdown Renderer
**What:** Each schema type gets a dedicated render function that produces structured Markdown.
**When to use:** `render_*_md()` functions in `renderer.py`.
**Example:**
```python
from minilegion.core.schemas import ResearchSchema

def render_research_md(data: ResearchSchema) -> str:
    """Render ResearchSchema as human-readable Markdown."""
    lines = ["# Research Report", ""]
    lines.append(f"## Project Overview\n\n{data.project_overview}\n")

    if data.tech_stack:
        lines.append("## Tech Stack\n")
        for item in data.tech_stack:
            lines.append(f"- {item}")
        lines.append("")

    if data.architecture_patterns:
        lines.append("## Architecture Patterns\n")
        for item in data.architecture_patterns:
            lines.append(f"- {item}")
        lines.append("")

    # ... additional sections for each field
    return "\n".join(lines)
```

### Pattern 5: save_dual Convenience Function
**What:** Save both JSON and Markdown representations using `write_atomic()`.
**When to use:** After every successful LLM call that produces a validated Pydantic model.
**Example:**
```python
from pathlib import Path
from pydantic import BaseModel
from minilegion.core.file_io import write_atomic

# Registry mapping schema types to render functions
_RENDERERS = {
    "ResearchSchema": render_research_md,
    "DesignSchema": render_design_md,
    "PlanSchema": render_plan_md,
    "ExecutionLogSchema": render_execution_log_md,
    "ReviewSchema": render_review_md,
}

def save_dual(data: BaseModel, json_path: Path, md_path: Path) -> None:
    """Save artifact as both JSON and Markdown using write_atomic."""
    # JSON output
    json_str = data.model_dump_json(indent=2)
    write_atomic(json_path, json_str)

    # Markdown output via type-specific renderer
    type_name = type(data).__name__
    renderer = _RENDERERS.get(type_name)
    if renderer is None:
        raise ValueError(f"No renderer registered for {type_name}")
    md_str = renderer(data)
    write_atomic(md_path, md_str)
```

### Anti-Patterns to Avoid
- **Jinja2 for simple substitution:** Adding a template engine dependency for `{{key}}` → `value` replacement is over-engineering. `re.sub` with a 5-line replacer handles it perfectly.
- **Reading prompt files with `open()` + `__file__`:** Breaks in zip-imported packages and some installation scenarios. Always use `importlib.resources`.
- **Asking the LLM to generate Markdown:** Violates DUAL-02. Markdown must be generated programmatically from the parsed JSON/Pydantic model.
- **Single monolithic render function:** Each schema has different fields and structure. One `render_md(data)` with `isinstance` checks becomes unwieldy. Use one function per type.
- **Storing prompts as Python strings:** Makes prompts hard to edit, hard to diff, and mixes concerns. Markdown files are human-editable and version-control friendly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template variable substitution | Custom parser | `re.sub(r"\{\{(\w+)\}\}", ...)` | Regex is stdlib, 5 lines, handles all `{{word_chars}}` cases |
| JSON serialization of models | Custom `to_json()` | `model_dump_json(indent=2)` | Pydantic handles all field types, enums, nested models, optional fields automatically |
| Package resource loading | `Path(__file__).parent / file` | `importlib.resources.files()` | Works in editable installs, wheels, zips — the standard since Python 3.9 |
| Atomic file writes | Custom temp+rename | `write_atomic()` (existing) | Already built and tested in Phase 1 — reuse it |

**Key insight:** This phase is pure string processing. Every building block already exists in stdlib or the project. The complexity is in getting the prompt content right (behavioral anchoring, JSON enforcement) and the Markdown formatting readable — not in the infrastructure code.

## Common Pitfalls

### Pitfall 1: Package Data Not Included in Wheel Builds
**What goes wrong:** `.md` files in `minilegion/prompts/` are not included when building a wheel/sdist because setuptools only includes `*.py` files by default.
**Why it happens:** No `[tool.setuptools.package-data]` configuration in `pyproject.toml`.
**How to avoid:** Add package-data configuration to `pyproject.toml`:
```toml
[tool.setuptools.package-data]
"minilegion.prompts" = ["*.md"]
```
**Warning signs:** `importlib.resources` raises `FileNotFoundError` when running from an installed wheel but works fine in editable mode.

### Pitfall 2: Marker Splitting Order Matters
**What goes wrong:** If `<!-- SYSTEM -->` appears after `<!-- USER_TEMPLATE -->` in the file, the split logic produces garbled output.
**Why it happens:** Splitting on one marker first assumes a specific order in the file.
**How to avoid:** Always split on `<!-- USER_TEMPLATE -->` first (it separates the two major sections), then extract the system content from the first half by splitting on `<!-- SYSTEM -->`. Validate that both markers exist before splitting.
**Warning signs:** System prompt contains user template content or vice versa.

### Pitfall 3: Unresolved Placeholders Silently Pass
**What goes wrong:** If `render_prompt()` doesn't check for leftover `{{...}}` patterns, a misspelled variable name results in the literal `{{placeholder}}` being sent to the LLM.
**Why it happens:** Simple string `.replace()` doesn't error on missing keys.
**How to avoid:** Use `re.sub` with a replacer function that raises `ConfigError` on any key not in the `variables` dict. Alternatively, after substitution, scan the result for remaining `{{...}}` patterns.
**Warning signs:** LLM receives prompts containing literal `{{variable_name}}` text.

### Pitfall 4: Markdown Renderer Missing Fields
**What goes wrong:** A Pydantic schema field is added or renamed but the corresponding Markdown renderer doesn't get updated, causing silent data omission in the `.md` output.
**Why it happens:** Renderers are hand-crafted strings, not auto-generated from the model.
**How to avoid:** Test that each render function's output contains a section for every non-empty field in a fully-populated test fixture. If a field has data, it must appear in the Markdown.
**Warning signs:** The `.json` has data that the `.md` doesn't show.

### Pitfall 5: JSON Anchoring Too Aggressive
**What goes wrong:** JSON enforcement instructions are so verbose they consume significant token budget, or the LLM over-focuses on format compliance at the expense of content quality.
**Why it happens:** Repeating JSON instructions too many times or making them too long.
**How to avoid:** Keep JSON anchoring to 1-2 sentences at the start and 1 sentence at the end of the SYSTEM prompt. Do NOT repeat in USER_TEMPLATE (already decided in CONTEXT.md). The adapter's `call_for_json()` already uses `response_format={"type": "json_object"}` which provides SDK-level enforcement.
**Warning signs:** LLM responses are valid JSON but shallow/low-quality content.

### Pitfall 6: Windows Line Endings in Prompt Files
**What goes wrong:** On Windows, `.md` files may have `\r\n` line endings that cause marker splitting to leave trailing `\r` in extracted content.
**Why it happens:** Git autocrlf or editor settings.
**How to avoid:** Use `.strip()` after splitting on markers. The `read_text('utf-8')` from `importlib.resources` returns the raw file content including whatever line endings exist.
**Warning signs:** System prompts end with `\r` characters.

## Code Examples

Verified patterns from the existing codebase and stdlib:

### Loading Package Resources (importlib.resources)
```python
# Source: Python 3.12 official docs — importlib.resources
from importlib import resources

# Modern API (Python 3.9+, recommended)
content = (
    resources.files("minilegion.prompts")
    .joinpath("researcher.md")
    .read_text("utf-8")
)
# Returns: str content of the file
```

### Pydantic model_dump_json for JSON Output
```python
# Source: Pydantic v2 — verified in project codebase
from minilegion.core.schemas import ResearchSchema

data = ResearchSchema(project_overview="test", tech_stack=["python"])
json_str = data.model_dump_json(indent=2)
# Returns: '{\n  "project_overview": "test",\n  "tech_stack": [\n    "python"\n  ],\n  ...'
```

### Atomic File Writes (existing project utility)
```python
# Source: minilegion/core/file_io.py (Phase 1)
from pathlib import Path
from minilegion.core.file_io import write_atomic

write_atomic(Path("project-ai/RESEARCH.json"), json_str)
write_atomic(Path("project-ai/RESEARCH.md"), md_str)
```

### ConfigError for Prompt Loading Failures
```python
# Source: minilegion/core/exceptions.py (Phase 1)
from minilegion.core.exceptions import ConfigError

# Prompt file not found
raise ConfigError("Prompt file not found: researcher.md")
# Missing section marker
raise ConfigError("Missing <!-- SYSTEM --> in researcher.md")
# Unresolved placeholder
raise ConfigError("Unresolved placeholder: {{missing_var}} — available variables: ['brief_content', 'project_name']")
```

### Markdown Rendering Helper Patterns
```python
def _bullets(items: list[str], heading: str) -> str:
    """Render a list as a Markdown bullet section. Returns empty string if list is empty."""
    if not items:
        return ""
    lines = [f"## {heading}\n"]
    for item in items:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _table(rows: list[dict], columns: list[str], heading: str) -> str:
    """Render a list of dicts as a Markdown table."""
    if not rows:
        return ""
    lines = [f"## {heading}\n"]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        cells = [str(row.get(col, "")) for col in columns]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources` for package data | `importlib.resources.files()` | Python 3.9 (2020) | No setuptools runtime dependency; faster, cleaner API |
| `importlib.resources.read_text()` (flat API) | `importlib.resources.files().joinpath().read_text()` | Python 3.9 | Flat API still works but files() is the modern recommendation |
| Jinja2 for all templates | Simple regex for simple cases | Ongoing | Jinja2 is overkill when templates only need `{{key}}` → value replacement |
| `model.json()` (Pydantic v1) | `model.model_dump_json()` (Pydantic v2) | Pydantic v2 (2023) | New API, old one deprecated |

**Deprecated/outdated:**
- `importlib.resources.read_text(package, resource)`: Still works in Python 3.12 but the `files()` API is recommended
- `pydantic.BaseModel.json()`: Deprecated in v2, use `model_dump_json()` instead

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_loader.py tests/test_renderer.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRMT-01 | 5 prompt files exist with SYSTEM+USER_TEMPLATE | unit | `pytest tests/test_loader.py::TestLoadPrompt -x` | Wave 0 |
| PRMT-02 | JSON anchoring at start+end of system prompt | unit | `pytest tests/test_loader.py::TestJsonAnchoring -x` | Wave 0 |
| PRMT-03 | Prompts loaded from package via importlib.resources | unit | `pytest tests/test_loader.py::TestLoadPrompt -x` | Wave 0 |
| PRMT-04 | {{placeholder}} replacement with missing-var detection | unit | `pytest tests/test_loader.py::TestRenderPrompt -x` | Wave 0 |
| DUAL-01 | save_dual saves both .json and .md | unit | `pytest tests/test_renderer.py::TestSaveDual -x` | Wave 0 |
| DUAL-02 | Markdown generated from Pydantic model, not LLM | unit | `pytest tests/test_renderer.py::TestRenderers -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_loader.py tests/test_renderer.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_loader.py` — covers PRMT-01, PRMT-02, PRMT-03, PRMT-04
- [ ] `tests/test_renderer.py` — covers DUAL-01, DUAL-02
- [ ] `minilegion/prompts/researcher.md` — first prompt file (needed for loader tests)

## Open Questions

1. **Package data inclusion for wheel builds**
   - What we know: Editable installs work fine because `importlib.resources.files()` resolves to the filesystem. Built wheels may not include `.md` files without explicit configuration.
   - What's unclear: Whether the project will ever be built as a wheel (it may only ever run in editable/dev mode).
   - Recommendation: Add `[tool.setuptools.package-data]` to `pyproject.toml` proactively — it's 2 lines and prevents a nasty production bug. This is a low-cost, high-value defensive measure.

2. **Renderer dispatch mechanism**
   - What we know: `save_dual()` needs to pick the right renderer for a given Pydantic model. Options: (a) dict mapping `type(data).__name__` to function, (b) `isinstance` chain, (c) accept renderer as parameter.
   - What's unclear: Which approach best serves downstream phases (6-10) that will call `save_dual()`.
   - Recommendation: Use a dict registry (`_RENDERERS`) keyed by class name. It's O(1) lookup, easy to extend, and avoids import-time isinstance checks. Fallback: raise `ValueError` for unregistered types.

## Sources

### Primary (HIGH confidence)
- Python 3.12 official docs: `importlib.resources` — verified `files()` API, `read_text()`, package anchor semantics
- Project codebase: `minilegion/core/schemas.py` — all 5 Pydantic models with exact field names and types
- Project codebase: `minilegion/core/file_io.py` — `write_atomic()` signature and behavior
- Project codebase: `minilegion/core/exceptions.py` — `ConfigError` class
- Project codebase: `minilegion/adapters/base.py` — `call_for_json(system_prompt, user_message)` signature
- Runtime verification: Python 3.12.10 on this system, `importlib.resources.files('minilegion.prompts')` resolves correctly
- Runtime verification: `re.sub(r'\{\{(\w+)\}\}', replacer, template)` handles placeholder substitution with error detection
- Runtime verification: `model_dump_json(indent=2)` produces clean indented JSON from Pydantic v2 models

### Secondary (MEDIUM confidence)
- Pydantic v2 docs: `model_dump_json()` API (verified via runtime test)
- setuptools docs: package-data inclusion for non-`.py` files

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib + existing project dependencies, verified at runtime
- Architecture: HIGH — patterns directly dictated by CONTEXT.md locked decisions, verified with working code
- Pitfalls: HIGH — identified through code analysis and runtime testing, all reproducible
- Prompt content: MEDIUM — behavioral anchoring wording is discretionary; effectiveness depends on LLM behavior at call time (Phases 6-10)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable — stdlib + Pydantic v2, no fast-moving dependencies)
