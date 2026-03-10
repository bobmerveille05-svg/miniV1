# Roadmap: MiniLegion

## Overview

MiniLegion delivers a file-centric, LLM-assisted work protocol where every task flows through a structured pipeline (brief → research → design → plan → execute → review → archive) with human approval gates. The build order follows dependency chains: foundation and state first, then schemas and validation (safety before LLM calls), then the adapter layer, then guardrails and approval gates, then prompts for all roles, and finally the pipeline stages in sequence — culminating in the archivist, coherence checks, and fast mode that require the full pipeline to exist.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & CLI** - State machine, config, exceptions, atomic I/O, and CLI skeleton with 8 commands (completed 2026-03-10)
- [ ] **Phase 2: Schemas & Validation** - Pydantic models for all 6 artifacts, JSON schema generation, and retry logic
- [ ] **Phase 3: LLM Adapter** - Abstract base class and OpenAI concrete adapter with structured output support
- [ ] **Phase 4: Guardrails & Approval Gates** - Pre-flight checks, scope lock, path normalization, and 5 human approval gates
- [ ] **Phase 5: Prompts & Dual Output** - Role prompt templates for all 5 LLM roles and programmatic Markdown generation
- [ ] **Phase 6: Brief & Research Stage** - Brief creation, deep context codebase scanner, and Researcher pipeline stage
- [ ] **Phase 7: Design Stage** - Designer role producing architecture decisions with rejected alternatives
- [ ] **Phase 8: Plan Stage** - Planner role producing task decomposition constrained by design
- [ ] **Phase 9: Execute Stage** - Builder role producing structured patches with approval and dry-run support
- [ ] **Phase 10: Review & Revise** - Reviewer role with design/convention checks and bounded revise loop
- [ ] **Phase 11: Archivist & Coherence** - Deterministic archival and inter-phase coherence validation across all stages
- [ ] **Phase 12: Fast Mode** - Abbreviated pipeline with --fast and --skip-research-design flags

## Phase Details

