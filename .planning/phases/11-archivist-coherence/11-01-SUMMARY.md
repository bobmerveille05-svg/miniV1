# Phase 11-01 Summary: render_decisions_md + Archive Preflight

**Plan:** 11-01
**Wave:** 1
**Status:** Complete

## What Was Done

### Task 1: render_decisions_md() in renderer.py
- Added `render_decisions_md(design_data: DesignSchema) -> str` to `minilegion/core/renderer.py`
- Function placed after all existing render functions, before `_RENDERERS` dict
- NOT registered in `_RENDERERS` — called directly from `archive()` via `write_atomic()`
- Format: `# Architecture Decisions\n\n` header, then per decision: `### Decision: {d}`, `**Rationale:** {r}`, `**Alternatives Rejected:**` section
- Empty decisions list → `_No architecture decisions recorded._` placeholder

### Task 2: Stage.ARCHIVE in preflight dicts
- Added `Stage.ARCHIVE: ["REVIEW.json", "PLAN.json", "EXECUTION_LOG.json", "DESIGN.json"]` to `REQUIRED_FILES`
- Added `Stage.ARCHIVE: ["review_approved"]` to `REQUIRED_APPROVALS`
- Updated docstring comment (INIT, BRIEF no longer include ARCHIVE as "no requirements")

## Tests Added

- `TestRenderDecisionsMd` (9 tests) in `tests/test_renderer.py`
- `TestArchivePreflight` (7 tests) in `tests/test_preflight.py`

## Verification

All 16 new tests pass. Full suite: 530 passing (490 baseline + 40 new Phase 11 Wave 1 combined).
