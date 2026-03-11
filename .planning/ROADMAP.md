# Roadmap: MiniLegion

## Milestones

- ✅ **v1.0 MVP** — Phases 1–12 (shipped 2026-03-10) ([archived roadmap](milestones/v1.0-ROADMAP.md), [archived requirements](milestones/v1.0-REQUIREMENTS.md))
- ✅ **v1.1 pre-work** — Phase 1 (shipped 2026-03-11)
- 🚧 **v1.1 Portable Kernel** — Phases 2–17 (in progress)

---

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–12) — SHIPPED 2026-03-10</summary>

12 phases, 23 plans, all requirements shipped. See [archived roadmap](milestones/v1.0-ROADMAP.md) for full detail.

</details>

<details>
<summary>✅ Phase 1: Config Hardening + Provider Healthcheck — COMPLETE 2026-03-11</summary>

### Phase 1: Action immediate — harden config

**Goal:** Harden configuration and pre-research runtime safety so provider/model setup is explicit, validated, and fail-fast before any research-stage LLM work.
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06
**Depends on:** (v1.0 complete)
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md - Extend config schema and config CLI for small model, tool permissions, recommended vs all models, and aliases
- [x] 01-02-PLAN.md - Add provider healthcheck gate and deterministic context compaction in research orchestration

**Status:** COMPLETE — verified 7/7 must-haves, 620 tests passing. Closed 2026-03-11.

</details>

---

### 🚧 v1.1 Portable Kernel (In Progress)

**Milestone Goal:** Transform miniV1 from a solid LLM-orchestrated pipeline CLI into a portable, auditable, resumable kernel. After this milestone, a user can open any old project, run `minilegion status` then `minilegion context claude`, and resume work in under 2 minutes without re-reading the repo or knowing which model was used before.

---

### Phase 2: Context + Adapters

**Goal:** Users can assemble a complete, portable context block for any AI tool with one command, enabling instant resumption in Claude, ChatGPT, Copilot, or OpenCode.
**Depends on:** Phase 1
**Requirements:** CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CFG-08, CFG-09
**Success Criteria** (what must be TRUE):
  1. `minilegion context claude` writes `project-ai/context/claude.md` and prints a usable context block to stdout in one command
  2. `minilegion context chatgpt`, `minilegion context copilot`, `minilegion context opencode` each produce tool-specific context blocks with correct adapter framing
  3. The context block contains: current STATE, previous artifact summary, current stage template, memory digest (decisions/glossary/constraints), and chosen adapter instructions
  4. `project-ai/adapters/` contains `_base.md`, `claude.md`, `chatgpt.md`, `copilot.md`, `opencode.md`
  5. ADR-0007 file exists at `.planning/milestones/v1.1-ADR-0007.md` with all required fields
**Plans:** 2/2 plans complete

Plans:
- [ ] 02-01-PLAN.md — Implement `minilegion context <tool>` command, context assembler, ContextConfig sub-model
- [ ] 02-02-PLAN.md — Create adapter files, stage templates, memory scaffolding, wire into `minilegion init`

---

### Phase 3: History Extraction

**Goal:** STATE.json is clean current-state-only; all pipeline events are preserved as an append-only, human-readable chronological log in `project-ai/history/`.
**Depends on:** Phase 2
**Requirements:** HST-01, HST-02, HST-03, HST-04, HST-05
**Success Criteria** (what must be TRUE):
  1. `minilegion history` prints a readable chronological timeline of pipeline events for the current project
  2. `STATE.json` contains no `history` field; opening an old project with embedded history auto-migrates non-destructively on first access
  3. `project-ai/history/` contains sequentially numbered JSON event files (e.g., `001_init.json`) after any pipeline operation
  4. `core/history.py` exposes `append_event()` and `read_history()` callable by all pipeline commands
**Plans:** TBD

Plans:
- [ ] 03-01: Implement `core/history.py`, history/ write path, and migration logic for old STATE.json
- [ ] 03-02: Implement `minilegion history` command and wire all pipeline stages to emit events

---

### Phase 4: Evidence Bundles