### Phase 1: Foundation & CLI
**Goal**: User can run `minilegion` commands against a project with reliable state management, configuration, and error handling
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion init myproject` and see a `project-ai/` directory created with template files
  2. User can run any of the 8 CLI commands and see appropriate routing (or "not yet implemented" stubs)
  3. State machine enforces valid transitions — running `design` from `init` state is rejected with a clear error
  4. Config file is loaded and parsed — user can set LLM provider, model, and per-role engine assignment
  5. All file writes use atomic pattern — interrupted writes never corrupt existing files
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Core infrastructure: package scaffold, exceptions, atomic file I/O, config model, state machine + unit tests
- [ ] 01-02-PLAN.md — CLI layer: 8 Typer commands (init, brief, research, design, plan, execute, review, status) + integration tests

### Phase 2: Schemas & Validation
**Goal**: All 6 machine-readable artifact types have enforced schemas with automatic validation and retry on failure
**Depends on**: Phase 1
**Requirements**: SCHM-01, SCHM-02, SCHM-03, SCHM-04, SCHM-05
**Success Criteria** (what must be TRUE):
  1. Pydantic models exist for all 6 artifact types (research, design, plan, execution_log, review, state) and reject invalid data with clear errors
  2. JSON Schema files are generated from Pydantic models and are valid JSON Schema documents
  3. Invalid LLM output triggers retry with error feedback — after 2 retries, raw output is saved to `*_RAW_DEBUG.txt`
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Pydantic models for all 6 artifacts, schema registry, JSON Schema generation
- [ ] 02-02-PLAN.md — Pre-parse fixup pipeline, retry logic with error feedback, RAW_DEBUG capture

### Phase 3: LLM Adapter
**Goal**: LLM calls can be made through a provider-agnostic interface with the OpenAI adapter as the concrete implementation
**Depends on**: Phase 2
**Requirements**: ADPT-01, ADPT-02, ADPT-03, ADPT-04
**Success Criteria** (what must be TRUE):
  1. Abstract base class defines a clear contract — a new adapter can be written by implementing 1 class without modifying any other code
  2. OpenAI adapter sends prompts and receives structured JSON responses validated against schemas from Phase 2
  3. Adapter reads API key from environment variable specified in config — missing key produces a clear error before any API call
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Guardrails & Approval Gates
**Goal**: No LLM call can execute without passing pre-flight checks, and no state mutation occurs without human approval
**Depends on**: Phase 1, Phase 2
**Requirements**: GUARD-01, GUARD-02, GUARD-03, GUARD-04, GUARD-05, APRV-01, APRV-02, APRV-03, APRV-04, APRV-05, APRV-06
**Success Criteria** (what must be TRUE):
  1. Running `design` without `RESEARCH.json` present produces a pre-flight failure with a message naming the missing file
  2. Running `design` without `research_approved` in STATE.json produces a pre-flight failure naming the missing approval
  3. User sees a summary and Y/N prompt at each approval gate — rejecting leaves STATE.json byte-identical to before
  4. Scope lock catches when a patch touches a file not in `files_allowed` — paths are normalized before comparison
  5. All 5 approval gates (brief, research, design, plan, patch) are functional and block state transitions on rejection
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Prompts & Dual Output
**Goal**: Every LLM role has a tested prompt template and every artifact is saved in both JSON and Markdown formats
**Depends on**: Phase 2, Phase 3
**Requirements**: PRMT-01, PRMT-02, PRMT-03, PRMT-04, DUAL-01, DUAL-02
**Success Criteria** (what must be TRUE):
  1. Five prompt files exist in `prompts/` directory (researcher, designer, planner, builder, reviewer) each with SYSTEM and USER_TEMPLATE sections
  2. All prompts enforce JSON-only output with anchoring instructions at start and end of the prompt
  3. `{{placeholder}}` variables in USER_TEMPLATE are replaced with actual context data at call time
  4. Every LLM-produced artifact is saved as both `.json` and `.md` — the Markdown is generated programmatically from parsed JSON, not by the LLM
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: Brief & Research Stage
**Goal**: User can create a brief and run the full research stage to produce verified codebase context
**Depends on**: Phase 3, Phase 4, Phase 5
**Requirements**: BRIEF-01, BRIEF-02, BRIEF-03, RSCH-01, RSCH-02, RSCH-03, RSCH-04, RSCH-05, RSCH-06, RSCH-07
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion brief "build a login page"` and see BRIEF.md created, then approve it via Y/N prompt
  2. Deep context scanner detects tech stack, extracts imports, and identifies naming conventions from a real codebase
  3. User can run `minilegion research` and see RESEARCH.json + RESEARCH.md produced with project_overview, tech_stack, relevant_files, and all required fields
  4. Researcher prompt enforces "explore, don't design" — output contains no solution proposals
  5. Deep context respects configurable limits (max depth, max file count, max file size)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

