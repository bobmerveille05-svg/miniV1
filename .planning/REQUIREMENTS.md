# Requirements: MiniLegion

**Defined:** 2026-03-09
**Core Value:** A complete, validated pipeline from brief to committed code that proves AI-assisted workflows can be rigorous, safe, and portable.

## v1 Requirements

Requirements for Sprint 1 (initial release). Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: User can run `minilegion init <name>` to create a project directory with all template files in `project-ai/`
- [x] **FOUND-02**: User can configure LLM provider, model, API key, timeouts, and per-role engine assignment via `minilegion.config.json`
- [x] **FOUND-03**: State machine manages transitions between 8 stages (init, brief, research, design, plan, execute, review, archive) with valid/invalid transition enforcement
- [x] **FOUND-04**: `STATE.json` is only written to disk after human approval — state is computed as Python objects first, written atomically via `os.replace()`
- [x] **FOUND-05**: All file I/O uses atomic write pattern (write to temp file, then `os.replace`) to prevent partial-failure corruption
- [x] **FOUND-06**: Custom exception hierarchy for distinct error categories (validation, LLM, state, preflight, approval)

### CLI

- [x] **CLI-01**: User can run 8 commands via `python run.py <command>`: init, brief, research, design, plan, execute, review, status
- [x] **CLI-02**: `plan` command accepts `--fast` and `--skip-research-design` flags
- [x] **CLI-03**: `execute` command accepts `--task N` and `--dry-run` flags
- [x] **CLI-04**: Running a command without arguments shows usage help
- [x] **CLI-05**: `status` command reads `STATE.json` and displays current stage, approvals, completed/pending tasks, and open risks

### LLM Adapter

- [x] **ADPT-01**: Abstract base class defines the LLM adapter contract (send prompt, receive response, structured output support)
- [x] **ADPT-02**: OpenAI adapter implements the base class using `openai` SDK with `response_format` for structured JSON output
- [x] **ADPT-03**: Adapter accepts system prompt + user message + max_tokens + timeout and returns raw content + token usage
- [x] **ADPT-04**: Adapter reads API key from environment variable specified in config

### Schemas & Validation

- [x] **SCHM-01**: Pydantic models define all 6 machine-readable artifact schemas (research, design, plan, execution_log, review, state)
- [x] **SCHM-02**: JSON Schema files generated from Pydantic models for external tool consumption
- [x] **SCHM-03**: LLM output is parsed and validated against schema immediately after each call
- [x] **SCHM-04**: Invalid JSON triggers retry with error feedback injected into next LLM call (max 2 retries)
- [x] **SCHM-05**: After max retries, raw LLM output is saved to `*_RAW_DEBUG.txt` for diagnosis

### Pre-flight & Guardrails

- [ ] **GUARD-01**: Pre-flight check validates required files exist before each LLM call (research needs BRIEF.md; design needs BRIEF.md + RESEARCH.json; etc.)
- [ ] **GUARD-02**: Pre-flight check validates required approvals in STATE.json before each LLM call (design needs brief_approved + research_approved; etc.)
- [ ] **GUARD-03**: In safe mode, `design` refuses to run without `RESEARCH.json`; `plan` refuses without `DESIGN.json`
- [ ] **GUARD-04**: Scope lock mechanically checks `changed_files` in EXECUTION_LOG.json against `files_allowed` from PLAN.json using normalized paths
- [ ] **GUARD-05**: Path normalization applied to all file paths before scope lock comparison (resolve `./`, trailing slashes, OS separators)

### Approval Gates

- [ ] **APRV-01**: CLI-based human approval gate after brief creation (approve_brief)
- [ ] **APRV-02**: CLI-based human approval gate after research with summary display (approve_research)
- [ ] **APRV-03**: CLI-based human approval gate after design with design display (approve_design)
- [ ] **APRV-04**: CLI-based human approval gate after plan with plan display (approve_plan)
- [ ] **APRV-05**: CLI-based human approval gate before each patch application with diff display (approve_patch)
- [ ] **APRV-06**: Rejection at any gate leaves STATE.json unchanged — no partial state mutation

