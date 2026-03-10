# Phase 12 Context: Fast Mode

**Phase:** 12 — Fast Mode
**Date:** 2026-03-10
**Mode:** YOLO (auto-generated)

## Goal

Experienced users can skip research and design stages for quick iterations with degraded but functional context.

## Requirements

- **FAST-01**: `--fast` flag allows plan command to work with basic context (tree + brief) when RESEARCH.json/DESIGN.json don't exist
- **FAST-02**: `--skip-research-design` explicitly skips research and design stages
- **FAST-03**: Skipped stages are recorded in STATE.json but don't block downstream commands

## Current State Analysis

### What exists

The `plan()` command in `commands.py` already accepts `--fast` and `--skip-research-design` flags (stubs from Phase 1 CLI skeleton), but both are ignored — the normal preflight + LLM flow runs regardless.

### Key constraints from codebase

1. **State machine** (`state.py`): forward transitions are strictly one-step-at-a-time. `can_transition(Stage.PLAN)` requires current stage to be `Stage.DESIGN`. When using fast mode, the user starts from BRIEF stage (having skipped research and design). We need the state machine to accept PLAN from BRIEF for fast mode, OR we must update state to PLAN via a series of synthetic transitions.

2. **Preflight** (`preflight.py`): `Stage.PLAN` requires files `["BRIEF.md", "RESEARCH.json", "DESIGN.json"]` and approvals `["brief_approved", "research_approved", "design_approved"]`. Fast mode must bypass these for missing research/design artifacts.

3. **Downstream stages** (execute, review, archive): require RESEARCH.json/DESIGN.json in their preflight file checks. If fast mode skips them, downstream stages must be aware.

4. **LLM prompt for planner** (`planner.md`): uses `{{research_json}}` and `{{design_json}}` placeholders. A fast-mode planner prompt needs a degraded fallback.

### Design Decisions (YOLO auto-generated)

**Decision 1: How to advance state through skipped stages**

- Option A: Modify `StateMachine.can_transition()` to allow multi-step skips — breaks linear constraint that is tested and relied upon elsewhere.
- Option B: Programmatically apply synthetic transitions through research→design stages, setting approvals and metadata flags — preserves state machine integrity, marks stages as auto-skipped.
- **→ Decision: Option B** — synthetic transitions with `skipped_stages` in metadata

**Decision 2: How to handle preflight for fast mode**

- Option A: Add `skip_stages` parameter to `check_preflight()` — clean separation
- Option B: Catch `PreflightError` in fast mode and ignore it — fragile, hides real errors
- Option C: In fast mode, pass custom reduced `REQUIRED_FILES`/`REQUIRED_APPROVALS` — verbose
- **→ Decision: Option A** — add optional `skip_stages: set[str] | None = None` to `check_preflight()`

**Decision 3: Fast mode planner prompt**

- Option A: Create a separate `planner_fast.md` prompt file — extra file to maintain
- Option B: Use the same prompt with empty strings for research_json and design_json — LLM gets no structure but doesn't error
- Option C: Pass a "tree summary" as a substitute for research_json — better context
- **→ Decision: Option C** — pass codebase tree summary as research_json substitute, empty object as design_json substitute

**Decision 4: Recording skipped stages in STATE.json**

- Use `state.metadata["skipped_stages"]` — JSON-serialized list of stage names
- Downstream commands check `state.metadata.get("skipped_stages", "[]")` to know what was skipped
- Preflight for EXECUTE and REVIEW skips file/approval checks for skipped stages

## Success Criteria

1. `minilegion plan --fast` from `brief` stage produces PLAN.json using only tree + brief
2. `minilegion plan --skip-research-design` is an alias for `--fast` (same behavior)
3. After fast plan, STATE.json has `metadata["skipped_stages"]` containing `["research", "design"]`
4. `minilegion execute` after fast plan works without RESEARCH.json or DESIGN.json
5. `minilegion review` after fast plan works without RESEARCH.json or DESIGN.json
6. `minilegion archive` after fast plan works without RESEARCH.json or DESIGN.json