### Phase 7: Design Stage
**Goal**: User can run the design stage to produce architecture decisions grounded in research findings
**Depends on**: Phase 6
**Requirements**: DSGN-01, DSGN-02, DSGN-03, DSGN-04, DSGN-05
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion design` and see DESIGN.json + DESIGN.md produced with components, architecture_decisions, and all required fields
  2. Every architecture decision includes at least 1 rejected alternative — schema validation enforces this
  3. conventions_to_follow references conventions discovered in RESEARCH.json
  4. Designer prompt enforces "design, don't plan" — output contains no task decomposition
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Plan Stage
**Goal**: User can run the plan stage to produce a task decomposition constrained by the approved design
**Depends on**: Phase 7
**Requirements**: PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion plan` and see PLAN.json + PLAN.md produced with tasks, touched_files, and all required fields
  2. Every task references a component from DESIGN.json — orphaned tasks are rejected
  3. touched_files is a subset of files declared in DESIGN.json components — extra files are rejected
  4. Planner prompt enforces "decompose, don't design" — design decisions are treated as settled
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Execute Stage
**Goal**: User can run the execute stage to produce code patches that are individually approved before application
**Depends on**: Phase 8
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion execute` and see EXECUTION_LOG.json produced with per-task patches
  2. Each patch is displayed to the user with a diff view — user approves or rejects each one individually
  3. Approved patches are applied to the filesystem by the patcher module
  4. User can run `minilegion execute --dry-run` and see what would change without any files being modified
  5. `--task N` flag allows executing a single task instead of the full plan
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

### Phase 10: Review & Revise
**Goal**: User can run the review stage to verify execution against design and conventions, with automatic revise loop on failure
**Depends on**: Phase 9
**Requirements**: REVW-01, REVW-02, REVW-03, REVW-04, REVW-05, REVS-01, REVS-02, REVS-03, REVS-04
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion review` and see REVIEW.json + REVIEW.md with bugs, scope_deviations, design_conformity, convention_violations, and verdict
  2. When verdict = "revise", pipeline automatically re-enters execute with corrective_actions — no manual intervention needed
  3. Revise loop stops after 2 iterations and escalates to human with full context display
  4. If design_conformity.conforms = false, user is offered the option to re-design before re-executing
  5. Reviewer prompt enforces "identify, don't correct" — no fixes are proposed, only issues flagged
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD
- [ ] 10-03: TBD

### Phase 11: Archivist & Coherence
**Goal**: Pipeline completion is archived deterministically and cross-phase coherence is validated at every stage boundary
**Depends on**: Phase 6, Phase 7, Phase 8, Phase 9, Phase 10
**Requirements**: ARCH-01, ARCH-02, ARCH-03, COHR-01, COHR-02, COHR-03, COHR-04, COHR-05
**Success Criteria** (what must be TRUE):
  1. After review passes, STATE.json is updated with completed tasks, final verdict, and history entry — with zero LLM calls
  2. DECISIONS.md is updated with architecture decisions made during the cycle
  3. Research→Design coherence check verifies recommended_focus_files were read by Designer
  4. Design→Plan coherence check verifies every component has at least 1 task
  5. Plan→Execute and Design→Review coherence checks catch scope drift between pipeline stages
**Plans**: TBD

Plans:
- [ ] 11-01: TBD
- [ ] 11-02: TBD
- [ ] 11-03: TBD

### Phase 12: Fast Mode
**Goal**: Experienced users can skip research and design stages for quick iterations with degraded but functional context
**Depends on**: Phase 6, Phase 7, Phase 8 (requires full pipeline to selectively skip parts)
**Requirements**: FAST-01, FAST-02, FAST-03
**Success Criteria** (what must be TRUE):
  1. User can run `minilegion plan --fast` and get a plan based on tree + brief alone when RESEARCH.json/DESIGN.json don't exist
  2. User can run `minilegion plan --skip-research-design` to explicitly bypass research and design stages
  3. Skipped stages are recorded in STATE.json — downstream commands work without requiring skipped artifacts
**Plans**: TBD

Plans:
- [ ] 12-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & CLI | 0/2 | Complete    | 2026-03-10 |
| 2. Schemas & Validation | 0/2 | Not started | - |
| 3. LLM Adapter | 0/2 | Not started | - |
| 4. Guardrails & Approval Gates | 0/3 | Not started | - |
| 5. Prompts & Dual Output | 0/2 | Not started | - |
| 6. Brief & Research Stage | 0/3 | Not started | - |
| 7. Design Stage | 0/2 | Not started | - |
| 8. Plan Stage | 0/2 | Not started | - |
| 9. Execute Stage | 0/2 | Not started | - |
| 10. Review & Revise | 0/3 | Not started | - |
| 11. Archivist & Coherence | 0/3 | Not started | - |
| 12. Fast Mode | 0/1 | Not started | - |