**Goal:** Every validation step produces a machine-readable evidence file, creating an auditable trail that downstream commands can query without re-running validation.
**Depends on:** Phase 3
**Requirements:** EVD-01, EVD-02, EVD-03
**Success Criteria** (what must be TRUE):
  1. After `minilegion validate brief`, `project-ai/evidence/brief.validation.json` exists with fields: step, status, checks_passed, validator, tool_used, date, notes
  2. Every validate invocation for any stage creates/overwrites its evidence file
  3. Evidence files are valid JSON readable by `advance` and `doctor` without re-running validation
**Plans:** TBD

Plans:
- [ ] 04-01: Implement evidence/ directory, evidence file schema, and write path in validate command

---

### Phase 5: Validate + Advance as Distinct Commands

**Goal:** Artifact creation and state advancement are decoupled — users can edit artifacts then validate, and `advance` enforces that validation passed before changing stage.
**Depends on:** Phase 4
**Requirements:** VAD-01, VAD-02, VAD-03, VAD-04, CFG-07
**Success Criteria** (what must be TRUE):
  1. Running `minilegion brief`, `minilegion research`, etc. creates/updates the artifact but does NOT change STATE.json stage
  2. `minilegion validate <step>` runs checks, writes evidence, and reports pass/fail — stage unchanged
  3. `minilegion advance` succeeds and changes stage only when the current step's evidence file shows a passing validation
  4. `minilegion advance` exits non-zero with a clear "validation required" message when no passing evidence exists
  5. `workflow.strict_mode` and `workflow.require_validation` config fields are accepted (optional, non-breaking)
**Plans:** TBD

Plans:
- [ ] 05-01: Decouple state advancement from stage-producing commands; implement `minilegion validate <step>`
- [ ] 05-02: Implement `minilegion advance` with evidence gate, history event write, and config fields

---

### Phase 6: Research Brainstorm Mode

**Goal:** `minilegion research` supports exploration mode that produces structured candidate directions with a clear recommendation, enabling better design decisions when the problem space is open-ended.
**Depends on:** Phase 2
**Requirements:** RSM-01, RSM-02, RSM-03, RSM-04
**Success Criteria** (what must be TRUE):
  1. `minilegion research` (no flags) behaves identically to before — no regression
  2. `minilegion research --mode brainstorm --options 3` produces RESEARCH.json with fields: problem_framing, facts, assumptions, candidate_directions (≤3 entries), tradeoffs, risks, recommendation, open_questions
  3. The `recommendation` field is always present and non-empty in brainstorm mode output
  4. Config accepts `research.default_mode`, `research.default_options`, `research.min_options`, `research.max_options`, `research.require_recommendation` — omitting them leaves existing behavior unchanged
**Plans:** TBD

Plans:
- [ ] 06-01: Add `--mode` and `--options` flags, brainstorm schema, and prompt variant for brainstorm mode

---

### Phase 7: Rollback

**Goal:** Users can safely reset a project to its previous stage with a reason, leaving a complete audit trail and preserving rejected artifacts.
**Depends on:** Phase 5
**Requirements:** RBK-01, RBK-02
**Success Criteria** (what must be TRUE):
  1. `minilegion rollback "design rejected"` resets STATE.json to the correct previous stage without deleting the current artifact (artifact is marked rejected)
  2. A rollback event appears in `history/` with the provided reason, timestamp, previous stage, and reset-to stage
  3. The rejected artifact remains readable at its original path (or as a `*.rejected.json` sibling)
**Plans:** TBD

Plans:
- [ ] 07-01: Implement `minilegion rollback "<reason>"` with artifact preservation, stage reset, and history event

---

### Phase 8: Doctor

**Goal:** Users can instantly verify project health with one command, getting green/yellow/red status on all critical coherence checks.
**Depends on:** Phases 3, 4, 5, 7
**Requirements:** DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):
  1. `minilegion doctor` runs and outputs a per-check status table (green/yellow/red) plus a summary conclusion (pass/warn/fail)
  2. Doctor detects at least 4 classes of incoherence: invalid STATE.json, missing current-stage artifact, missing/corrupt history/, stage-artifact mismatch, missing adapter definition
  3. Running `minilegion doctor` on a healthy project produces all-green output with pass conclusion
  4. Running `minilegion doctor` on a broken project (e.g., deleted DESIGN.json while stage=design) produces at least one red check and a fail conclusion
**Plans:** TBD

