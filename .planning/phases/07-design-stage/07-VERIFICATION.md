---
phase: 07-design-stage
verified: 2026-03-10T00:00:00Z
status: gaps_found
score: 3/5 success criteria verified
re_verification: false
gaps:
  - truth: "Every architecture decision includes at least 1 rejected alternative — schema validation enforces this"
    status: failed
    reason: "ArchitectureDecision.alternatives_rejected uses Field(default_factory=list) with no min_length constraint. Empty list is accepted by Pydantic, the schema registry, and validate_with_retry. DSGN-03 requirement is NOT enforced mechanically."
    artifacts:
      - path: "minilegion/core/schemas.py"
        issue: "alternatives_rejected: list[str] = Field(default_factory=list) — no min_length=1 or field_validator enforcing non-empty"
    missing:
      - "Add min_length=1 constraint: alternatives_rejected: list[str] = Field(default_factory=list, min_length=1)"
      - "OR add a @field_validator('alternatives_rejected') that raises ValueError if empty"
      - "Add a test in test_cli_design.py that rejects a design with empty alternatives_rejected"

  - truth: "conventions_to_follow references conventions discovered in RESEARCH.json"
    status: failed
    reason: "DSGN-04 requires that conventions_to_follow reference conventions explicitly discovered in RESEARCH.json. The designer.md prompt gives a generic instruction ('maintain consistency with the existing codebase') with no explicit directive to populate the field from RESEARCH.json's existing_conventions field. The prompt does include {{research_json}} injection (structural support), but the instruction does not explicitly name existing_conventions as the source."
    artifacts:
      - path: "minilegion/prompts/designer.md"
        issue: "Line 21: conventions_to_follow instruction is generic ('consistency with the existing codebase') — no explicit instruction to use existing_conventions from RESEARCH.json"
    missing:
      - "Update conventions_to_follow instruction to explicitly say: 'List of conventions drawn from the existing_conventions field in the Research Findings above'"
      - "OR add a separate sentence in USER_TEMPLATE: 'Populate conventions_to_follow using the existing_conventions discovered in the Research Findings.'"
human_verification: []
---

# Phase 7: Design Stage Verification Report

**Phase Goal:** User can run the design stage to produce architecture decisions grounded in research findings
**Verified:** 2026-03-10T00:00:00Z
**Status:** ⚠️ GAPS FOUND (2 gaps)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can run `minilegion design` and see DESIGN.json + DESIGN.md produced with components, architecture_decisions, and all required fields | ✓ VERIFIED | `design()` command is fully implemented (lines 333-394 commands.py), not a stub. Calls validate_with_retry → save_dual → DESIGN.json + DESIGN.md. All 12 DesignSchema fields present. |
| 2 | Every architecture decision includes at least 1 rejected alternative — schema validation enforces this | ✗ FAILED | `alternatives_rejected: list[str] = Field(default_factory=list)` — empty list accepted. Confirmed: `validate('design', json_with_empty_alternatives)` passes without error. Schema constraint missing. |
| 3 | conventions_to_follow references conventions discovered in RESEARCH.json | ✗ FAILED | designer.md instruction for conventions_to_follow is generic ("maintain consistency with the existing codebase"). No explicit directive to draw from RESEARCH.json's `existing_conventions` field. `existing_conventions` not mentioned anywhere in the prompt. |
| 4 | Designer prompt enforces "design, don't plan" — output contains no task decomposition | ✓ VERIFIED | Line 4 designer.md: "Do NOT decompose into tasks or write implementation steps — design, don't plan." Explicit and correct. |
| 5 | design() produces DESIGN.json + DESIGN.md with all required fields from DesignSchema | ✓ VERIFIED | 12-field DesignSchema confirmed. DESIGN.json + DESIGN.md saved via save_dual(). Tested by test_design_saves_dual_output and test_design_writes_atomically_before_approval (both GREEN). |

