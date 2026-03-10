---
phase: 07-design-stage
plan: 01
subsystem: cli
tags: [typer, pydantic, design, llm, pipeline]

# Dependency graph
requires:
  - phase: 06-brief-research
    provides: research() command pattern, OpenAIAdapter, validate_with_retry, save_dual, approve_research

provides:
  - design() CLI command: preflight → prompt → LLM → validate_with_retry("design") → save_dual → approve_design → state transition
  - DSGN-01..05 requirements satisfied
  - DesignSchema with min_length=1 enforcement on alternatives_rejected
  - designer.md updated to explicitly reference existing_conventions from RESEARCH.json
  - 10 unit tests in tests/test_cli_design.py (441 total passing)

affects: [08-plan-stage, 11-archivist-coherence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "design() mirrors research() exactly — pure wiring phase pattern"
    - "alternatives_rejected: min_length=1 in DesignSchema schema enforcement"
    - "conventions_to_follow explicitly drawn from existing_conventions in RESEARCH.json via prompt"

key-files:
  created:
    - tests/test_cli_design.py
    - .planning/phases/07-design-stage/07-RESEARCH.md
    - .planning/phases/07-design-stage/07-VALIDATION.md
    - .planning/phases/07-design-stage/07-01-PLAN.md
    - .planning/phases/07-design-stage/07-VERIFICATION.md
  modified:
    - minilegion/cli/commands.py
    - minilegion/core/schemas.py
    - minilegion/prompts/designer.md
    - minilegion/schemas/design.schema.json

key-decisions:
  - "design() follows exact research() pattern — same 12-step flow, no new modules"
  - "focus_files_content placeholder '(Focus file reading deferred to Phase 9)' — avoids unresolved {{placeholder}} crash in render_prompt()"
  - "alternatives_rejected enforced via min_length=1 Field constraint, NOT custom validator"
  - "conventions_to_follow linked to existing_conventions via prompt instruction, not code"
  - "approve_design import added alongside approve_brief, approve_research on line 15"

patterns-established:
  - "Pipeline command wiring: every stage command mirrors research() with stage-specific substitutions"
  - "Schema enforcement: use Field(min_length=N) for list length constraints, not @validator"
  - "Prompt conventions: reference specific JSON field names (existing_conventions) to guide LLM field-level sourcing"

requirements-completed:
  - DSGN-01
  - DSGN-02
  - DSGN-03
  - DSGN-04
  - DSGN-05

# Metrics
duration: ~20min
completed: 2026-03-10
---

# Phase 7: Design Stage Summary

**design() command wires the full designer pipeline (preflight → LLM → DesignSchema validation → dual output → approval → state transition) with schema-enforced alternatives_rejected and research-linked conventions**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-10T17:30:00Z
- **Completed:** 2026-03-10T18:00:00Z
- **Tasks:** 2 (+ 2 gap fixes)
- **Files modified:** 4

## Accomplishments
- `design()` command fully implemented — replaces `_pipeline_stub(Stage.DESIGN)` with ~60-line implementation mirroring `research()`
- `DesignSchema.ArchitectureDecision.alternatives_rejected` now enforces `min_length=1` via Pydantic `Field` constraint
- `designer.md` updated to explicitly reference `existing_conventions` from RESEARCH.json for `conventions_to_follow`
- 10 unit tests in `tests/test_cli_design.py`, all passing (441 total suite)

## Task Commits

1. **task 1: wire design() command** — `7229a76` (feat(07): implement design command and tests)
2. **gap fix: DSGN-03 + DSGN-04** — `33a92eb` (fix(07): enforce alternatives_rejected min_length=1, update designer prompt conventions)

## Files Created/Modified
- `minilegion/cli/commands.py` — design() fully implemented; approve_design imported
- `minilegion/core/schemas.py` — ArchitectureDecision.alternatives_rejected gets min_length=1
- `minilegion/prompts/designer.md` — conventions_to_follow instruction now references existing_conventions
- `minilegion/schemas/design.schema.json` — regenerated to include minItems:1 for alternatives_rejected
- `tests/test_cli_design.py` — 10 tests covering DSGN-01..05 + APRV-03/06

## Decisions Made
- `focus_files_content` receives placeholder string `"(Focus file reading deferred to Phase 9)"` — empty string would leave unresolved `{{placeholder}}` in render_prompt() causing a crash
- Schema enforcement via `Field(min_length=1)` preferred over custom Pydantic validator — simpler, reflected in JSON Schema, no test breakage since VALID_DESIGN fixture already has 1 entry
- Prompt-level enforcement for `conventions_to_follow` → `existing_conventions` link: explicit field name reference in prompt instruction is sufficient; no code-level assertion needed

## Deviations from Plan

### Auto-fixed Issues

**1. [DSGN-03] alternatives_rejected not schema-enforced**
- **Found during:** gsd-verifier run after execution
- **Issue:** `ArchitectureDecision.alternatives_rejected` used `default_factory=list` without `min_length=1` — empty list was accepted, violating success criterion "schema validation enforces this"
- **Fix:** `Field(default_factory=list, min_length=1)` in schemas.py; design.schema.json regenerated
- **Files modified:** minilegion/core/schemas.py, minilegion/schemas/design.schema.json
- **Verification:** `test_json_schemas.py::test_schema_matches_model[design]` now passes
- **Committed in:** 33a92eb

**2. [DSGN-04] conventions_to_follow not explicitly linked to RESEARCH.json**
- **Found during:** gsd-verifier run after execution
- **Issue:** designer.md description for conventions_to_follow was generic ("maintain consistency with the existing codebase") — no reference to `existing_conventions` field from RESEARCH.json
- **Fix:** Updated prompt field description to explicitly reference `existing_conventions` in Research Findings JSON
- **Files modified:** minilegion/prompts/designer.md
- **Verification:** Prompt field description now reads: "drawn directly from the 'existing_conventions' field in the Research Findings JSON above"
- **Committed in:** 33a92eb

---

**Total deviations:** 2 auto-fixed (schema constraint gap, prompt instruction gap)
**Impact on plan:** Both auto-fixes required to satisfy success criteria. No scope creep.

## Issues Encountered
- `test_json_schemas.py::test_schema_matches_model[design]` failed after adding `min_length=1` — schema file was stale. Fixed by regenerating design.schema.json from model.

## Next Phase Readiness
- Phase 8 (Plan Stage): `plan()` command can follow identical pattern — `validate_with_retry("plan", ...)`, `save_dual`, `approve_plan`, `Stage.PLAN`
- All infrastructure ready: PlanSchema defined, approve_plan in approval.py, planner.md exists, render_plan_md in renderer.py

---
*Phase: 07-design-stage*
*Completed: 2026-03-10*
