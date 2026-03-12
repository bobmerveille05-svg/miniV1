# Milestones

## 🚧 v1.1 Portable Kernel (In Progress — started 2026-03-11)

**Goal:** User can open any old project, run `minilegion status` then `minilegion context claude`, and resume in <2 min.

**Phases:** 2–8 (7 phases, ~10 plans)

**Slices:** context+adapters, history extraction, evidence bundles, validate+advance, research brainstorm, rollback, doctor

**ADR:** `.planning/milestones/v1.1-ADR-0007.md`

---

## v1.0 MVP (Shipped: 2026-03-10)

**Phases completed:** 12 phases, 23 plans, 2 tasks

**Key accomplishments:**
- Shipped full 8-stage CLI pipeline with strict transition enforcement and human approvals.
- Implemented schema-first execution with retry/fixup loop and RAW_DEBUG capture.
- Delivered execute/review/archive stages with scope lock, revise loop, and coherence checks.
- Added fast-mode planning (`--fast` / `--skip-research-design`) with downstream preflight support.
- Added multi-provider adapter layer (OpenAI, Anthropic, Gemini, Ollama, OpenAI-compatible).
- Added interactive configuration UX (`minilegion config init`, `minilegion config model`) and aligned product README.

**Known gaps accepted at close:**
- Milestone audit file not present at completion (`.planning/v1.0-MILESTONE-AUDIT.md`).

---
