# MiniLegion

## What This Is

MiniLegion is a file-centric, multi-provider, LLM-assisted protocol for software delivery. It runs a strict pipeline (`brief -> research -> design -> plan -> execute -> review -> archive`) with schema validation, approval gates, and deterministic archival.

## Core Value

A complete, validated path from brief to committed code that stays auditable and safe under human control.

## Current State

- **Shipped version:** v1.0 MVP (2026-03-10)
- **Milestone status:** Complete and archived
- **Coverage:** 12 phases completed, 23 plans completed, all v1 requirements checked
- **Production capabilities delivered:**
  - Full 8-stage pipeline with enforced transitions
  - 5 approval gates + immutable rejection behavior
  - Schema validation + bounded retry + debug capture
  - Scope lock + coherence checks + deterministic archive
  - Fast mode (`--fast`, `--skip-research-design`)
  - Multi-provider adapters (OpenAI, Anthropic, Gemini, Ollama, OpenAI-compatible)
  - Interactive provider/model configuration (`minilegion config init`, `minilegion config model`)

## Next Milestone Goals

- Define v1.1 outcomes from real user adoption and feedback loops
- Add milestone audit discipline before closure (to avoid unverified completion)
- Prioritize highest-leverage DX and reliability improvements from first external usage

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
*Last updated: 2026-03-10 after v1.0 milestone completion*