Plans:
- [ ] 08-01: Implement `minilegion doctor` with all coherence checks, per-check reporting, and summary verdict

---

### Phase 13: Context Evidence + Verification Backfill

**Goal:** Re-establish auditable proof for context adapter outcomes and close the context completeness gap surfaced by milestone audit.
**Depends on:** Phase 8
**Requirements:** CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CFG-08, CFG-09
**Gap Closure:** Closes orphaned Phase 2 requirement evidence and the status->context flow gap from v1.1 audit.
**Plans:** 2/2 plans complete

Plans:
- [ ] 13-01-PLAN.md — Wire deterministic compact-plan lookahead into context assembly and test CTX-01/CFG-08 behavior
- [ ] 13-02-PLAN.md — Backfill Phase 2 requirement-ID verification artifact and context default docs for audit traceability

---

### Phase 14: History Foundation + Migration

**Goal:** Implement the history subsystem and migration path so state remains current-only while all events are append-only and queryable.
**Depends on:** Phase 13
**Requirements:** HST-01, HST-02, HST-03, HST-04, HST-05
**Gap Closure:** Closes history extraction integration and E2E flow gaps from v1.1 audit.
**Plans:** TBD

Plans:
- [ ] 14-01: Implement `core/history.py` append/read APIs and history/ storage contract
- [ ] 14-02: Add old STATE history migration and `minilegion history` CLI output

---

### Phase 15: Evidence Pipeline + Validate/Advance Gates

**Goal:** Separate artifact generation from progression, enforce validation gates with machine-readable evidence, and restore workflow strictness controls.
**Depends on:** Phase 14
**Requirements:** EVD-01, EVD-02, EVD-03, VAD-01, VAD-02, VAD-03, VAD-04, CFG-07
**Gap Closure:** Closes evidence/advance integration and validate->advance flow gaps from v1.1 audit.
**Plans:** TBD

Plans:
- [ ] 15-01: Add `validate <step>` command and evidence bundle writes
- [ ] 15-02: Add `advance` command with hard pass/fail gate and strict workflow config support

---

### Phase 16: Research Brainstorm Mode

**Goal:** Add brainstorm exploration mode with bounded options, schema-validated recommendation output, and non-breaking config defaults.
**Depends on:** Phase 15
**Requirements:** RSM-01, RSM-02, RSM-03, RSM-04
**Gap Closure:** Closes brainstorm integration and E2E flow gaps from v1.1 audit.
**Plans:** TBD

Plans:
- [ ] 16-01: Add `research --mode` and `--options` plus schema/prompt wiring for brainstorm mode

---

### Phase 17: Rollback + Doctor Health Surface

**Goal:** Restore operational safety with rollback semantics and expose project health via a user-facing doctor command.
**Depends on:** Phase 16
**Requirements:** RBK-01, RBK-02, DOC-01, DOC-02, DOC-03
**Gap Closure:** Closes rollback/doctor integration and E2E flow gaps from v1.1 audit.
**Plans:** TBD

Plans:
- [ ] 17-01: Implement rollback command with artifact preservation and history events
- [ ] 17-02: Implement doctor command with coherence checks and green/yellow/red output

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Config Hardening | v1.1 pre-work | 2/2 | Complete | 2026-03-11 |
| 2. Context + Adapters | 2/2 | Complete   | 2026-03-11 | - |
| 3. History Extraction | v1.1 | 0/2 | Not started | - |
| 4. Evidence Bundles | v1.1 | 0/1 | Not started | - |
| 5. Validate + Advance | v1.1 | 0/2 | Not started | - |
| 6. Research Brainstorm | v1.1 | 0/1 | Not started | - |
| 7. Rollback | v1.1 | 0/1 | Not started | - |
| 8. Doctor | v1.1 | 0/1 | Not started | - |
| 13. Context Evidence + Verification Backfill | 2/2 | Complete    | 2026-03-11 | - |
| 14. History Foundation + Migration | v1.1 gap closure | 0/2 | Not started | - |
| 15. Evidence Pipeline + Validate/Advance Gates | v1.1 gap closure | 0/2 | Not started | - |
| 16. Research Brainstorm Mode | v1.1 gap closure | 0/1 | Not started | - |
| 17. Rollback + Doctor Health Surface | v1.1 gap closure | 0/2 | Not started | - |
