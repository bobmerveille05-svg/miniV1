# MiniLegion

## What This Is

MiniLegion is a file-centric, multi-provider, LLM-assisted protocol for software delivery. It runs a strict pipeline (`brief -> research -> design -> plan -> execute -> review -> archive`) with schema validation, approval gates, and deterministic archival.

## Core Value

A complete, validated path from brief to committed code that stays auditable and safe under human control.

## Current State

- **Shipped version:** v1.0 MVP (2026-03-10), v1.1 Phase 1 pre-work (2026-03-11)
- **Active milestone:** v1.1 Portable Kernel (Phases 2–8, in progress)
- **Coverage:** 12 v1.0 phases + 1 v1.1 pre-work phase completed; 620 tests passing
- **Production capabilities delivered:**
  - Full 8-stage pipeline with enforced transitions
  - 5 approval gates + immutable rejection behavior
  - Schema validation + bounded retry + debug capture
  - Scope lock + coherence checks + deterministic archive
  - Fast mode (`--fast`, `--skip-research-design`)
  - Multi-provider adapters (OpenAI, Anthropic, Gemini, Ollama, OpenAI-compatible)
  - Interactive provider/model configuration (`minilegion config init`, `minilegion config model`)
  - Hardened config: small_model, tool_permissions, recommended_models, model_aliases, context_auto_compact, provider_healthcheck

## Current Milestone: v1.1 Portable Kernel

**Goal:** Transform miniV1 from a solid LLM-orchestrated pipeline CLI into a portable, auditable, resumable kernel. After this milestone, a user can open any old project, run `minilegion status` then `minilegion context claude`, and resume work in under 2 minutes.

**Phases:** 2–8 (7 phases)
**Requirements:** 30 defined in `.planning/REQUIREMENTS.md`
**ADR:** `.planning/milestones/v1.1-ADR-0007.md`

**Slices:**
- Phase 2: Context + Adapters (`minilegion context <tool>`)
- Phase 3: History Extraction (`project-ai/history/`, `minilegion history`)
- Phase 4: Evidence Bundles (`project-ai/evidence/`)
- Phase 5: Validate + Advance as distinct commands
- Phase 6: Research Brainstorm Mode (`--mode brainstorm`)
- Phase 7: Rollback (`minilegion rollback "<reason>"`)
- Phase 8: Doctor (`minilegion doctor`)

## Out of Scope (Carried Forward)

- GUI/Web interface
- IDE integration
- Automatic terminal command execution by LLM
- Voice workflow

## Archive

<details>
<summary>v1.0 planning baseline (archived)</summary>

- Roadmap archive: `milestones/v1.0-ROADMAP.md`
- Requirements archive: `milestones/v1.0-REQUIREMENTS.md`
- Milestone summary: `MILESTONES.md`

</details>

---
*Last updated: 2026-03-11 after v1.1 milestone roadmap creation*
