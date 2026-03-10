# Phase 5: Prompts & Dual Output - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Role prompt templates for the 5 LLM pipeline roles (researcher, designer, planner, builder, reviewer) and programmatic Markdown generation from parsed JSON artifacts. This phase delivers the prompt infrastructure and dual-output layer that pipeline stages (Phases 6-10) will use. It does NOT implement the pipeline stages themselves — it builds the prompt templates and the JSON-to-Markdown rendering functions.

</domain>

<decisions>
## Implementation Decisions

### Prompt File Format & Storage
- Prompts stored as plain Markdown files in `minilegion/prompts/` directory (package-level, importable)
- One file per role: `researcher.md`, `designer.md`, `planner.md`, `builder.md`, `reviewer.md`
- Each file has two sections delimited by markers: `<!-- SYSTEM -->` and `<!-- USER_TEMPLATE -->`
- SYSTEM section contains the system prompt (role definition, constraints, output format)
- USER_TEMPLATE section contains the user message template with `{{placeholder}}` variables
- Files are read at runtime via a `load_prompt(role: str) -> tuple[str, str]` function that returns `(system_prompt, user_template)`

### Prompt Loading & Variable Injection
- `minilegion/prompts/loader.py` module with:
  - `load_prompt(role: str) -> tuple[str, str]` — reads the markdown file, splits on markers, returns (system, user_template)
  - `render_prompt(template: str, **variables) -> str` — replaces `{{key}}` with values from `variables` dict
  - Raises `ConfigError` if prompt file not found or missing sections
  - Raises `ConfigError` if a `{{placeholder}}` has no corresponding variable (unresolved placeholders detected)
- Uses `importlib.resources` (Python 3.9+) to load prompt files from the package, not filesystem paths — works in installed packages and editable installs

### JSON-Only Output Enforcement
- All 5 prompts include anchoring instructions at the START of the system prompt: "You MUST respond with valid JSON only. No markdown, no explanations, no code fences."
- All 5 prompts include anchoring at the END of the system prompt: "CRITICAL: Your entire response must be a single valid JSON object. Nothing else."
- The user template does NOT repeat JSON instructions — system prompt handles enforcement

### Placeholder Variables per Role
- Researcher: `{{brief_content}}`, `{{codebase_context}}`, `{{project_name}}`
- Designer: `{{brief_content}}`, `{{research_json}}`, `{{focus_files_content}}`, `{{project_name}}`
- Planner: `{{brief_content}}`, `{{research_json}}`, `{{design_json}}`, `{{project_name}}`
- Builder: `{{plan_json}}`, `{{source_files}}`, `{{project_name}}`
- Reviewer: `{{diff_text}}`, `{{plan_json}}`, `{{design_json}}`, `{{conventions}}`, `{{project_name}}`

### Dual Output (JSON + Markdown)
- Markdown renderer module in `minilegion/core/renderer.py`
- One render function per artifact type: `render_research_md(data: ResearchSchema) -> str`, etc.
- Accepts parsed Pydantic model, returns Markdown string
- Convenience function: `save_dual(data: BaseModel, json_path: Path, md_path: Path) -> None` — saves both `.json` (via `model_dump_json()`) and `.md` (via renderer) using `write_atomic()`
- Markdown is structured with headers, bullet lists, and tables — human-readable output, not raw JSON dump
- Each render function produces consistent sections matching the schema fields

### Role Prompt Constraints (behavioral anchoring)
- Researcher: "Explore, don't design" — output must not contain solution proposals
- Designer: "Design, don't plan" — output must not contain task decomposition
- Planner: "Decompose, don't design" — design decisions treated as settled
- Builder: "Build, don't redesign" — follows plan exactly, flags issues in `out_of_scope_needed`
- Reviewer: "Identify, don't correct" — flags issues without proposing fixes

### OpenCode's Discretion
- Exact wording of system prompts and user templates (as long as they follow the behavioral constraints above)
- Internal structure of each prompt file (section ordering within SYSTEM block)
- Markdown rendering formatting details (table widths, heading levels, bullet styles)
- Whether `render_review_md()` uses a table or bullet list for findings
- Helper functions for common rendering patterns (list-to-bullets, dict-to-table)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `minilegion/prompts/__init__.py` — empty placeholder, ready for population
- `minilegion/core/schemas.py` — all 5 Pydantic models (ResearchSchema, DesignSchema, PlanSchema, ExecutionLogSchema, ReviewSchema) that renderer will consume
- `minilegion/core/file_io.py` — `write_atomic()` for saving both JSON and Markdown files
- `minilegion/core/exceptions.py` — `ConfigError` for prompt loading failures
- `minilegion/adapters/base.py` — `LLMAdapter.call_for_json()` is what pipeline stages will call with rendered prompts

### Established Patterns
- `Stage(str, Enum)` and `Verdict(str, Enum)` — string enums for JSON serialization
- `write_atomic()` for all file writes — renderer output must use this
- Pydantic `BaseModel` for all data models — renderer functions accept these directly
- `importlib.resources` is the standard way to load package data files in modern Python

### Integration Points
- Pipeline stages (Phases 6-10) will: load prompt → render with variables → call adapter → validate response → save dual output
- `load_prompt()` feeds into `render_prompt()` feeds into `adapter.call_for_json()` — this is the prompt pipeline
- `save_dual()` is called after schema validation (Phase 2 validate_with_retry) produces a valid Pydantic model

</code_context>

<specifics>
## Specific Ideas

- PRMT-01 through PRMT-04 specify prompt structure and variable injection
- DUAL-01 and DUAL-02 specify dual output behavior
- Each prompt file should be self-contained — readable by a human opening the .md file
- The `<!-- SYSTEM -->` and `<!-- USER_TEMPLATE -->` markers make it easy to edit prompts without touching code
- `importlib.resources` handles finding prompt files regardless of installation method

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-prompts-dual-output*
*Context gathered: 2026-03-10*
