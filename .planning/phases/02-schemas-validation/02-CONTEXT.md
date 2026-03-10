# Phase 2: Schemas & Validation - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Pydantic models for all 6 machine-readable artifact types (research, design, plan, execution_log, review, state), JSON Schema generation from those models, a schema registry with validation function, and retry logic that handles invalid LLM output with error feedback and raw debug capture. This phase delivers the validation layer that sits between LLM calls (Phase 3) and the pipeline stages (Phases 6-10).

</domain>

<decisions>
## Implementation Decisions

### Schema Strictness & Field Optionality
- All fields required with sensible defaults where applicable (matches ProjectState pattern from Phase 1)
- Standard Pydantic coercion enabled (e.g., `'3'` becomes `3`) plus custom fixups for common LLM quirks
- Pre-parse fixups: strip markdown code fences (`\`\`\`json...\`\`\``), fix trailing commas, strip BOM/control characters — applied before Pydantic validation
- The existing `ProjectState` in `core/state.py` is reused as the canonical state schema (6th artifact type) — added to registry, no separate model
- Constrained string fields: use `Stage(str, Enum)` pattern for reusable values (like verdict enums), `Literal` types for one-off constraints (e.g., action='create'|'modify')

### JSON Schema Output & Location
- JSON Schema files stored in `minilegion/schemas/` (package-level, not project-level)
- Pre-generated and checked into source control — not generated at runtime
- Naming convention: `artifact.schema.json` (e.g., `research.schema.json`, `design.schema.json`)
- Schema files generated from Pydantic models via `model_json_schema()`

### Schema Registry & Validation API
- Central registry mapping artifact name (string) to Pydantic model class
- `get_schema('research')` returns the model class
- `get_json_schema('research')` returns the JSON Schema dict
- `validate(artifact_name, data)` convenience function — validates data against named schema in one call
- Registry + validate pattern gives downstream modules a single entry point

### Retry Feedback Format
- On validation failure, summarize Pydantic errors into 2-3 human-readable sentences (not raw Pydantic error dumps)
- On retry, resend the original prompt with the previous bad output + simplified errors appended in a "here's what you got wrong" section
- Retry count uses `config.max_retries` (currently defaults to 2) — single source of truth, no separate setting

### RAW_DEBUG.txt Handling
- Saved to `project-ai/debug/` subdirectory (separate from real artifacts)
- Timestamped filenames: `RESEARCH_RAW_DEBUG_20260310T143022.txt` — accumulates, never overwrites
- Content: raw LLM output + validation errors (no prompt — could contain sensitive context)
- Uses `write_atomic()` for consistency with all other file writes

### OpenCode's Discretion
- Exact field names and types within each Pydantic model (guided by REQUIREMENTS.md SCHM-01 field lists)
- Internal structure of the schema registry module
- Pre-parse fixup implementation details
- Error summary formatting logic
- Test structure and organization

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ProjectState` (core/state.py): Existing Pydantic model — becomes the state schema in the registry
- `MiniLegionConfig` (core/config.py): Pattern reference for Pydantic models with defaults and Field()
- `Stage(str, Enum)` (core/state.py): Pattern for constrained string enums — reuse for verdict, action enums
- `HistoryEntry` (core/state.py): Nested Pydantic model pattern — reuse for nested schema structures
- `write_atomic()` (core/file_io.py): Used for writing debug files
- `ValidationError` (core/exceptions.py): Already exists for schema validation failures

### Established Patterns
- `BaseModel` with `Field(default_factory=...)` for complex defaults
- `model_dump_json(indent=2)` for serialization
- `model_validate_json(raw)` for deserialization
- `str+Enum` for string enums that need JSON serialization
- Exception wrapping: `raise XError(...) from exc`

### Integration Points
- Schema registry will be imported by LLM adapter (Phase 3) for response validation
- Retry logic will be called by adapter layer after failed validation
- Pre-parse fixups run between raw LLM response and Pydantic validation
- `validate()` function used by every pipeline stage (Phases 6-10)
- Debug file writing integrates with `project-ai/debug/` directory

</code_context>

<specifics>
## Specific Ideas

- REQUIREMENTS.md specifies exact field lists for research (RSCH-06), design (DSGN-02), plan (PLAN-02), execution_log (BUILD-02), review (REVW-02) schemas
- Config already has `max_retries: int = 2` — retry logic should read from this
- The 6 artifact types map to: research, design, plan, execution_log, review, state
- JSON Schema files serve external tool consumption (per SCHM-02)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-schemas-validation*
*Context gathered: 2026-03-10*
