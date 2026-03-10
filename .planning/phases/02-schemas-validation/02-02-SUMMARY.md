---
phase: 02-schemas-validation
plan: 02
subsystem: validation
tags: [pydantic, regex, json, fixups, retry, error-handling, debug]

# Dependency graph
requires:
  - phase: 02-schemas-validation plan 01
    provides: "Schema registry with validate() function, Pydantic artifact models"
  - phase: 01-foundation
    provides: "MiniLegionConfig.max_retries, write_atomic(), ValidationError exception"
provides:
  - "Pre-parse fixup pipeline (strip_markdown_fences, fix_trailing_commas, strip_bom_and_control, apply_fixups)"
  - "Retry orchestration (validate_with_retry, summarize_errors, save_raw_debug)"
  - "RAW_DEBUG file capture for failed validation debugging"
affects: [03-llm-adapter, pipeline-stages]

# Tech tracking
tech-stack:
  added: []
  patterns: [pre-parse-fixup-pipeline, retry-with-error-feedback, raw-debug-capture]

key-files:
  created:
    - minilegion/core/fixups.py
    - minilegion/core/retry.py
    - tests/test_fixups.py
    - tests/test_retry.py
  modified: []

key-decisions:
  - "Simple regex for trailing commas — known edge case with commas in strings, acceptable per CONTEXT.md"
  - "Fixup order: BOM→fences→commas — BOM affects fence detection, fences contain trailing commas"
  - "PydanticValidationError aliased explicitly to avoid collision with minilegion.core.exceptions.ValidationError"
  - "Error feedback capped at 5 issues to keep retry prompts manageable for LLMs"

patterns-established:
  - "Pre-parse fixup pipeline: BOM/control → fence strip → trailing comma fix before any validation"
  - "Retry-with-feedback: augment prompt with human-readable error summary, not raw Pydantic dumps"
  - "RAW_DEBUG capture: save last raw output + errors to timestamped file on retry exhaustion"
  - "PydanticValidationError alias pattern for disambiguation"

requirements-completed: [SCHM-03, SCHM-04, SCHM-05]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 2 Plan 2: Pre-parse Fixups + Retry Logic Summary

**Pre-parse fixup pipeline (BOM, fences, trailing commas) and retry-with-feedback orchestration with RAW_DEBUG capture for exhausted retries**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T11:54:16Z
- **Completed:** 2026-03-10T11:58:32Z
- **Tasks:** 2
- **Files created:** 4
- **Tests added:** 53 (33 fixup + 20 retry)
- **Total test count:** 233 (180 existing + 53 new)

## Accomplishments
- Pre-parse fixup pipeline handles 3 common LLM output quirks: BOM/control chars, markdown fences, trailing commas
- Retry loop calls LLM with human-readable error feedback (capped at 5 issues) instead of raw Pydantic dumps
- RAW_DEBUG capture saves timestamped debug files via write_atomic when retries are exhausted
- Full validation-retry loop ready for Phase 3 LLM adapter integration

## Task Commits

Each task was committed atomically following TDD (RED→GREEN):

1. **Task 1: Pre-parse fixup pipeline**
   - RED: `3d11f9b` — test(02-02): add failing tests for pre-parse fixup pipeline
   - GREEN: `0539a09` — feat(02-02): implement pre-parse fixup pipeline

2. **Task 2: Retry logic with error feedback and RAW_DEBUG capture**
   - RED: `10a1142` — test(02-02): add failing tests for retry logic with error feedback and RAW_DEBUG
   - GREEN: `cc670fb` — feat(02-02): implement retry logic with error feedback and RAW_DEBUG capture

## Files Created/Modified
- `minilegion/core/fixups.py` — Pre-parse fixup pipeline: strip_bom_and_control, strip_markdown_fences, fix_trailing_commas, apply_fixups
- `minilegion/core/retry.py` — Retry orchestration: summarize_errors, save_raw_debug, validate_with_retry
- `tests/test_fixups.py` — 33 tests covering all fixup functions + pipeline + edge cases
- `tests/test_retry.py` — 20 tests covering error summarization, debug file saving, and full retry loop

## Decisions Made
- **Simple regex for trailing commas:** `r',\s*([}\]])'` may affect commas inside string values — accepted as an edge case per CONTEXT.md guidance to keep fixups simple
- **Fixup pipeline order (BOM→fences→commas):** BOM chars can interfere with fence regex detection; fences wrap the JSON body that may have trailing commas
- **Explicit PydanticValidationError alias:** Import as `PydanticValidationError` to avoid collision with `minilegion.core.exceptions.ValidationError`
- **Error feedback capped at 5 issues:** Keeps retry prompts concise and actionable for LLMs rather than overwhelming with every validation error

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Fixup pipeline and retry loop are ready for Phase 3 (LLM Adapter) integration
- `validate_with_retry` accepts `Callable[[str], str]` as the LLM call boundary — adapter just needs to provide this callable
- Phase 2 (Schemas & Validation) is now complete with all schemas, registry, fixups, and retry logic implemented

## Self-Check: PASSED

- All 4 created files verified on disk ✓
- All 4 task commits verified in git log ✓
- 233 tests pass (full suite regression check) ✓

---
*Phase: 02-schemas-validation*
*Completed: 2026-03-10*
