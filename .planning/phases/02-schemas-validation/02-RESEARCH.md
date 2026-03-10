# Phase 2: Schemas & Validation - Research

**Researched:** 2026-03-10
**Domain:** Pydantic v2 schema modeling, JSON Schema generation, LLM output validation & retry logic
**Confidence:** HIGH

## Summary

Phase 2 builds the validation layer that sits between LLM responses and the pipeline stages. It requires defining 6 Pydantic v2 models (research, design, plan, execution_log, review, and reusing the existing ProjectState as state), generating JSON Schema files from those models, building a central schema registry with validation helpers, implementing pre-parse fixups for common LLM output quirks, and adding retry logic with error feedback for failed validations.

The project already uses Pydantic v2.12.5 with established patterns: `BaseModel` + `Field()`, `Stage(str, Enum)`, `model_dump_json(indent=2)`, `model_validate_json()`, and the `write_atomic()` function. This phase extends those patterns to 5 new artifact models, adds a registry module, a pre-parse cleanup pipeline, and retry/debug-capture logic. No new dependencies are needed.

**Primary recommendation:** Build models following the existing `ProjectState`/`MiniLegionConfig` patterns with `BaseModel` + `Field()`, use `model_json_schema()` to pre-generate `.schema.json` files, implement the registry as a simple dict-based module with `validate()` / `get_schema()` / `get_json_schema()` functions, and keep pre-parse fixups as a standalone function pipeline applied before `model_validate_json()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All fields required with sensible defaults where applicable (matches ProjectState pattern from Phase 1)
- Standard Pydantic coercion enabled (e.g., `'3'` becomes `3`) plus custom fixups for common LLM quirks
- Pre-parse fixups: strip markdown code fences (`\`\`\`json...\`\`\``), fix trailing commas, strip BOM/control characters — applied before Pydantic validation
- The existing `ProjectState` in `core/state.py` is reused as the canonical state schema (6th artifact type) — added to registry, no separate model
- Constrained string fields: use `Stage(str, Enum)` pattern for reusable values (like verdict enums), `Literal` types for one-off constraints (e.g., action='create'|'modify')
- JSON Schema files stored in `minilegion/schemas/` (package-level, not project-level)
- Pre-generated and checked into source control — not generated at runtime
- Naming convention: `artifact.schema.json` (e.g., `research.schema.json`, `design.schema.json`)
- Schema files generated from Pydantic models via `model_json_schema()`
- Central registry mapping artifact name (string) to Pydantic model class
- `get_schema('research')` returns the model class
- `get_json_schema('research')` returns the JSON Schema dict
- `validate(artifact_name, data)` convenience function — validates data against named schema in one call
- On validation failure, summarize Pydantic errors into 2-3 human-readable sentences (not raw Pydantic error dumps)
- On retry, resend the original prompt with the previous bad output + simplified errors appended in a "here's what you got wrong" section
- Retry count uses `config.max_retries` (currently defaults to 2) — single source of truth, no separate setting
- RAW_DEBUG saved to `project-ai/debug/` subdirectory (separate from real artifacts)
- Timestamped filenames: `RESEARCH_RAW_DEBUG_20260310T143022.txt` — accumulates, never overwrites
- RAW_DEBUG content: raw LLM output + validation errors (no prompt — could contain sensitive context)
- RAW_DEBUG uses `write_atomic()` for consistency with all other file writes

