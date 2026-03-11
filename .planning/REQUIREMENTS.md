# Requirements: MiniLegion v1.1 — Portable Kernel

**Defined:** 2026-03-11
**Core Value:** A user can open any old project, run `minilegion status` then `minilegion context claude`, and resume work in under 2 minutes without re-reading the repo or knowing which model was used before.

---

## v1.1 Requirements

All requirements below are v1.1 scope (in-milestone). Previous v1.0 requirements are archived in `.planning/milestones/v1.0-REQUIREMENTS.md`.

---

### Context + Adapters (Slice 1)

- **CTX-01**: `minilegion context <tool>` command assembles a portable context block (STATE.json current state, previous artifact, current stage template, useful memory, compact plan, chosen adapter) and writes it to `project-ai/context/<tool>.md`
- **CTX-02**: `minilegion context <tool>` prints the assembled context block to stdout so it can be pasted directly into any AI tool
- **CTX-03**: Adapter definition files exist for `claude`, `chatgpt`, `copilot`, and `opencode` in `project-ai/adapters/` (base + per-tool markdown)
- **CTX-04**: Formal per-stage prompt templates live in `project-ai/templates/` (one template per pipeline stage)
- **CTX-05**: Memory files (`decisions.md`, `glossary.md`, `constraints.md`) are created in `project-ai/memory/` and injected into the context block
- **CTX-06**: ADR-0007 "Evolve miniV1 toward a portable kernel" is saved to `.planning/milestones/v1.1-ADR-0007.md` with full fields (status, context, decision, consequences, rejected alternatives, success criterion)

---

### History Extraction (Slice 2)

- **HST-01**: `project-ai/history/` is created as an append-only event log directory; each event is a sequentially numbered JSON file (e.g., `001_init.json`, `002_validate_brief.json`) with fields: event_type, stage, timestamp, actor, tool_used, notes
- **HST-02**: `STATE.json` no longer contains an embedded history field; it holds current state only
- **HST-03**: `core/history.py` helper provides `append_event(event)` and `read_history()` functions
- **HST-04**: `minilegion history` command reads `history/` and prints a chronological timeline of recent events
- **HST-05**: On first access of an old STATE.json containing a history field, the tool non-destructively migrates: writes new history/ files from embedded history, then strips the history field from STATE.json (original data preserved in history/ files)

---

### Evidence Bundles (Slice 3)

- **EVD-01**: `project-ai/evidence/` directory is created; each `validate <step>` writes a structured evidence file (e.g., `brief.validation.json`) with fields: step, status, checks_passed, validator, tool_used, date, notes
- **EVD-02**: Every validate invocation creates or overwrites the corresponding evidence file for that step
- **EVD-03**: Evidence files are machine-readable JSON so that downstream commands (`advance`, `doctor`) can query validation status without re-running validation

---

### Validate + Advance as Distinct Commands (Slice 4)

- **VAD-01**: Stage-producing commands (`brief`, `research`, `design`, `plan`, `execute`, `review`) create/update artifacts without automatically advancing STATE.json stage
- **VAD-02**: `minilegion validate <step>` validates the artifact for the given step, writes an evidence file to `project-ai/evidence/`, and reports pass/fail without changing stage
- **VAD-03**: `minilegion advance` checks that the current step's evidence file shows a passing validation, then changes the stage in STATE.json and appends an event to `history/`
- **VAD-04**: `minilegion advance` refuses to advance (exits non-zero with clear message) if the current step has no passing evidence file

---

### Research Brainstorm Mode (Slice 5)

