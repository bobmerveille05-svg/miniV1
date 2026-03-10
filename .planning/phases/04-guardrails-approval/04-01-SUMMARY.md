---
phase: 04-guardrails-approval
plan: 01
subsystem: safety
tags: [preflight, scope-lock, path-normalization, guardrails, validation]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Stage enum, ProjectState, save_state/load_state, exceptions
provides:
  - check_preflight() — declarative file+approval validation per stage
  - normalize_path() — cross-platform path canonicalization
  - check_scope() / validate_scope() — scope lock enforcement
  - REQUIRED_FILES / REQUIRED_APPROVALS — declarative requirements mappings
affects: [04-02, 06-brief-research, 07-design, 08-plan, 09-execute, 10-review]

# Tech tracking
tech-stack:
  added: []
  patterns: [declarative-requirements-mapping, fail-fast-validation, set-based-scope-comparison]

key-files:
  created:
    - minilegion/core/preflight.py
    - minilegion/core/scope_lock.py
    - tests/test_preflight.py
    - tests/test_scope_lock.py
  modified: []

key-decisions:
  - "Fail-fast on first missing prerequisite — clearer error messages, simpler control flow"
  - "Declarative dict mapping Stage→requirements — easy to extend when new stages are added"
  - "normalize_path avoids os.path.normpath — it converts to backslashes on Windows"
  - "check_scope returns original (un-normalized) paths — preserves user-facing context"

patterns-established:
  - "Declarative requirements mapping: dict[Stage, list[str]] for stage prerequisites"
  - "Path normalization before comparison: all scope checks use normalize_path() on both sides"
  - "Fail-fast validation: raise on first missing prerequisite, not batch errors"

requirements-completed: [GUARD-01, GUARD-02, GUARD-03, GUARD-04, GUARD-05]

# Metrics
duration: 3min
completed: 2026-03-10
---

# Phase 4 Plan 1: Pre-flight Checks & Scope Lock Summary

**Declarative pre-flight validation (file + approval gates per stage) and scope lock with cross-platform path normalization**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T13:20:47Z
- **Completed:** 2026-03-10T13:23:52Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Pre-flight checks enforce file existence and approval requirements per pipeline stage (GUARD-01, GUARD-02, GUARD-03)
- Scope lock detects out-of-scope file mutations with path normalization handling ./ prefix, backslashes, trailing slashes, and Windows case (GUARD-04, GUARD-05)
- 34 unit tests covering all edge cases including Windows-specific path handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Pre-flight checks module** — TDD
   - RED: `64f8245` (test) — 15 failing tests for file/approval/safe-mode checks
   - GREEN: `5989cd8` (feat) — Implementation with declarative requirements mapping

2. **Task 2: Scope lock and path normalization** — TDD
   - RED: `67f887e` (test) — 19 failing tests for normalize_path, check_scope, validate_scope
   - GREEN: `143a10e` (feat) — Implementation with set-based scope comparison

## Files Created/Modified
- `minilegion/core/preflight.py` — Pre-flight check function with REQUIRED_FILES and REQUIRED_APPROVALS declarative mappings
- `minilegion/core/scope_lock.py` — normalize_path(), check_scope(), validate_scope() for scope enforcement
- `tests/test_preflight.py` — 15 tests: TestPreflightFiles (7), TestPreflightApprovals (6), TestSafeModeGuards (2)
- `tests/test_scope_lock.py` — 19 tests: TestNormalizePath (10), TestCheckScope (9)

## Decisions Made
- Fail-fast on first missing prerequisite — clearer error messages, simpler control flow
- Declarative dict mapping Stage→requirements — easy to extend when new stages are added
- normalize_path avoids os.path.normpath — it converts to backslashes on Windows
- check_scope returns original (un-normalized) paths — preserves user-facing context in error messages

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Pre-flight checks ready for pipeline stages (Phases 6-10) to call before LLM interactions
- Scope lock ready for patch application in Phase 9 (execute stage)
- Phase 4 Plan 2 (approval gates) can proceed — no blockers

---
*Phase: 04-guardrails-approval*
*Completed: 2026-03-10*