### OpenCode's Discretion
- Exact field names and types within each Pydantic model (guided by REQUIREMENTS.md SCHM-01 field lists)
- Internal structure of the schema registry module
- Pre-parse fixup implementation details
- Error summary formatting logic
- Test structure and organization

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCHM-01 | Pydantic models define all 6 machine-readable artifact schemas (research, design, plan, execution_log, review, state) | Pydantic v2 BaseModel + Field() patterns verified; field lists from RSCH-06, DSGN-02, PLAN-02, BUILD-02, REVW-02; ProjectState already exists for state |
| SCHM-02 | JSON Schema files generated from Pydantic models for external tool consumption | `model_json_schema()` verified in Pydantic v2.12; generates Draft 2020-12 compliant schemas; `json.dumps()` for serialization |
| SCHM-03 | LLM output is parsed and validated against schema immediately after each call | Registry `validate()` function + `model_validate_json()` for parsing; pre-parse fixups handle LLM quirks before validation |
| SCHM-04 | Invalid JSON triggers retry with error feedback injected into next LLM call (max 2 retries) | `pydantic.ValidationError.errors()` provides structured error list with `loc`, `msg`, `type`; summarize into human-readable feedback; use `config.max_retries` |
| SCHM-05 | After max retries, raw LLM output is saved to `*_RAW_DEBUG.txt` for diagnosis | `write_atomic()` already exists; timestamped filenames in `project-ai/debug/`; content = raw output + error summary |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Schema definition, validation, JSON Schema generation | Already installed and used in Phase 1; BaseModel is the foundation of the project |
| pydantic-core | (bundled) | Underlying validation engine; provides `ValidationError` | Bundled with pydantic; `pydantic_core.ValidationError` is the actual exception class |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | `json.dumps()` for writing schema files, `json.loads()` for pre-parse validation | Always — schema serialization and raw JSON manipulation |
| re (stdlib) | - | Regex for pre-parse fixups (markdown fence stripping, trailing comma removal) | Pre-parse fixup pipeline |
| datetime (stdlib) | - | Timestamp generation for RAW_DEBUG filenames | Debug file naming |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual pre-parse fixups | `json-repair` library | Adds dependency; our fixups are 3 specific patterns (fences, trailing commas, BOM) — simpler to implement directly |
| Dict-based registry | Class-based Registry with metaclass | Over-engineered for 6 static entries; dict is clearer and matches project's pragmatic style |

**Installation:**
```bash
# No new dependencies needed — pydantic>=2.12.0 already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── core/
│   ├── schemas.py         # 5 new Pydantic models (research, design, plan, execution_log, review)
│   ├── registry.py        # Schema registry: SCHEMA_REGISTRY dict + get_schema/get_json_schema/validate
│   ├── fixups.py          # Pre-parse fixup pipeline: strip_markdown_fences, fix_trailing_commas, strip_bom
│   ├── retry.py           # validate_with_retry() + summarize_errors() + save_raw_debug()
│   ├── state.py           # Existing — ProjectState reused as 6th schema
│   ├── config.py          # Existing — max_retries read from here
│   ├── exceptions.py      # Existing — ValidationError already defined
│   └── file_io.py         # Existing — write_atomic() used for debug files
├── schemas/               # Pre-generated JSON Schema files (checked in)
│   ├── research.schema.json
│   ├── design.schema.json
│   ├── plan.schema.json
│   ├── execution_log.schema.json
│   ├── review.schema.json
│   └── state.schema.json
└── ...
```

### Pattern 1: Pydantic Model Definition (Following Existing Conventions)
**What:** Define each artifact schema as a `BaseModel` subclass using `Field()` with defaults where sensible.
**When to use:** Every new model in this phase.
**Example:**
```python
# Source: Existing pattern from minilegion/core/state.py + REQUIREMENTS.md field lists
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """Reusable verdict enum — Stage(str, Enum) pattern."""
    PASS = "pass"
    REVISE = "revise"


class ArchitectureDecision(BaseModel):
    """Nested model — follows HistoryEntry pattern."""
    decision: str
    rationale: str
    alternatives_rejected: list[str] = Field(default_factory=list)


class DesignSchema(BaseModel):
    """DESIGN.json schema — all fields required, defaults where sensible."""
    design_approach: str
    architecture_decisions: list[ArchitectureDecision] = Field(default_factory=list)
    components: list[dict] = Field(default_factory=list)
    data_models: list[str] = Field(default_factory=list)
    api_contracts: list[str] = Field(default_factory=list)
    integration_points: list[str] = Field(default_factory=list)
    design_patterns_used: list[str] = Field(default_factory=list)
    conventions_to_follow: list[str] = Field(default_factory=list)
    technical_risks: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    test_strategy: str = ""
    estimated_complexity: str = "medium"
```

