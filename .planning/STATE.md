---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Portable Kernel
status: completed
stopped_at: Completed 17-rollback-doctor-health-surface/17-02-PLAN.md
last_updated: "2026-03-12T00:00:00Z"
last_activity: 2026-03-12 — Phase 17 complete (rollback + doctor). v1.1 Portable Kernel milestone SHIPPED.
progress:
  total_phases: 15
  completed_phases: 15
  total_plans: 29
  completed_plans: 29
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A user can open any old project, run `minilegion status` then `minilegion context claude`, and resume work in under 2 minutes — portable, auditable, resumable.
**Current focus:** v1.1 Portable Kernel — COMPLETE ✅

## Current Position

Phase: 17 of 17 (v1.1 gap closure) — rollback + doctor COMPLETE
Plan: 2 of 2 in current phase ✅
Status: **v1.1 milestone COMPLETE** — all phases and plans done
Last activity: 2026-03-12 — Phase 17 UAT 7/7 passed. Rollback + Doctor shipped.

Progress: [██████████] 100% (29 of 29 plans complete)

## Performance Metrics

**Velocity (v1.1 so far):**
- Total plans completed: 8 (Phase 1: 2, Phase 13: 2, Phase 16: 4)
- Average duration: ~11 min
- Total execution time: ~85 min

**Recent Trend:**
- Phase 1: 2 plans, ~11 min total
- Phase 13: 2 plans, ~6 min total
- Phase 16 Plan 1: ~18 min
- Phase 16 Plan 2: ~15 min
- Trend: Maintaining velocity

| Phase | Plan | Duration | Tasks | Files |
|---|---|---|---|---|
| 02-context-adapters | 01 | ~15 min | 2 | 5 |
| 02-context-adapters | 02 | ~8 min | 2 | 4 |
| 13-context-evidence-verification-backfill | 01 | ~4 min | 2 | 2 |
| 13-context-evidence-verification-backfill | 02 | ~2 min | 3 | 2 |
| 16-research-brainstorm-mode | 01 | ~18 min | 5 | 5 |
| 16-research-brainstorm-mode | 02 | ~15 min | 2 | 4 |

## Accumulated Context

### Key Decisions

- [v1.1 Roadmap]: context command is Phase 2 (highest value — unblocks portability)
- [v1.1 Roadmap]: history extraction before evidence (evidence files reference history events)
- [v1.1 Roadmap]: validate+advance decoupled after evidence (advance gate reads evidence files)
- [v1.1 Roadmap]: rollback depends on validate+advance (needs clean state semantics)
- [v1.1 Roadmap]: doctor is last (checks all other slices' outputs)
- [v1.1 Constraint]: All existing pipeline, approval gates, scope lock, revise loop must remain intact
- [Phase 01]: Model catalogs and aliases now live in MiniLegionConfig as provider-keyed defaults
- [Phase 02-01]: ContextConfig uses default_factory so omitting 'context' in JSON gives defaults (CFG-09)
- [Phase 02-01]: assemble_context is a pure function — CLI command owns all file writes
- [Phase 02-01]: Graceful degradation: missing adapters/templates/memory produce stub text, never raise
- [Phase 02-01]: Warn to stderr (not raise) when assembled context exceeds warn_threshold
- [Phase 02-02]: Adapter/template content as module-level constants in commands.py — simpler than bundled package files
- [Phase 02-02]: init command extended (not replaced) to add adapters/templates/memory after prompts/
- [Phase 02-02]: STAGE_TEMPLATES dict covers all 8 Stage enum values — every pipeline stage has a template
- [Phase 13-01]: `## Compact Plan` is rendered deterministically from PLAN.json pending tasks minus STATE completed task IDs
- [Phase 13-01]: Missing or malformed PLAN.json is non-fatal and yields `_No plan context available._`
- [Phase 13-02]: Phase 2 verification now maps CTX/CFG requirements to explicit pytest node IDs and implementation file references.
- [Phase 13-02]: CTX-06 evidence is field-level anchored to ADR-0007 (`status`, `context`, `decision`, `consequences`, `rejected alternatives`, `success criterion`).
- [Phase 16-01]: ResearchConfig follows ContextConfig/WorkflowConfig pattern with default_factory for non-breaking backward compatibility
- [Phase 16-01]: Brainstorm mode uses dual prompts in single researcher.md file with mode-aware template substitution
- [Phase 16-01]: Schema supports both fact and brainstorm modes via optional fields (no discriminator needed)
- [Phase 16-02]: facts/assumptions/tradeoffs/risks use Field(default_factory=list) not None — preserves array semantics (empty array vs null) in brainstorm serialization
- [Phase 16-02]: Recommendation enforcement is Python-level in commands.py (not Pydantic validator) — JSON Schema cannot enforce conditional requirements
- [Phase 16-02]: research.schema.json regenerated from model_json_schema() to maintain single source of truth; test_schema_matches_model enforces ongoing sync

### Pending Todos

None.

### Blockers/Concerns

None. Phase 17 complete — all RBK + DOC requirements satisfied. 15 TestRollback/TestDoctor tests passing. UAT 7/7 passed. v1.1 Portable Kernel milestone SHIPPED.

## Session Continuity

Last session: 2026-03-12T00:00:00Z
Stopped at: Completed 17-rollback-doctor-health-surface/17-02-PLAN.md
Resume file: None
