# Technology Stack

**Project:** MiniLegion
**Researched:** 2026-03-09
**Overall Confidence:** HIGH

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | >=3.10 | Runtime | All key dependencies require 3.10+. Type unions (`X | Y`), match statements, and `tomllib` (3.11) are useful. Pin 3.10 as floor for broadest compat. | HIGH |

### CLI Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Typer | 0.24.1 | CLI entrypoint, 8 commands | Type-hint-driven commands eliminate boilerplate. Auto-generates `--help`. Built on Click (proven routing) but dramatically less code. Rich/shellingham bundled for future TUI (Sprint 2+). "FastAPI of CLIs" matches the project's Python-native philosophy. | HIGH |

**Why not Click directly?** Click works but requires manual decorators and option declarations for every parameter. Typer infers everything from function signatures — less code, fewer bugs, same underlying engine. The 8-command surface (`init`, `brief`, `research`, `design`, `plan`, `execute`, `review`, `status`) maps cleanly to Typer sub-commands.

**Why not argparse?** argparse is stdlib but produces verbose, hard-to-maintain code at 8+ commands. No auto-completion, no rich help formatting, manual subparser wiring. The marginal benefit of "no dependency" doesn't justify the DX cost.

### LLM Client

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| openai | 2.26.0 | OpenAI API adapter (MVP) | Native structured output via `client.chat.completions.parse(response_format=PydanticModel)` eliminates the need for separate parsing/validation layers. Built-in retry (default 2, configurable), async support via `AsyncOpenAI`, timeout configuration. References models up to `gpt-5.2`. | HIGH |

**Key capability — Native Structured Outputs:** The openai SDK >=1.x supports `response_format` with Pydantic models directly. The SDK handles JSON schema generation from Pydantic, sends it to the API, and returns a parsed Pydantic object. This is the primary reason `instructor` is NOT recommended (see below).

**Adapter pattern:** Define `adapters/base.py` as an abstract base class. The `openai` adapter implements it. Future adapters (Anthropic, local models) implement the same interface. The base class should define: `call(prompt, schema, config) -> ParsedResponse`.

### Schema & Validation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pydantic | 2.12.5 | Schema definition, LLM output validation, config parsing | Single library for ALL validation: LLM response schemas, `minilegion.config.json` parsing, inter-phase coherence checks. V2 is Rust-backed (pydantic-core) — fast validation. Integrates directly with openai SDK's `response_format`. | HIGH |
| jsonschema | 4.26.0 | JSON Schema Draft 2020-12 validation (optional, for raw schema files) | Only needed if the project stores standalone `.json` schema files and validates against them outside Pydantic. Pydantic can export JSON Schema via `model_json_schema()`. Consider deferring this dependency until needed. | MEDIUM |

**Recommendation:** Use Pydantic as the single source of truth for all 6 artifact schemas (research, design, plan, execution_log, review, state). Export JSON Schema files from Pydantic models for documentation/interop. Validate LLM responses by passing Pydantic models directly to the openai SDK. This eliminates an entire validation layer.

### File State Management

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `pathlib` (stdlib) | — | File path operations | Pythonic path handling, cross-platform. No dependency. | HIGH |
| `json` (stdlib) | — | JSON read/write for all `.json` artifacts | All state is JSON. Stdlib is sufficient — no need for `orjson` or `ujson` at this scale. | HIGH |
| `shutil` (stdlib) | — | Directory operations (init, archive) | Copy/move for archival operations. | HIGH |

**No external dependencies needed.** File-centric memory is just JSON files in `project-ai/`. Pydantic handles serialization (`model_dump_json()`) and deserialization (`model_validate_json()`). The filesystem is the database.

### Patch Application

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `difflib` (stdlib) | — | Generating unified diffs for review/display | Stdlib, no dependency. Good for showing what changed. | HIGH |

**Why not `unidiff`?** Last updated March 2023, Python 3.11 classifier ceiling, effectively abandoned. Do not depend on it.

**Patch strategy:** The Builder role produces structured JSON patches (per PROJECT.md: `EXECUTION_LOG.json`), not unified diffs. The patch format should be a Pydantic model describing file operations (create, modify, delete) with content. Apply patches by writing files directly — no diff/patch tooling needed. `difflib` is only for generating human-readable diffs in review output.

### Retry & Resilience

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Built-in retry (openai SDK) | — | Network-level retries | openai SDK has `max_retries` (default 2) for transient HTTP errors. Configure, don't replace. | HIGH |
| Custom retry loop | — | Application-level JSON validation retry | PROJECT.md specifies "max 2 retries on JSON parse failure." This is application logic (re-prompt LLM with error), not network retry. A simple for-loop with error feedback is clearer than tenacity for this use case. | HIGH |

**Why not `tenacity`?** Tenacity (v9.1.4) is a solid library, but the retry requirements here are simple and domain-specific:
1. Network retries -> already handled by openai SDK
2. JSON parse retries -> max 2, with error message fed back to LLM as context
3. Revise loop -> max 2, with human escalation