### Pattern 2: Schema Registry (Dict-Based)
**What:** Central registry mapping artifact name -> Pydantic model class, with convenience functions.
**When to use:** Single entry point for all validation throughout the codebase.
**Example:**
```python
# Source: CONTEXT.md decisions — registry + validate pattern
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

from minilegion.core.schemas import (
    ResearchSchema, DesignSchema, PlanSchema,
    ExecutionLogSchema, ReviewSchema,
)
from minilegion.core.state import ProjectState

SCHEMA_REGISTRY: dict[str, Type[BaseModel]] = {
    "research": ResearchSchema,
    "design": DesignSchema,
    "plan": PlanSchema,
    "execution_log": ExecutionLogSchema,
    "review": ReviewSchema,
    "state": ProjectState,
}


def get_schema(artifact_name: str) -> Type[BaseModel]:
    """Return the Pydantic model class for the named artifact."""
    if artifact_name not in SCHEMA_REGISTRY:
        raise KeyError(f"Unknown artifact: {artifact_name}. Valid: {list(SCHEMA_REGISTRY)}")
    return SCHEMA_REGISTRY[artifact_name]


def get_json_schema(artifact_name: str) -> dict:
    """Return the JSON Schema dict for the named artifact."""
    return get_schema(artifact_name).model_json_schema()


def validate(artifact_name: str, data: str | dict | Any) -> BaseModel:
    """Validate data against the named schema. Returns validated model instance."""
    model_cls = get_schema(artifact_name)
    if isinstance(data, str):
        return model_cls.model_validate_json(data)
    return model_cls.model_validate(data)
```

### Pattern 3: Pre-Parse Fixup Pipeline
**What:** Chain of text transformations applied to raw LLM output before JSON parsing.
**When to use:** Between receiving raw LLM response and calling `model_validate_json()`.
**Example:**
```python
# Source: CONTEXT.md decisions — strip markdown fences, fix trailing commas, strip BOM
import re


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that LLMs often add."""
    text = text.strip()
    # Match opening fence with optional language tag
    pattern = r'^```(?:json)?\s*\n?(.*?)\n?\s*```$'
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (common LLM mistake)."""
    # Handles: {"a": 1,} or [1, 2,]
    return re.sub(r',\s*([}\]])', r'\1', text)


def strip_bom_and_control(text: str) -> str:
    """Remove BOM and non-printable control characters (except whitespace)."""
    text = text.lstrip('\ufeff')  # BOM
    # Remove control chars except \n, \r, \t
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)


def apply_fixups(raw_text: str) -> str:
    """Apply all pre-parse fixups in order."""
    text = strip_bom_and_control(raw_text)
    text = strip_markdown_fences(text)
    text = fix_trailing_commas(text)
    return text
```

### Pattern 4: Error Summary for LLM Retry
**What:** Convert Pydantic `ValidationError.errors()` list into a concise human-readable summary.
**When to use:** When constructing retry prompts after validation failure.
**Example:**
```python
# Source: Pydantic v2 official docs — ValidationError.errors() returns list of ErrorDetails dicts
# Each dict has: type, loc (tuple), msg (str), input, url
from pydantic import ValidationError


def summarize_errors(exc: ValidationError) -> str:
    """Summarize validation errors into 2-3 human-readable sentences."""
    errors = exc.errors()
    error_count = len(errors)

    # Group by field location for concise summary
    field_issues: list[str] = []
    for err in errors[:5]:  # Cap at 5 to keep summary concise
        loc = ".".join(str(part) for part in err["loc"]) if err["loc"] else "root"
        field_issues.append(f"'{loc}': {err['msg']}")

    summary = f"Validation failed with {error_count} error(s). "
    summary += "Issues: " + "; ".join(field_issues)
    if error_count > 5:
        summary += f" (and {error_count - 5} more)"
    summary += "."
    return summary
```

### Pattern 5: JSON Schema Generation Script
**What:** Script/function to regenerate JSON Schema files from Pydantic models.
**When to use:** During development when models change; output is checked into source control.
**Example:**
```python
# Source: Pydantic v2 docs — model_json_schema() returns JSON-serializable dict
import json
from pathlib import Path

from minilegion.core.registry import SCHEMA_REGISTRY

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def generate_schemas() -> None:
    """Generate JSON Schema files from all registered Pydantic models."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for name, model_cls in SCHEMA_REGISTRY.items():
        schema = model_cls.model_json_schema()
        path = SCHEMA_DIR / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate_schemas()
```