### Brief

- [ ] **BRIEF-01**: User can run `minilegion brief "<text>"` to create BRIEF.md from free-text input
- [ ] **BRIEF-02**: If no text argument provided, user is prompted via stdin
- [ ] **BRIEF-03**: After BRIEF.md creation, approve_brief() is called before state transitions

### Researcher

- [ ] **RSCH-01**: Deep context module scans codebase: detects tech stack from config files (package.json, requirements.txt, etc.)
- [ ] **RSCH-02**: Deep context scans files up to configurable depth, max file count, and max file size
- [ ] **RSCH-03**: Deep context extracts imports/exports from Python, JS/TS, and Go source files
- [ ] **RSCH-04**: Deep context detects naming conventions, directory structure patterns, and test patterns
- [ ] **RSCH-05**: Researcher role receives scanned context + BRIEF.md and produces RESEARCH.json + RESEARCH.md
- [ ] **RSCH-06**: RESEARCH.json contains: project_overview, tech_stack, architecture_patterns, relevant_files, existing_conventions, dependencies_map, potential_impacts, constraints, assumptions_verified, open_questions, recommended_focus_files
- [ ] **RSCH-07**: Researcher prompt enforces "explore, don't design" — no solutions proposed

### Designer

- [ ] **DSGN-01**: Designer role receives BRIEF.md + RESEARCH.json + recommended focus files and produces DESIGN.json + DESIGN.md
- [ ] **DSGN-02**: DESIGN.json contains: design_approach, architecture_decisions (with alternatives_rejected), components (with files), data_models, api_contracts, integration_points, design_patterns_used, conventions_to_follow, technical_risks, out_of_scope, test_strategy, estimated_complexity
- [ ] **DSGN-03**: Each architecture decision must have at least 1 rejected alternative
- [ ] **DSGN-04**: conventions_to_follow must reference conventions from RESEARCH.json
- [ ] **DSGN-05**: Designer prompt enforces "design, don't plan" — no task decomposition

### Planner

- [ ] **PLAN-01**: Planner role receives DESIGN.json + RESEARCH.json + BRIEF.md and produces PLAN.json + PLAN.md
- [ ] **PLAN-02**: PLAN.json contains: objective, design_ref, assumptions, tasks (with id, name, description, files, depends_on, component), touched_files, risks, success_criteria, test_plan
- [ ] **PLAN-03**: Each task references a component from DESIGN.json
- [ ] **PLAN-04**: touched_files must be a subset of files declared in DESIGN.json components
- [ ] **PLAN-05**: Planner prompt enforces "decompose, don't design" — design decisions are already made

### Builder

- [ ] **BUILD-01**: Builder role receives PLAN.json + source files and produces EXECUTION_LOG.json with structured patches
- [ ] **BUILD-02**: EXECUTION_LOG.json contains per-task: task_id, changed_files (path, action, content), unchanged_files, tests_run, test_result, blockers, out_of_scope_needed
- [ ] **BUILD-03**: Each patch is displayed to user for approval before application
- [ ] **BUILD-04**: Patcher module applies approved patches to the filesystem
- [ ] **BUILD-05**: Dry-run mode shows what would change without modifying files

### Reviewer

- [ ] **REVW-01**: Reviewer role receives diff + PLAN.json + DESIGN.json + conventions and produces REVIEW.json + REVIEW.md
- [ ] **REVW-02**: REVIEW.json contains: bugs, scope_deviations, design_conformity (conforms + deviations), convention_violations, security_risks, performance_risks, tech_debt, out_of_scope_files, success_criteria_met, verdict (pass|revise), corrective_actions
- [ ] **REVW-03**: Reviewer checks design conformity — implementation matches DESIGN.json components and interfaces
- [ ] **REVW-04**: Reviewer checks convention compliance against conventions from RESEARCH.json
- [ ] **REVW-05**: Reviewer prompt enforces "identify, don't correct" — no fixes proposed

### Revise Loop