- **RSM-01**: `minilegion research --mode fact` (default, current behavior) runs the existing codebase scan and produces the current RESEARCH.json output unchanged
- **RSM-02**: `minilegion research --mode brainstorm --options N` (default N=3) produces a structured output with fields: problem_framing, facts, assumptions, candidate_directions (max N), tradeoffs, risks, recommendation, open_questions
- **RSM-03**: Brainstorm mode always includes exactly one `recommendation` field identifying the preferred direction; the output is validated against a schema
- **RSM-04**: Config schema accepts `research.default_mode` (default: "fact"), `research.default_options` (default: 3), `research.min_options` (default: 1), `research.max_options` (default: 5), `research.require_recommendation` (default: true) — all optional, non-breaking

---

### Rollback (Slice 6)

- **RBK-01**: `minilegion rollback "<reason>"` command resets STATE.json stage to the correct previous stage without silently deleting the current artifact (current artifact is marked as rejected in its metadata or a sibling `*.rejected.json` file)
- **RBK-02**: `minilegion rollback "<reason>"` appends a rollback event to `history/` with the reason, timestamp, previous stage, and reset-to stage

---

### Doctor (Slice 7)

- **DOC-01**: `minilegion doctor` command checks: STATE.json schema validity, stage coherence (stage matches artifacts present), current artifact present, history/ readable, and requested adapter present
- **DOC-02**: `minilegion doctor` detects at least 4 classes of incoherence: invalid STATE.json, missing current-stage artifact, missing or corrupt history/, stage-artifact mismatch (e.g., stage=design but no DESIGN.json), missing adapter definition
- **DOC-03**: `minilegion doctor` outputs a green/yellow/red status per check, with a summary pass/warn/fail conclusion

---

### Config Additions (Non-breaking)

- **CFG-07**: `minilegion.config.json` schema accepts `workflow.strict_mode` (bool, default: true) and `workflow.require_validation` (bool, default: true) — optional, non-breaking, existing configs unaffected
- **CFG-08**: `minilegion.config.json` schema accepts `context.max_injection_tokens` (int, default: 3000), `context.lookahead_tasks` (int, default: 2), `context.warn_threshold` (float, default: 0.7) — optional, non-breaking
- **CFG-09**: All new config fields have documented defaults; omitting them in config produces identical behavior to the defaults

---

## v2 Requirements (Deferred)

- **DX-05**: Rich/TUI interface with progress indicators
- **ADV-01**: Parallel multi-builder execution
- **ADV-02**: Auto git commit on approval
- **MLLM-04**: Per-role engine enforcement (different models per pipeline stage)

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CTX-01 | Phase 13 | Complete |
| CTX-02 | Phase 13 | Complete |
| CTX-03 | Phase 13 | Complete |
| CTX-04 | Phase 13 | Complete |
| CTX-05 | Phase 13 | Complete |
| CTX-06 | Phase 13 | Complete |
| HST-01 | Phase 14 | Pending |
| HST-02 | Phase 14 | Pending |
| HST-03 | Phase 14 | Pending |
| HST-04 | Phase 14 | Pending |
| HST-05 | Phase 14 | Pending |
| EVD-01 | Phase 15 | Pending |
| EVD-02 | Phase 15 | Pending |
| EVD-03 | Phase 15 | Pending |
| VAD-01 | Phase 15 | Pending |
| VAD-02 | Phase 15 | Pending |
| VAD-03 | Phase 15 | Pending |
| VAD-04 | Phase 15 | Pending |
| RSM-01 | Phase 16 | Pending |
| RSM-02 | Phase 16 | Pending |
| RSM-03 | Phase 16 | Pending |
| RSM-04 | Phase 16 | Pending |
| RBK-01 | Phase 17 | Pending |
| RBK-02 | Phase 17 | Pending |
| DOC-01 | Phase 17 | Pending |
| DOC-02 | Phase 17 | Pending |
| DOC-03 | Phase 17 | Pending |
| CFG-07 | Phase 15 | Pending |
| CFG-08 | Phase 13 | Complete |
| CFG-09 | Phase 13 | Complete |

**Coverage:**
- v1.1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0
- Pending after audit replan: 30

---
*Requirements defined: 2026-03-11*
