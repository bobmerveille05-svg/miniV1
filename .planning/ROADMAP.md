# Roadmap: MiniLegion

## Milestones

- ✅ **v1.0 MVP** — 12 phases shipped on 2026-03-10 ([archived roadmap](milestones/v1.0-ROADMAP.md), [archived requirements](milestones/v1.0-REQUIREMENTS.md))

## Next

Use `/gsd-new-milestone` to define the next milestone roadmap.

### Phase 1: Action immediate: harden config with small_model, tool_permissions confirm default, recommended_models vs all_models, model_aliases, context_auto_compact, and provider_healthcheck before research

**Goal:** Harden configuration and pre-research runtime safety so provider/model setup is explicit, validated, and fail-fast before any research-stage LLM work.
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06
**Depends on:** Phase 0
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md - Extend config schema and config CLI for small model, tool permissions, recommended vs all models, and aliases
- [ ] 01-02-PLAN.md - Add provider healthcheck gate and deterministic context compaction in research orchestration
