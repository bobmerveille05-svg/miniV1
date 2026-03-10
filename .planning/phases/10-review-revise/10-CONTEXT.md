# Phase 10 Context

**Phase:** 10 — Review & Revise
**Date:** 2026-03-10
**Status:** Planning

## Goal

User can run the review stage to verify execution against design and conventions, with automatic revise loop on failure.

## Requirements

- REVW-01: Reviewer role receives diff + PLAN.json + DESIGN.json + conventions → REVIEW.json + REVIEW.md
- REVW-02: REVIEW.json fields: bugs, scope_deviations, design_conformity, convention_violations, security_risks, performance_risks, tech_debt, out_of_scope_files, success_criteria_met, verdict, corrective_actions
- REVW-03: Reviewer checks design conformity
- REVW-04: Reviewer checks convention compliance (from RESEARCH.json)
- REVW-05: Reviewer prompt enforces "identify, don't correct"
- REVS-01: verdict="revise" → re-enter execute with corrective_actions
- REVS-02: Revise loop bounded at max 2 iterations
- REVS-03: After 2 failed revisions, escalate to human with full context display
- REVS-04: design_conformity.conforms=False → offer to re-design before re-executing

## What already exists

- `Stage.REVIEW` defined in state.py
- `REQUIRED_FILES[Stage.REVIEW]` + `REQUIRED_APPROVALS[Stage.REVIEW]` in preflight.py
- `ReviewSchema` + `Verdict` enum in schemas.py
- `render_review_md()` in renderer.py
- `reviewer.md` prompt with all required placeholders: project_name, diff_text, plan_json, design_json, conventions
- `review()` stub in commands.py (calls `_pipeline_stub(Stage.REVIEW)`)

## What needs to be built

### Plan 10-01: Core review infrastructure
1. `approve_review` function in approval.py
2. `minilegion/core/diff.py` — `generate_diff_text(execution_log, project_dir)` → readable diff string for reviewer
3. `builder.md` — add `{{corrective_actions}}` section (empty string renders nothing; populated on revise)
4. Tests: test_approve_review (3 tests), test_diff (5 tests)

### Plan 10-02: review() command + revise loop
1. Wire `review()` command (replace stub)
2. Revise loop: verdict="revise" → re-run builder with corrective_actions → re-run reviewer → bounded at 2
3. Escalate to human after 2 iterations
4. Offer re-design if design_conformity.conforms=False
5. Track revise_count in state.metadata
6. Tests: test_cli_review (12 tests)

## Design decisions

- `_generate_diff_text()` lives in `minilegion/core/diff.py` — reads EXECUTION_LOG.json, formats per-file summary
- `revise_count` stored in `state.metadata["revise_count"]` (str — metadata is dict[str, str])
- Max revise iterations = 2 (configurable via config later, hardcoded constant now)
- Re-design offer: display warning + typer.confirm → on "no", stop (exit 0); on "yes", transition back to design (backtrack)
- Builder re-invocation during revise: call same builder pipeline logic (extract to `_run_builder()` helper) rather than calling `execute()` recursively
- `approve_review` sets `review_approved` in STATE.json