### Anti-Patterns to Avoid
- **Catching `pydantic.ValidationError` but importing from wrong place:** In Pydantic v2, `ValidationError` is re-exported from `pydantic` but lives in `pydantic_core`. The project's own `minilegion.core.exceptions.ValidationError` is a different class. Always be explicit about which `ValidationError` you're catching — use `pydantic.ValidationError` for Pydantic errors, wrap and re-raise as `minilegion.core.exceptions.ValidationError` for the project's exception hierarchy.
- **Generating JSON Schema at runtime:** The user decided schemas are pre-generated and checked in. Do NOT call `model_json_schema()` at runtime for validation — only use the pre-generated files or the registry's `get_json_schema()` for informational purposes.
- **Overly complex pre-parse fixups:** Keep fixups to the 3 agreed-upon patterns (fences, trailing commas, BOM). Don't try to fix structural JSON errors (missing quotes, wrong nesting) — those should fail validation and trigger retry.
- **Dumping raw Pydantic error output to LLM:** The user explicitly decided on simplified 2-3 sentence summaries. Raw `ValidationError` output is verbose and confusing to LLMs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema generation | Custom schema builder | `BaseModel.model_json_schema()` | Pydantic generates Draft 2020-12 compliant schemas with `$defs`, `$ref`, proper type mapping |
| JSON parsing with error details | Manual JSON parser | `model_validate_json()` + `ValidationError.errors()` | Pydantic gives structured error details (loc, msg, type) for free |
| Enum serialization | Custom `__str__` / serializers | `Stage(str, Enum)` pattern | Already proven in Phase 1; `str` mixin gives JSON-friendly values automatically |
| Atomic file writes | Direct `open().write()` | `write_atomic()` from `core/file_io.py` | Already handles temp files, fsync, os.replace, cleanup — don't reinvent |

**Key insight:** Pydantic v2 handles schema generation, validation, error reporting, and JSON serialization. The only custom code needed is the pre-parse fixup pipeline (3 regex functions), error summarization (formatting), and retry orchestration (control flow).

## Common Pitfalls

### Pitfall 1: Pydantic ValidationError vs Project ValidationError Name Collision
**What goes wrong:** Importing `ValidationError` without qualification catches the wrong exception or raises the wrong type.
**Why it happens:** The project defines `minilegion.core.exceptions.ValidationError` AND Pydantic has `pydantic.ValidationError`. Both are used in this phase.
**How to avoid:** Always import with explicit names: `from pydantic import ValidationError as PydanticValidationError` OR `import pydantic` and use `pydantic.ValidationError`. Wrap Pydantic errors into project errors at the boundary: `raise exceptions.ValidationError(...) from pydantic_exc`.
**Warning signs:** Tests that catch `ValidationError` but the wrong one silently passes.

### Pitfall 2: model_json_schema() $defs for Nested Models
**What goes wrong:** JSON Schema for models with nested sub-models (e.g., `ArchitectureDecision` inside `DesignSchema`) generates `$ref` references to a `$defs` section. If you naively compare schemas or try to use them standalone, the `$defs` are missing.
**Why it happens:** Pydantic v2 puts nested model definitions in `$defs` at the schema root and uses `$ref` pointers.
**How to avoid:** Always serialize the complete schema dict returned by `model_json_schema()`. Don't strip `$defs`. This is correct JSON Schema behavior.
**Warning signs:** Schemas that reference `#/$defs/SomeModel` but the definition doesn't exist in the file.

### Pitfall 3: Pre-Parse Fixup Order Matters
**What goes wrong:** If you strip markdown fences after fixing trailing commas, the fence markers may interfere with the regex.
**Why it happens:** Fixups interact — BOM affects fence detection, fences contain the JSON that has trailing commas.
**How to avoid:** Apply fixups in this order: (1) strip BOM/control chars, (2) strip markdown fences, (3) fix trailing commas. Always test with combined edge cases.
**Warning signs:** Fixups work individually but fail when combined.

### Pitfall 4: Retry Logic Must Distinguish JSON Parse Errors from Schema Validation Errors
**What goes wrong:** Raw text that isn't JSON at all (e.g., LLM returns prose) throws `json.JSONDecodeError` or Pydantic's `json_invalid` error, not a schema `ValidationError`.
**Why it happens:** `model_validate_json()` raises `pydantic.ValidationError` for both malformed JSON and valid-JSON-wrong-schema. The error type inside will be `json_invalid` for malformed JSON.
**How to avoid:** Catch `pydantic.ValidationError` uniformly — both cases are validation failures from the retry logic's perspective. The error summary function handles both cases via `error.errors()`.
**Warning signs:** Code that tries `json.loads()` separately before `model_validate_json()` — this is redundant since Pydantic handles JSON parsing internally.

