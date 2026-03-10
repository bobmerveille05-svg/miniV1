---
phase: 03-llm-adapter
plan: 01
subsystem: adapters
tags: [openai, llm, abc, dataclass, sdk]

# Dependency graph
requires:
  - phase: 02-schemas
    provides: "Schema registry and validation for structured LLM output"
  - phase: 01-foundation
    provides: "MiniLegionConfig, LLMError, validate_with_retry callable interface"
provides:
  - "LLMAdapter ABC — provider-agnostic contract for LLM calls"
  - "LLMResponse and TokenUsage frozen dataclasses for structured responses"
  - "OpenAIAdapter concrete implementation using openai SDK"
  - "Callable[[str], str] pattern compatible with validate_with_retry()"
affects: [04-guardrails, 05-approval, 06-research, 07-design, 08-plan, 09-execute, 10-review]

# Tech tracking
tech-stack:
  added: [openai>=1.0]
  patterns: [lazy-client-init, abc-adapter-pattern, frozen-dataclass-responses, exception-chaining]

key-files:
  created:
    - minilegion/adapters/base.py
    - minilegion/adapters/openai_adapter.py
    - tests/test_adapter_base.py
    - tests/test_openai_adapter.py
  modified:
    - minilegion/adapters/__init__.py
    - pyproject.toml

key-decisions:
  - "Lazy client init — OpenAI client created on first call, not at construction"
  - "max_retries=0 on SDK client — retry logic lives in core/retry.py"
  - "_do_call() private helper shared between call() and call_for_json() to avoid duplication"
  - "Frozen dataclasses for LLMResponse/TokenUsage — immutable after construction"

patterns-established:
  - "ABC adapter pattern: subclass LLMAdapter, implement call() + call_for_json(), no other changes needed"
  - "Exception chaining: all SDK errors wrapped via raise LLMError(...) from exc"
  - "Lazy init: expensive resources created on demand, not at import/construction time"

requirements-completed: [ADPT-01, ADPT-02, ADPT-03, ADPT-04]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 3 Plan 1: LLM Adapter Summary

**LLMAdapter ABC with frozen dataclass responses and OpenAI SDK adapter featuring lazy client init, JSON mode, and exception chaining**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T13:51:02Z
- **Completed:** 2026-03-10T13:54:46Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- LLMAdapter ABC with call() and call_for_json() abstract methods — new adapters only need subclass + implement
- TokenUsage and LLMResponse frozen dataclasses for immutable structured responses
- OpenAIAdapter with lazy client init, API key validation from config, response_format for JSON mode
- All OpenAI SDK errors wrapped in LLMError with raise...from exc chaining
- openai>=1.0 added to project dependencies
- 30 new tests (9 base + 21 adapter) all passing, 263 total

## Task Commits

Each task was committed atomically:

1. **Task 1: Abstract base class, dataclasses, and __init__.py re-exports** - `d8376fc` (feat)
2. **Task 2: OpenAI adapter implementation with dependency update** - `937de51` (feat)

## Files Created/Modified
- `minilegion/adapters/base.py` - LLMAdapter ABC, TokenUsage, LLMResponse frozen dataclasses
- `minilegion/adapters/openai_adapter.py` - OpenAIAdapter with lazy init, error wrapping, JSON mode
- `minilegion/adapters/__init__.py` - Re-exports for public API (all 4 names)
- `pyproject.toml` - Added openai>=1.0 to dependencies
- `tests/test_adapter_base.py` - 9 tests for ABC enforcement, dataclasses, imports
- `tests/test_openai_adapter.py` - 21 tests for lazy init, key validation, params, errors

## Decisions Made
- Lazy client init: OpenAI client created on first call, not at construction time — avoids requiring API key at import/construction
- max_retries=0 on SDK client: retry logic lives in core/retry.py, not the SDK
- _do_call() private helper shared between call() and call_for_json() to avoid code duplication
- Frozen dataclasses for LLMResponse/TokenUsage: immutable after construction for safety

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- LLM adapter layer complete and fully tested
- Ready for Phase 4 (Guardrails) which will use the adapter for LLM calls
- Pipeline stages (Phases 6-10) can construct an adapter, bind a system prompt via lambda, and pass the resulting Callable[[str], str] to validate_with_retry()

## Self-Check: PASSED

- All 6 created/modified files exist on disk
- Both task commits verified: d8376fc, 937de51
- 263 tests passing (233 existing + 30 new)

---
*Phase: 03-llm-adapter*
*Completed: 2026-03-10*