- [ ] **REVS-01**: When verdict = "revise", pipeline re-enters execute with corrective_actions from REVIEW.json
- [ ] **REVS-02**: Revise loop bounded at max 2 iterations
- [ ] **REVS-03**: After 2 failed revisions, escalate to human with full context display
- [ ] **REVS-04**: If design_conformity.conforms = false, offer to re-design before re-executing

### Archivist

- [ ] **ARCH-01**: Archivist is fully deterministic — no LLM calls
- [ ] **ARCH-02**: After review passes, Archivist updates STATE.json with completed tasks, final verdict, and history entry
- [ ] **ARCH-03**: Archivist updates DECISIONS.md with any architecture decisions made during the cycle

### Inter-phase Coherence

- [ ] **COHR-01**: Research→Design check: recommended_focus_files from RESEARCH.json were read by Designer
- [ ] **COHR-02**: Design→Plan check: every component in DESIGN.json has at least 1 task in PLAN.json
- [ ] **COHR-03**: Plan→Execute check: files in patches are subset of touched_files in PLAN.json
- [ ] **COHR-04**: Design→Review check: execution conforms to DESIGN.json components and interfaces
- [ ] **COHR-05**: Research conventions→Review check: code follows conventions from RESEARCH.json

### Prompts

- [ ] **PRMT-01**: 5 role prompts (researcher, designer, planner, builder, reviewer) each with SYSTEM and USER_TEMPLATE sections
- [ ] **PRMT-02**: All prompts enforce JSON-only output with anchoring instructions at start and end
- [ ] **PRMT-03**: Prompts stored as markdown files in `prompts/` directory
- [ ] **PRMT-04**: USER_TEMPLATE uses `{{placeholder}}` syntax for variable injection

### Dual Output

- [ ] **DUAL-01**: Every LLM-produced artifact is saved in both .json (machine) and .md (human) formats
- [ ] **DUAL-02**: Markdown is generated programmatically from parsed JSON — not by the LLM

### Fast Mode

- [ ] **FAST-01**: `--fast` flag allows plan command to work with basic context (tree + brief) when RESEARCH.json/DESIGN.json don't exist
- [ ] **FAST-02**: `--skip-research-design` explicitly skips research and design stages
- [ ] **FAST-03**: Skipped stages are recorded in STATE.json but don't block downstream commands

## v2 Requirements

Deferred to future sprints. Tracked but not in current roadmap.

### Multi-LLM

- **MLLM-01**: Codex adapter implementation
- **MLLM-02**: Claude adapter implementation
- **MLLM-03**: Gemini adapter implementation
- **MLLM-04**: Per-role engine enforcement (different models for different roles)

### Developer Experience

- **DX-01**: `doctor` command for environment validation
- **DX-02**: Session log with full pipeline history
- **DX-03**: Context manifest showing what was sent to LLM
- **DX-04**: `reset` command to clear state
- **DX-05**: Rich/TUI interface with progress indicators

### Testing

- **TEST-01**: Unit tests for state machine transitions
- **TEST-02**: Unit tests for scope lock enforcement
- **TEST-03**: Unit tests for JSON schema validation
- **TEST-04**: Integration tests for full pipeline

### Advanced