### Pitfall 5: Timestamp Format in RAW_DEBUG Filenames
**What goes wrong:** Using `datetime.now().isoformat()` produces colons in filenames (`2026-03-10T14:30:22`) which are invalid on Windows.
**Why it happens:** ISO 8601 format includes `:` characters.
**How to avoid:** Use `datetime.now().strftime("%Y%m%dT%H%M%S")` to produce `20260310T143022` — no special characters. This matches the CONTEXT.md spec.
**Warning signs:** Tests pass on Linux but fail on Windows.

### Pitfall 6: Default Factory vs Default Value for Mutable Defaults
**What goes wrong:** Using `list[str] = []` instead of `list[str] = Field(default_factory=list)` causes shared mutable default.
**Why it happens:** Pydantic v2 actually handles this correctly (it copies), but `Field(default_factory=list)` is the established pattern in this project.
**How to avoid:** Follow the existing `ProjectState` pattern: always use `Field(default_factory=list)` for list/dict defaults.
**Warning signs:** Inconsistent patterns across models.

## Code Examples

Verified patterns from official sources and existing codebase:

### JSON Schema Generation
```python
# Source: https://docs.pydantic.dev/latest/concepts/json_schema/
import json
from pydantic import BaseModel, Field

class ResearchSchema(BaseModel):
    project_overview: str
    tech_stack: list[str] = Field(default_factory=list)

schema = ResearchSchema.model_json_schema()
# Returns: {'properties': {...}, 'required': [...], 'title': 'ResearchSchema', 'type': 'object'}

# Write to file
with open("research.schema.json", "w") as f:
    json.dump(schema, f, indent=2)
```

### Validation with Error Extraction
```python
# Source: https://docs.pydantic.dev/latest/errors/errors/
from pydantic import BaseModel, ValidationError

class MyModel(BaseModel):
    name: str
    count: int

try:
    MyModel.model_validate_json('{"name": 123}')
except ValidationError as e:
    errors = e.errors()
    # errors = [
    #   {'type': 'string_type', 'loc': ('name',), 'msg': 'Input should be a valid string', ...},
    #   {'type': 'missing', 'loc': ('count',), 'msg': 'Field required', ...},
    # ]
    error_count = e.error_count()  # 2
    human_str = str(e)  # Multi-line human-readable
```

### model_validate_json for Raw String Input
```python
# Source: Existing pattern in minilegion/core/state.py line 183-184
from pydantic import BaseModel

class MySchema(BaseModel):
    field: str

raw = '{"field": "value"}'
instance = MySchema.model_validate_json(raw)  # Parse + validate in one call
```

### Enum with str Mixin (Existing Pattern)
```python
# Source: minilegion/core/state.py lines 21-32
from enum import Enum

class Verdict(str, Enum):
    PASS = "pass"
    REVISE = "revise"

# Usage in model:
from typing import Literal
class ReviewSchema(BaseModel):
    verdict: Verdict  # Reusable enum for pass/revise
    action: Literal["create", "modify"]  # One-off constraint
```