These are 3-5 line loops, not complex retry policies. Adding tenacity creates a dependency for something that's clearer as explicit code. If retry logic grows complex in Sprint 2+, reconsider.

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | 9.0.2 | Test runner | Industry standard. Fixture system, parametrize, plugins. No contest. | HIGH |
| pytest-mock | latest | Mocking LLM calls | Clean `mocker.patch()` API for mocking openai client responses. | HIGH |

**Testing strategy for LLM calls:** Mock at the adapter boundary. The abstract base class makes this trivial — inject a `FakeAdapter` that returns canned Pydantic model instances. Never call real LLM APIs in tests.

**Note:** PROJECT.md lists "Framework unit tests — not in Sprint 1" under Out of Scope. However, having pytest configured from day 1 costs nothing and the adapter boundary pattern makes testing easy when Sprint 2 adds it.

### Dev Dependencies

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | latest | Linting + formatting | Single tool replaces flake8 + black + isort. Fast (Rust-based). Opinionated defaults reduce config. | HIGH |
| mypy | latest | Type checking | Pydantic V2 has excellent mypy plugin. Catches schema errors at dev time. | MEDIUM |

## What NOT to Use

| Library | Why Not |
|---------|---------|
| **instructor** (v1.14.5) | The openai SDK now natively supports structured outputs with Pydantic models via `response_format`. Instructor was valuable when this didn't exist. Now it's an unnecessary abstraction layer that obscures the direct SDK integration. For a single-provider MVP, use the SDK directly. |
| **langchain** | Massive dependency tree, over-abstracted for this use case. MiniLegion's 4-layer architecture is simpler and more debuggable than LangChain's chain/agent abstractions. |
| **unidiff** (v0.7.5) | Last updated March 2023. Python 3.11 ceiling. Effectively abandoned. Patches are structured JSON, not unified diffs. |
| **tenacity** (v9.1.4) | Retry requirements are simple (max 2, with domain-specific error feedback). A for-loop is clearer than a decorator for this use case. Reconsider if complexity grows. |
| **rich** (standalone) | Already bundled with Typer. Don't add as a separate dependency. Use Typer's built-in rich integration when Sprint 2+ adds TUI. |
| **pyyaml** | Project uses `minilegion.config.json`, not YAML. No need for YAML parsing. |
| **SQLite / tinydb** | File-centric memory is the architecture decision. JSON files in `project-ai/` are the database. Adding a DB violates the portability constraint. |
| **click** (standalone) | Typer wraps Click. Don't import Click directly — use Typer's API. Click is an implementation detail. |

## Dependency Summary

### Production Dependencies

```
openai>=2.26.0
pydantic>=2.12.0
typer>=0.24.0
```

**Total: 3 production dependencies.** This is intentionally minimal. The project's value is in the protocol/workflow logic, not in library integrations.

### Dev Dependencies

```
pytest>=9.0.0
pytest-mock>=3.14.0
ruff>=0.9.0
mypy>=1.14.0
```

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Production
pip install openai pydantic typer

# Dev
pip install pytest pytest-mock ruff mypy

# Or with pyproject.toml (recommended)
pip install -e ".[dev]"
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| CLI | Typer | Click | More boilerplate for same result; Typer wraps Click anyway |
| CLI | Typer | argparse | Too verbose at 8 commands; no auto-completion; manual subparsers |
| LLM Client | openai SDK | litellm | Adds abstraction for multi-provider, but MVP is OpenAI-only; adapter pattern handles future providers |
| Validation | Pydantic | dataclasses + jsonschema | Two libraries doing what one does better; no openai SDK integration |
| Structured Output | openai SDK native | instructor | SDK now has native `response_format` with Pydantic; instructor is redundant for OpenAI |
| Retry | Custom loop | tenacity | Requirements too simple to justify dependency; domain-specific error feedback doesn't fit decorator pattern |
| Patch | stdlib (json + pathlib) | unidiff | Abandoned library; patches are structured JSON, not unified diffs |

## Open Questions

1. **`jsonschema` as optional dependency:** If standalone JSON Schema files are needed for external tooling or documentation, add `jsonschema`. If Pydantic is the only validation layer, skip it. Decision can be deferred to Sprint 1 implementation.

2. **`httpx` vs `requests`:** The openai SDK uses `httpx` internally. If MiniLegion needs HTTP calls beyond LLM (e.g., future web search in Sprint 2+), `httpx` is already in the dependency tree — prefer it over adding `requests`.

3. **Package manager:** `pip` with `pyproject.toml` is sufficient for Sprint 1. Consider `uv` (from Astral, makers of ruff) for faster installs if DX matters. Not a blocking decision.

## Sources

- PyPI: openai 2.26.0 release (March 2026)
- PyPI: typer 0.24.1 release (February 2026)
- PyPI: pydantic 2.12.5 release (November 2025)
- PyPI: jsonschema 4.26.0 release (January 2026)
- PyPI: instructor 1.14.5 release (January 2026)
- PyPI: tenacity 9.1.4 release (February 2026)
- PyPI: pytest 9.0.2 release (December 2025)
- PyPI: unidiff 0.7.5 release (March 2023)
- OpenAI Structured Outputs documentation (platform.openai.com)
- PROJECT.md — project constraints, requirements, and key decisions