**Score: 3/5 truths verified**

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `minilegion/cli/commands.py` | design() command — full implementation | ✓ VERIFIED | Lines 333-394. Full pipeline: preflight → load_prompt → render_prompt → validate_with_retry → save_dual → approve_design → state transition. Not a stub. |
| `tests/test_cli_design.py` | 10 unit tests for design command | ✓ VERIFIED | 10 tests, all GREEN (8.28s). Covers: preflight, LLM call, dual output, preflight failure, LLM error, write-before-approval, approval/rejection, stage transition. |
| `minilegion/prompts/designer.md` | Designer prompt with "design, don't plan" and {{research_json}} | ✓ VERIFIED | "design, don't plan" present (line 4). `{{research_json}}` present (line 38). `{{focus_files_content}}` present (line 40). 43 lines, substantive content. |
| `minilegion/core/schemas.py` | DesignSchema with 12 fields + alternatives_rejected min 1 constraint | ⚠️ PARTIAL | All 12 fields present. BUT: `alternatives_rejected` has no min_length=1 constraint. DSGN-03 not mechanically enforced. |
| `minilegion/core/preflight.py` | DESIGN stage requires BRIEF.md + RESEARCH.json + both approvals | ✓ VERIFIED | `Stage.DESIGN: ["BRIEF.md", "RESEARCH.json"]` (line 20). `Stage.DESIGN: ["brief_approved", "research_approved"]` (line 36). Complete. |
| `minilegion/core/approval.py` | approve_design() function | ✓ VERIFIED | Lines 98-105. Correct signature: `approve_design(state, state_path, design_summary)`. Calls `approve("design_approved", ...)`. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `design()` in commands.py | `_pipeline_stub` | NOT called | ✓ WIRED | Confirmed: `_pipeline_stub` not called in design() function body. Full implementation. |
| `design()` | `approve_design()` | Import + call at line 380 | ✓ WIRED | `from minilegion.core.approval import ... approve_design` (line 19). Called at line 380. |
| `design()` | `save_dual()` before `approve_design()` | Lines 376, 380 | ✓ WIRED | `save_dual(...)` line 376 precedes `approve_design(...)` line 380. Write-before-gate verified. |
| `design()` | `state.current_stage = Stage.DESIGN.value` | Line 383 | ✓ WIRED | Set at line 383, before `save_state()` at line 385. Correct. |
| `design()` | `except ApprovalError` before `except MiniLegionError` | Lines 388, 392 | ✓ WIRED | ApprovalError caught at line 388, MiniLegionError at line 392. Correct order. |
| `DesignSchema.ArchitectureDecision` | `alternatives_rejected` min 1 constraint | Schema Field constraint | ✗ NOT_WIRED | `Field(default_factory=list)` — no min_length or validator. Empty list accepted. |
| `designer.md` | `existing_conventions` from RESEARCH.json | Explicit prompt instruction | ✗ PARTIAL | `{{research_json}}` is injected (structural support), but no explicit instruction to use `existing_conventions` from it for `conventions_to_follow`. |
| `design()` | `RESEARCH.json` read and passed to LLM | `research_json = (project_dir / "RESEARCH.json").read_text(...)` line 355 | ✓ WIRED | RESEARCH.json read at line 355, passed to render_prompt as `research_json=research_json` at line 362. |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DSGN-01 | Designer receives BRIEF.md + RESEARCH.json + focus files → DESIGN.json + DESIGN.md | ✓ SATISFIED | Lines 354-363: BRIEF.md read, RESEARCH.json read, focus_files_content deferred (placeholder). Lines 376-377: DESIGN.json + DESIGN.md saved. Tests confirm. |
| DSGN-02 | DESIGN.json has all 12 required fields | ✓ SATISFIED | DesignSchema has exactly 12 fields: design_approach, architecture_decisions, components, data_models, api_contracts, integration_points, design_patterns_used, conventions_to_follow, technical_risks, out_of_scope, test_strategy, estimated_complexity. |
| DSGN-03 | Each architecture decision must have at least 1 rejected alternative | ✗ BLOCKED | `alternatives_rejected: list[str] = Field(default_factory=list)` — no min_length=1. Pydantic and registry accept empty list. Schema does NOT enforce this. |
| DSGN-04 | conventions_to_follow must reference conventions from RESEARCH.json | ✗ BLOCKED | Prompt instruction is generic. No explicit directive to use `existing_conventions` field from RESEARCH.json. `existing_conventions` not mentioned in prompt. |
| DSGN-05 | Designer prompt enforces "design, don't plan" | ✓ SATISFIED | Line 4 of designer.md: "Do NOT decompose into tasks or write implementation steps — design, don't plan." |