### write_atomic for Debug Files
```python
# Source: minilegion/core/file_io.py
from datetime import datetime
from pathlib import Path
from minilegion.core.file_io import write_atomic

def save_raw_debug(
    artifact_name: str,
    raw_output: str,
    error_summary: str,
    project_dir: Path,
) -> Path:
    """Save raw LLM output + errors to debug file."""
    debug_dir = project_dir / "project-ai" / "debug"
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"{artifact_name.upper()}_RAW_DEBUG_{timestamp}.txt"
    path = debug_dir / filename

    content = f"=== RAW LLM OUTPUT ===\n{raw_output}\n\n=== VALIDATION ERRORS ===\n{error_summary}\n"
    write_atomic(path, content)
    return path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `schema()` | Pydantic v2 `model_json_schema()` | Pydantic v2 (2023) | Method name changed; output is Draft 2020-12 not Draft 7 |
| Pydantic v1 `parse_raw_as()` | Pydantic v2 `model_validate_json()` | Pydantic v2 (2023) | Unified API; handles JSON parsing + validation |
| Pydantic v1 `dict()` / `json()` | Pydantic v2 `model_dump()` / `model_dump_json()` | Pydantic v2 (2023) | Already used in Phase 1 |
| Pydantic v1 validator decorator | Pydantic v2 `@field_validator` / `@model_validator` | Pydantic v2 (2023) | Different decorator names and modes (before/after/wrap) |

**Deprecated/outdated:**
- `BaseModel.schema()` — replaced by `model_json_schema()` in v2
- `BaseModel.parse_raw()` — replaced by `model_validate_json()` in v2
- `validator` decorator — replaced by `field_validator` in v2

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHM-01 | 6 Pydantic models exist and validate/reject data | unit | `python -m pytest tests/test_schemas.py -x` | Wave 0 |
| SCHM-01 | Each model rejects invalid data with clear errors | unit | `python -m pytest tests/test_schemas.py -x -k "test_invalid"` | Wave 0 |
| SCHM-02 | JSON Schema files are valid and match models | unit | `python -m pytest tests/test_json_schemas.py -x` | Wave 0 |
| SCHM-03 | Registry validate() parses and validates correctly | unit | `python -m pytest tests/test_registry.py -x` | Wave 0 |
| SCHM-03 | Pre-parse fixups clean LLM output | unit | `python -m pytest tests/test_fixups.py -x` | Wave 0 |
| SCHM-04 | Retry logic retries with error feedback | unit | `python -m pytest tests/test_retry.py -x -k "test_retry"` | Wave 0 |
| SCHM-05 | After max retries, RAW_DEBUG.txt saved | unit | `python -m pytest tests/test_retry.py -x -k "test_raw_debug"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_schemas.py` — covers SCHM-01: model creation, validation, rejection with clear errors for all 6 types
- [ ] `tests/test_json_schemas.py` — covers SCHM-02: JSON Schema file existence, validity, and match to models
- [ ] `tests/test_registry.py` — covers SCHM-03: get_schema, get_json_schema, validate functions
- [ ] `tests/test_fixups.py` — covers SCHM-03: pre-parse fixup functions (fences, trailing commas, BOM)
- [ ] `tests/test_retry.py` — covers SCHM-04, SCHM-05: retry with error feedback, RAW_DEBUG file saving

## Open Questions

1. **Exact field names for each artifact model**
   - What we know: REQUIREMENTS.md specifies field lists at RSCH-06, DSGN-02, PLAN-02, BUILD-02, REVW-02
   - What's unclear: Some fields may need sub-models (e.g., `components` in design has nested structure with `files`)
   - Recommendation: Follow REQUIREMENTS.md field lists exactly; create nested sub-models where the field description implies structure (e.g., `architecture_decisions` with `alternatives_rejected`)

2. **Whether `validate()` should accept both str and dict**
   - What we know: `model_validate_json(str)` for JSON strings, `model_validate(dict)` for dicts
   - What's unclear: Whether downstream callers will always provide raw strings or sometimes dicts
   - Recommendation: Accept both — check `isinstance(data, str)` and route accordingly. This is future-proof and costs nothing.

3. **How retry logic interfaces with LLM adapter (Phase 3)**
   - What we know: Retry needs original prompt, bad output, and error summary. Phase 3 builds the adapter.
   - What's unclear: Exact function signature boundary between validation retry and LLM call
   - Recommendation: Build `validate_with_retry()` as a standalone function that accepts a callable (the LLM call function), prompt string, artifact name, config, and project dir. This keeps the boundary clean — Phase 3 just needs to pass its call function.

## Sources

### Primary (HIGH confidence)
- Pydantic v2.12.5 — installed and verified in project (`pip show pydantic`)
- https://docs.pydantic.dev/latest/concepts/json_schema/ — JSON Schema generation API, Draft 2020-12 compliance, `model_json_schema()` usage
- https://docs.pydantic.dev/latest/concepts/validators/ — Field validators (before/after/wrap/plain), model validators, `ValidationInfo`
- https://docs.pydantic.dev/latest/errors/errors/ — `ValidationError.errors()` returns list of `ErrorDetails` dicts with `type`, `loc`, `msg`, `input`, `url`
- Existing codebase: `minilegion/core/state.py`, `config.py`, `exceptions.py`, `file_io.py` — established patterns

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md RSCH-06, DSGN-02, PLAN-02, BUILD-02, REVW-02 — field lists for each artifact type (definitive but may need interpretation for nested structures)

### Tertiary (LOW confidence)
- None — all findings verified against official docs or existing code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Pydantic v2 already installed and used; no new dependencies
- Architecture: HIGH — patterns directly extend existing codebase conventions; registry is straightforward
- Pitfalls: HIGH — verified against Pydantic v2 official docs and Windows file naming constraints
- Field definitions: MEDIUM — REQUIREMENTS.md field lists are clear but some nested structure interpretation needed

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable — Pydantic v2 API is mature)