- **ADV-01**: Parallel multi-builder execution
- **ADV-02**: Auto git commit on approval
- **ADV-03**: Observe mode for review (read-only, no LLM)
- **ADV-04**: Context digest for large codebases

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI / Web interface | MiniLegion's value is in the protocol, not the UI. 3-6 month effort. |
| IDE integration | Massive engineering effort; CLI is IDE-agnostic |
| Browser / web browsing | Adds Playwright/Chrome dependency; tangential to "prove the workflow" |
| Terminal command execution | Security risks and sandbox complexity; Builder produces patches only |
| Voice input | Orthogonal to protocol rigor |
| MCP / tool extensibility | Requires protocol server infrastructure |
| Mobile app | CLI-first, terminal-based |
| Multi-file simultaneous LLM calls | Optimization, not correctness; sequential pipeline for Sprint 1 |
| Config YAML | JSON is sufficient; no added value from YAML complexity |
| External web search | Researcher works with codebase context only in Sprint 1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| FOUND-06 | Phase 1 | Complete |
| CLI-01 | Phase 1 | Complete |
| CLI-02 | Phase 1 | Complete |
| CLI-03 | Phase 1 | Complete |
| CLI-04 | Phase 1 | Complete |
| CLI-05 | Phase 1 | Complete |
| SCHM-01 | Phase 2 | Complete |
| SCHM-02 | Phase 2 | Complete |
| SCHM-03 | Phase 2 | Complete |
| SCHM-04 | Phase 2 | Complete |
| SCHM-05 | Phase 2 | Complete |
| ADPT-01 | Phase 3 | Complete |
| ADPT-02 | Phase 3 | Complete |
| ADPT-03 | Phase 3 | Complete |
| ADPT-04 | Phase 3 | Complete |
| GUARD-01 | Phase 4 | Pending |
| GUARD-02 | Phase 4 | Pending |
| GUARD-03 | Phase 4 | Pending |
| GUARD-04 | Phase 4 | Pending |
| GUARD-05 | Phase 4 | Pending |
| APRV-01 | Phase 4 | Pending |
| APRV-02 | Phase 4 | Pending |
| APRV-03 | Phase 4 | Pending |
| APRV-04 | Phase 4 | Pending |
| APRV-05 | Phase 4 | Pending |
| APRV-06 | Phase 4 | Pending |
| PRMT-01 | Phase 5 | Pending |
| PRMT-02 | Phase 5 | Pending |
| PRMT-03 | Phase 5 | Pending |
| PRMT-04 | Phase 5 | Pending |
| DUAL-01 | Phase 5 | Pending |
| DUAL-02 | Phase 5 | Pending |
| BRIEF-01 | Phase 6 | Pending |
| BRIEF-02 | Phase 6 | Pending |
| BRIEF-03 | Phase 6 | Pending |
| RSCH-01 | Phase 6 | Pending |
| RSCH-02 | Phase 6 | Pending |
| RSCH-03 | Phase 6 | Pending |
| RSCH-04 | Phase 6 | Pending |
| RSCH-05 | Phase 6 | Pending |
| RSCH-06 | Phase 6 | Pending |
| RSCH-07 | Phase 6 | Pending |
| DSGN-01 | Phase 7 | Pending |
| DSGN-02 | Phase 7 | Pending |
| DSGN-03 | Phase 7 | Pending |
| DSGN-04 | Phase 7 | Pending |
| DSGN-05 | Phase 7 | Pending |
| PLAN-01 | Phase 8 | Pending |
| PLAN-02 | Phase 8 | Pending |
| PLAN-03 | Phase 8 | Pending |
| PLAN-04 | Phase 8 | Pending |
| PLAN-05 | Phase 8 | Pending |
| BUILD-01 | Phase 9 | Pending |
| BUILD-02 | Phase 9 | Pending |
| BUILD-03 | Phase 9 | Pending |
| BUILD-04 | Phase 9 | Pending |
| BUILD-05 | Phase 9 | Pending |
| REVW-01 | Phase 10 | Pending |
| REVW-02 | Phase 10 | Pending |
| REVW-03 | Phase 10 | Pending |
| REVW-04 | Phase 10 | Pending |
| REVW-05 | Phase 10 | Pending |
| REVS-01 | Phase 10 | Pending |
| REVS-02 | Phase 10 | Pending |
| REVS-03 | Phase 10 | Pending |
| REVS-04 | Phase 10 | Pending |
| ARCH-01 | Phase 11 | Pending |
| ARCH-02 | Phase 11 | Pending |
| ARCH-03 | Phase 11 | Pending |
| COHR-01 | Phase 11 | Pending |
| COHR-02 | Phase 11 | Pending |
| COHR-03 | Phase 11 | Pending |
| COHR-04 | Phase 11 | Pending |
| COHR-05 | Phase 11 | Pending |
| FAST-01 | Phase 12 | Pending |
| FAST-02 | Phase 12 | Pending |
| FAST-03 | Phase 12 | Pending |

**Coverage:**
- v1 requirements: 82 total
- Mapped to phases: 82
- Unmapped: 0

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after initial definition*