**DSGN-01 ORPHANED NOTE:** Focus files content is a placeholder string `"(Focus file reading deferred to Phase 9)"` — this is acceptable for Phase 7 scope, but marks incomplete DSGN-01 coverage until Phase 9.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `minilegion/cli/commands.py` | 356 | `focus_files_content = "(Focus file reading deferred to Phase 9)"` | ℹ️ Info | Placeholder for focus file content. Intentionally deferred to Phase 9. Does not block Design stage functionality. |
| `minilegion/core/schemas.py` | 38 | `alternatives_rejected: list[str] = Field(default_factory=list)` | 🛑 Blocker | Missing min_length=1 constraint means DSGN-03 is not mechanically enforced by the schema. LLM can return empty list without validation failure. |
| `minilegion/prompts/designer.md` | 21 | `"conventions_to_follow": List of conventions to maintain consistency with the existing codebase.` | 🛑 Blocker | Generic instruction does not reference RESEARCH.json's `existing_conventions`. LLM may hallucinate conventions rather than use discovered ones. |

---

## Human Verification Required

None — all verification items are fully automatable for this phase.

---

## Verification Checks Summary (All 10)

| # | Check | Result |
|---|-------|--------|
| 1 | design() command body replaces `_pipeline_stub` — no stub call remains | ✓ PASS |
| 2 | `approve_design` imported and called after `save_dual` | ✓ PASS |
| 3 | `state.current_stage = Stage.DESIGN.value` set before `save_state()` | ✓ PASS |
| 4 | `except ApprovalError:` appears BEFORE `except MiniLegionError:` | ✓ PASS |
| 5 | `save_dual()` called BEFORE `approve_design()` (write-before-gate) | ✓ PASS |
| 6 | All 10 design tests pass GREEN | ✓ PASS — 10/10 passed in 8.28s |
| 7 | Full suite 441 tests pass GREEN | ✓ PASS — 441 passed in 12.81s |
| 8 | DesignSchema has all 12 fields from DSGN-02 | ✓ PASS |
| 9 | designer.md contains "design, don't plan" instruction (DSGN-05) | ✓ PASS |
| 10 | designer.md has `{{research_json}}` variable (DSGN-04 support) | ✓ PASS — structural, but DSGN-04 semantics not met |

---

## Gaps Summary

**2 gaps block full goal achievement:**

### Gap 1 — DSGN-03: Schema does not enforce min 1 alternative rejected (BLOCKER)

The success criterion states "schema validation enforces this." It does not. `ArchitectureDecision.alternatives_rejected` uses `Field(default_factory=list)` with no minimum length constraint. A design with zero rejected alternatives will pass validation silently. The LLM prompt *does* say "MUST include at least one entry" but this is advisory to the LLM, not a machine-enforced contract.

**Fix:** Add `min_length=1` to the Field declaration:
```python
alternatives_rejected: list[str] = Field(default_factory=list, min_length=1)
```

### Gap 2 — DSGN-04: conventions_to_follow not explicitly linked to RESEARCH.json conventions (PARTIAL)

The `{{research_json}}` variable is correctly injected into the prompt, providing the LLM with research data. However, the `conventions_to_follow` field description says only "maintain consistency with the existing codebase" — it does not tell the LLM to populate this field *from* the `existing_conventions` field in RESEARCH.json. The LLM may invent generic conventions rather than using discovered ones.

**Fix:** Update the conventions_to_follow instruction in designer.md to:
```
- "conventions_to_follow": List of conventions drawn from the `existing_conventions` field in the Research Findings above. Each entry should directly reference a convention discovered during research.
```

---

_Verified: 2026-03-10T00:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
