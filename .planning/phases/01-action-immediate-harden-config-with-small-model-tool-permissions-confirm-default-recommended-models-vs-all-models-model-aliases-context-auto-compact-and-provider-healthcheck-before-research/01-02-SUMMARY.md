---
phase: 01-action-immediate-harden-config-with-small-model-tool-permissions-confirm-default-recommended-models-vs-all-models-model-aliases-context-auto-compact-and-provider-healthcheck-before-research
plan: 02
subsystem: infra
tags: [provider-health, context-compaction, config, research, fail-fast]

# Dependency graph
requires:
  - phase: 01-01
    provides: config fields provider_healthcheck and context_auto_compact already in MiniLegionConfig
provides:
  - Provider healthcheck module with fail-fast gate before research
  - Context auto-compaction with deterministic truncation marker in research stage
  - scan_max_file_size_kb normalization fix in commands.py and pipeline.py
affects: [research stage, pipeline service layer, any future stage calling scan/LLM]

# Tech tracking
tech-stack:
  added: []
  patterns: [fail-fast gate before LLM work, deterministic context truncation with explicit marker]

key-files:
  created:
    - minilegion/core/provider_health.py
    - tests/test_provider_health.py
  modified:
    - minilegion/cli/commands.py
    - minilegion/core/pipeline.py
    - tests/test_cli_brief_research.py

key-decisions:
  - "Healthcheck runs before check_preflight, scan_codebase, render_prompt, and validate_with_retry — earliest possible fail-fast"
  - "Context compaction uses explicit [CONTEXT TRUNCATED: ...] marker so LLM knows data was cut"
  - "Compaction threshold is 50,000 chars — keeps prompt budget bounded for typical models"
  - "scan_max_file_size bug fixed: both commands.py and pipeline.py now use scan_max_file_size_kb * 1024"
  - "Ollama probe hits /api/tags endpoint with configured timeout (lightweight local check)"
  - "openai-compatible provider requires both base_url and API key env var"

patterns-established:
  - "Fail-fast gate pattern: config bool gates expensive/irreversible work at earliest decision point"
  - "Deterministic compaction: truncate at fixed char threshold + append explicit marker line"

requirements-completed: [CFG-05, CFG-06]

# Metrics
duration: 25min
completed: 2026-03-11
---

# Plan 01-02 Summary

**Provider healthcheck fail-fast gate and deterministic context compaction wired into research stage with scan_max_file_size_kb normalization**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-11
- **Completed:** 2026-03-11
- **Tasks:** 2 (TDD: 4 commits total)
- **Files modified:** 5

## Accomplishments
- `minilegion/core/provider_health.py` — reusable provider-readiness checks for openai, anthropic, gemini, openai-compatible, and ollama with actionable error messages
- Healthcheck gate wired into `research()` in `commands.py` and `run_research()` in `pipeline.py` — runs before preflight, scanner, prompt rendering, or LLM
- Deterministic context compaction in research stage — truncates oversized codebase context at 50,000 chars with explicit `[CONTEXT TRUNCATED: ...]` marker when `context_auto_compact=True`
- Fixed long-standing bug: `scan_max_file_size` (nonexistent) → `scan_max_file_size_kb * 1024` in both `commands.py` and `pipeline.py`
- 8 new integration tests covering all ordering and compaction behaviours; `TestResearchCommand` autouse fixture ensures healthcheck is properly isolated

## Task Commits

1. **task 1 (RED): failing tests for provider healthcheck** — `53395d0` (test)
2. **task 1 (GREEN): implement provider readiness helper** — `0c08519` (feat)
3. **task 2 (RED): failing tests for healthcheck gate, compaction, scan_max** — `bd63ffd` (test)
4. **task 2 (GREEN): wire healthcheck + compaction, fix scan_max_file_size_kb** — `2211ae5` (feat)

## Files Created/Modified
- `minilegion/core/provider_health.py` — provider readiness checks (no-op gate, env var checks, Ollama HTTP probe)
- `minilegion/cli/commands.py` — healthcheck + compaction wired into `research()`; `scan_max_file_size_kb` fix in `_read_source_files`
- `minilegion/core/pipeline.py` — healthcheck + compaction wired into `run_research()`; `scan_max_file_size_kb` fix in `read_source_files`
- `tests/test_provider_health.py` — 6 unit tests for provider health pass/fail branches
- `tests/test_cli_brief_research.py` — 8 new integration tests; autouse fixture for existing `TestResearchCommand`

## Decisions Made
- Healthcheck ordering: runs before `check_preflight` so nothing expensive fires on an unready provider
- Compaction threshold of 50,000 chars chosen as safe default; fits within typical model context windows without cutting too aggressively for small codebases
- `TestResearchCommand` autouse `_noop_healthcheck` fixture to avoid leaking real healthcheck into pre-existing tests

## Deviations from Plan

None — plan executed exactly as written. Both tasks discovered that Task 1 (provider_health.py + test_provider_health.py) had already been created by an earlier executor run; existing 6 tests already passed. Task 2 was the gap that needed closing.

## Issues Encountered
- Existing `TestResearchCommand` tests did not mock `run_provider_healthcheck`, causing 10 test failures after wiring. Fixed with an `autouse` pytest fixture at class level — no test logic changes needed.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 1 is fully complete: config schema hardened (01-01), provider healthcheck + context compaction wired (01-02)
- 613 tests passing, 0 failures
- Ready for phase verification (`gsd-verifier`) and phase close

---
*Phase: 01-action-immediate-harden-config*
*Completed: 2026-03-11*

## Self-Check: PASSED
