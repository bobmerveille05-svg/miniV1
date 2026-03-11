---
phase: 01-action-immediate-harden-config-with-small-model-tool-permissions-confirm-default-recommended-models-vs-all-models-model-aliases-context-auto-compact-and-provider-healthcheck-before-research
plan: 01
subsystem: config
tags: [pydantic, typer, config, model-catalogs]
requires: []
provides:
  - Hardened config defaults for small-model and tool-permission settings
  - Config-backed recommended and full model catalogs with alias persistence
  - README contract for new config fields and interactive catalog selection
affects: [research, provider-healthcheck, context-compaction, config-cli]
tech-stack:
  added: []
  patterns:
    - schema-backed provider model catalogs
    - shared CLI model selection helper
key-files:
  created: []
  modified:
    - minilegion/core/config.py
    - minilegion/cli/config_commands.py
    - tests/test_config.py
    - tests/test_config_commands.py
    - README.md
key-decisions:
  - "Model catalogs and aliases now live in MiniLegionConfig as provider-keyed defaults instead of CLI-only constants."
  - "config init and config model share one branching flow for recommended, full-catalog, and alias-based model selection."
patterns-established:
  - "Provider catalogs use {id, description} entries so JSON config and runtime access share one stable shape."
  - "Manual alias input resolves against provider-specific aliases and validates against configured all_models before save."
requirements-completed: [CFG-01, CFG-02, CFG-03, CFG-04]
duration: 7min
completed: 2026-03-11
---

# Phase 01 Plan 01: Extend config schema and config CLI for small model, tool permissions, recommended vs all models, and aliases Summary

**Validated config defaults for small-model safety, config-backed provider catalogs, and canonical alias persistence in the interactive config CLI**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-11T03:41:19Z
- **Completed:** 2026-03-11T03:47:56Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Added `small_model`, `tool_permissions`, `recommended_models`, `all_models`, `model_aliases`, `context_auto_compact`, and `provider_healthcheck` to `MiniLegionConfig` with backward-compatible defaults.
- Moved model browsing to config-backed catalogs and shared one CLI helper for recommended, full-catalog, and alias/manual model selection.
- Updated `README.md` so the shipped config JSON and CLI behavior match the implemented defaults and persistence rules.

## task Commits

Each task was committed atomically:

1. **task 1: extend config schema with hardened fields and safe defaults** - `7563df3` (test), `1f4d8a0` (feat)
2. **task 2: add recommended-vs-all catalog helpers and canonical alias resolution** - `444ffeb` (test), `5a7ef3c` (feat)
3. **task 3: update user-facing config documentation to match shipped behavior** - `bcad64f` (docs)

**Plan metadata:** pending final docs commit

## Files Created/Modified
- `minilegion/core/config.py` - adds validated hardening fields, provider catalogs, and alias defaults.
- `minilegion/cli/config_commands.py` - shares model source selection, alias resolution, and canonical persistence.
- `tests/test_config.py` - covers new defaults, legacy backfill, invalid tool permissions, and catalog shapes.
- `tests/test_config_commands.py` - covers recommended vs full catalog branching, alias persistence, and error handling.
- `README.md` - documents the new config fields, default catalogs, and alias behavior.

## Decisions Made
- Stored provider model catalogs in config defaults so runtime JSON and CLI prompts use the same shape.
- Used provider-keyed alias maps and validated manual input against `all_models` before saving canonical model IDs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The worktree already had staged planning files before execution, so the first RED-phase commit also captured those staged docs; later task commits used `git commit --only` to keep task-specific code changes isolated.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Config hardening and config CLI catalog behavior are in place for the remaining Phase 1 research-safety work.
- `context_auto_compact` and `provider_healthcheck` now exist in config and are ready to be enforced by the next plan.

## Self-Check: PASSED
