---
phase: 16-research-brainstorm-mode
plan: 02
subsystem: research
tags: [pydantic, schemas, validation, brainstorm, json-schema, tdd]

# Dependency graph
requires:
  - phase: 16-research-brainstorm-mode/16-01
    provides: ResearchConfig with require_recommendation, JSON schema file with brainstorm fields, brainstorm prompt templates
provides:
  - ResearchSchema with 7 brainstorm fields (problem_framing, facts, assumptions, candidate_directions, tradeoffs, risks, recommendation)
  - model_dump_json() preservation of all brainstorm fields (no silent data loss)
  - Post-validation recommendation enforcement in research() command
  - Synced research.schema.json matching Pydantic model_json_schema() output
  - 5 new tests: 2 direct Pydantic tests + 3 CLI enforcement tests
affects: [research command, brainstorm output, RESEARCH.json serialization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional brainstorm fields appended after required fact fields with None/empty-list defaults — no fact-mode regression"
    - "TDD: write failing tests (RED) → implement (GREEN) with separate commits at each stage"
    - "Post-validate_with_retry enforcement check using require_recommendation config flag"

key-files:
  created: []
  modified:
    - minilegion/core/schemas.py
    - minilegion/cli/commands.py
    - minilegion/schemas/research.schema.json
    - tests/test_cli_brief_research.py

key-decisions:
  - "facts/assumptions/tradeoffs/risks use Field(default_factory=list) not None — preserves array semantics in serialized JSON (empty array vs null)"
  - "recommendation enforcement placed after validate_with_retry (not inside Pydantic model) — JSON schema cannot enforce conditional requirements; Python-level check is the right layer"
  - "research.schema.json regenerated from model_json_schema() output to keep file as single source of truth"

patterns-established:
  - "Schema files in minilegion/schemas/ must be regenerated from model_json_schema() after any model field change"
  - "test_schema_matches_model test acts as contract test ensuring file and model stay in sync"

requirements-completed: [RSM-01, RSM-02, RSM-03, RSM-04]

# Metrics
duration: 15min
completed: 2026-03-12
---

# Phase 16 Plan 02: ResearchSchema Brainstorm Fields + Recommendation Enforcement Summary

**ResearchSchema extended to 18 fields (11 fact + 7 brainstorm), model_dump_json() now preserves all brainstorm fields, and research command enforces non-empty recommendation in brainstorm mode via require_recommendation config flag**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-12T01:30:00Z
- **Completed:** 2026-03-12T01:45:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added 7 optional brainstorm fields to ResearchSchema — `model_dump_json()` no longer silently drops brainstorm data (RSM-02/RSM-03 unblocked)
- Post-validation recommendation enforcement in `research()` command exits code 1 when mode=brainstorm and recommendation is None or empty string (RSM-03/RSM-04)
- 5 new tests: 2 direct Pydantic path tests bypass all mocking to verify the actual serialization fix, 3 CLI tests exercise the enforcement path
- research.schema.json synced to exactly match Pydantic-generated schema (fixes pre-existing test_schema_matches_model failure from Plan 01)

## Task Commits

Each task was committed atomically:

1. **task 1: add brainstorm fields to ResearchSchema** - `46c2777` (feat)
2. **task 2 RED: add failing tests for brainstorm recommendation enforcement** - `f7dfcb5` (test)
3. **task 2 GREEN: recommendation enforcement in commands + schema sync** - `be0b664` (feat)

**Plan metadata:** _(see final commit)_

_Note: TDD task 2 has two commits (test RED → feat GREEN)_

## Files Created/Modified
- `minilegion/core/schemas.py` - Added 7 brainstorm fields + updated class docstring
- `minilegion/cli/commands.py` - Added post-validate_with_retry recommendation enforcement block
- `minilegion/schemas/research.schema.json` - Regenerated from model_json_schema() to match Pydantic model
- `tests/test_cli_brief_research.py` - Added 5 new tests to TestResearchBrainstormMode class

## Decisions Made
- `facts`/`assumptions`/`tradeoffs`/`risks` use `Field(default_factory=list)` not `None` — JSON arrays serialize as `[]` not `null`, maintaining consistency with existing list fields
- Recommendation enforcement is Python-level (in commands.py), not Pydantic validator — JSON Schema cannot enforce conditional field requirements; the command layer is the correct enforcement point
- `research.schema.json` regenerated from `model_json_schema()` to maintain single source of truth; the test_schema_matches_model contract test enforces ongoing sync

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Synced research.schema.json after Pydantic model update**
- **Found during:** task 2 (full test suite run)
- **Issue:** `test_schema_matches_model[research-research.schema.json]` failed because the JSON schema file (updated in Plan 01) had different structure from the Pydantic-generated schema (description text mismatch, `candidate_directions` items schema, `recommendation`/`problem_framing` nullable types, `additionalProperties` at root)
- **Fix:** Regenerated `research.schema.json` from `ResearchSchema.model_json_schema()` output to ensure exact byte-level match
- **Files modified:** `minilegion/schemas/research.schema.json`
- **Verification:** `test_schema_matches_model[research-research.schema.json]` passes; all schema tests pass
- **Committed in:** `be0b664` (task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug: schema file out of sync with model)
**Impact on plan:** Auto-fix was necessary for test suite correctness. Strictly within plan scope (same files).

## Issues Encountered
None — the schema sync was the only issue and was auto-fixed inline.

## Next Phase Readiness
- RSM-01 through RSM-04 all satisfied — brainstorm mode gap closure complete
- Phase 16 is fully done (Plan 01 + Plan 02 complete)
- Ready for Phase 17 (final phase)

---
*Phase: 16-research-brainstorm-mode*
*Completed: 2026-03-12*
