# MiniLegion

## What This Is

MiniLegion is a file-centric, multi-engine, LLM-assisted work protocol written in Python. It implements a spec-driven, portable workflow where every task goes through a structured pipeline: brief → research → design → plan → execute → review → archive. Each stage produces both human-readable Markdown and machine-parseable JSON artifacts with mandatory human approval gates, making execution verifiable, safe, and runtime-independent.

## Core Value

A complete, validated pipeline from brief to committed code that proves AI-assisted workflows can be rigorous, safe, and portable — "Prove the workflow."

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **CLI entrypoint** (`run.py`) with 8 commands: init, brief, research, design, plan, execute, review, status
- [ ] **6 roles** with distinct responsibilities: Researcher, Designer, Planner, Builder, Reviewer, Archivist
- [ ] **Researcher** explores codebase, produces `RESEARCH.md` + `RESEARCH.json` with deep scan
- [ ] **Designer** produces architecture decisions in `DESIGN.md` + `DESIGN.json`
- [ ] **Planner** produces `PLAN.md` + `PLAN.json` constrained by design
- [ ] **Builder** produces structured JSON patches in `EXECUTION_LOG.json`
- [ ] **Reviewer** verifies design conformity and convention compliance, produces `REVIEW.md` + `REVIEW.json`
- [ ] **Archivist** is deterministic (no LLM) — updates `STATE.json` and `DECISIONS.md`
- [ ] **Dual output format**: every stage produces both `.md` (human) and `.json` (machine)
- [ ] **JSON Schemas** for all 6 machine-readable artifacts (research, design, plan, execution_log, review, state)
- [ ] **Pre-flight checks** validate required files and approvals before each LLM call
- [ ] **Human approval gates** at 5 points: brief, research, design, plan, patch
- [ ] **Scope lock**: `changed_files` mechanically checked against `files_allowed`
- [ ] **Retry logic** for invalid JSON (max 2 retries)
- [ ] **Revise loop** bounded at max 2 iterations with human escalation
- [ ] **State invariant**: state unchanged if output not approved
- [ ] **Deep context module** (`core/deep_context.py`) for codebase scanning
- [ ] **Inter-phase coherence checks** (research↔design, design↔plan, design↔review)
- [ ] **Fast mode** (`--fast`, `--skip-research-design`) for abbreviated pipeline
- [ ] **Dry-run** support for execute command
- [ ] **OpenAI adapter** (MVP) with abstract base for future adapters
- [ ] **Config file** (`minilegion.config.json`) with per-role engine assignment and timeouts
- [ ] **`NO_ADD.md`** — Sprint 1 non-addition contract enforced by team

### Out of Scope

- `doctor` command — deferred to MVP+
- `git commit auto` — suggested only, not automatic (D11)
- `session log` — deferred to MVP+
- `context manifest` — deferred to MVP+
- Multi-LLM simultaneous calls — Sprint 2+
- `reset` command — not in Sprint 1
- Observe mode for review — not in Sprint 1
- Separate `SCOPE_LOCK.json` — state-embedded
- Context digest auto — not in Sprint 1
- Dual MD+JSON in single LLM call — not in Sprint 1
- Advanced milestones/phases — Sprint 3+
- Model profiles per step — Sprint 3+
- Parallel multi-builder — Sprint 3+
- Web/GUI interface — not planned
- Framework unit tests — not in Sprint 1
- Rich/TUI interface — not in Sprint 1
- Complex `config.yaml` — config.json is sufficient
- External web search auto — not in Sprint 1
- IDE integration — not planned

## Context

- **Language**: Python (sole language for MVP)
- **License**: MIT
- **LLM Adapter (MVP)**: OpenAI / GPT-4o via `OPENAI_API_KEY`
- **4-layer architecture**: Protocol (prompts) → Orchestrator (CLI + state + guardrails) → LLM Adapters → Local repo
- **File-centric memory**: All state lives in `project-ai/` directory as files, no database
- **Pipeline philosophy**: Each role has a single concern; roles cannot skip ahead; state is only written on approval
- **Benchmark target**: Beat GSD on ≥ 4/7 dimensions at 30 days (D14)
- **Abandon criteria**: 3 explicit conditions (X1-X3) to prevent sunk-cost continuation
- **Version**: v1.1 — adds Research + Design phases to the v1.0 plan→execute→review core

## Constraints

- **Tech stack**: Python only — no JS, no compiled dependencies
- **Runtime portability**: Must work with any LLM adapter (base.py contract), not just OpenAI
- **Scope lock**: Builder cannot touch files not listed in `touched_files` — mechanical enforcement
- **State safety**: `STATE.json` only transitions on human approval — no auto-mutations
- **Sprint 1 scope**: 24 elements defined; `NO_ADD.md` contract prevents additions
- **LLM output**: All LLM responses must be pure JSON — no markdown wrappers, validated against schema
- **Retry bound**: Max 2 retries on JSON parse failure, then fail with debug output
- **Revise bound**: Max 2 revise iterations, then escalate to human

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 6 roles (not 4) | Separating Research and Design from Planning prevents plans based on false assumptions | — Pending |
| Extended pipeline (brief→research→design→plan→execute→review→archive) | Ensures every plan is grounded in verified context and explicit architecture decisions | — Pending |
| Dual output MD+JSON | Markdown for human review, JSON for mechanical validation and downstream consumption | — Pending |
| Deterministic Archivist (no LLM) | Archiving is a state transition — it must be reliable, not probabilistic | — Pending |
| Mechanical scope lock | Textual scope checks fail; file-list comparison is unambiguous | — Pending |
| Bounded revise loop (max 2) | Prevents infinite loops; escalates to human when LLM cannot self-correct | — Pending |
| State immutability on non-approval | Prevents partial-state corruption; approval is the atomic commit point | — Pending |
| Fast mode (`--skip-research-design`) | Allows experienced users to skip to plan with degraded but usable context | — Pending |
| OpenAI adapter first | Fastest path to working MVP; adapter pattern ensures portability later | — Pending |
| `NO_ADD.md` contract | Formal scope lock for the team — prevents feature creep during Sprint 1 | — Pending |

---
*Last updated: 2026-03-09 after initialization*
