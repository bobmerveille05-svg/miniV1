---
phase: 16-research-brainstorm-mode
verified: 2026-03-12T02:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/7
  gaps_closed:
    - "RSM-02 BLOCKED: ResearchSchema Pydantic model lacked 7 brainstorm fields → all 7 added in commit 46c2777"
    - "RSM-03 BLOCKED: No Python-level recommendation enforcement → post-validation check added in commands.py commit be0b664"
  gaps_remaining: []
  regressions: []
---

# Phase 16: Research Brainstorm Mode Verification Report

**Phase Goal:** Add brainstorm exploration mode with bounded options, schema-validated recommendation output, and non-breaking config defaults.
**Verified:** 2026-03-12T02:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after gap closure plan 16-02 execution

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `minilegion research` (no flags) produces identical output to v1.0 codebase scan (fact mode) | ✓ VERIFIED | default_mode="fact" preserved; `test_research_no_flags_uses_fact_mode_default` PASSES; fact-mode ResearchSchema fields unchanged |
| 2 | `minilegion research --mode brainstorm --options 3` produces structured output with 7 brainstorm fields plus shared fields | ✓ VERIFIED | ResearchSchema now has 18 fields (11 fact + 7 brainstorm); `test_brainstorm_fields_preserved_by_model_dump` PASSES (no mock); `test_research_brainstorm_mode_passes_mode_parameter` PASSES |
| 3 | Brainstorm output validates against schema with recommendation always present and non-empty | ✓ VERIFIED | Post-validation check at commands.py:739-747 enforces non-empty recommendation when mode=brainstorm and require_recommendation=True; `test_recommendation_required_in_brainstorm_mode_command` and `test_recommendation_empty_string_rejected_in_brainstorm_mode` both PASS (exit code 1) |
| 4 | Config accepts research.default_mode, default_options, min/max_options, require_recommendation — all optional | ✓ VERIFIED | ResearchConfig (config.py) has all 5 fields with correct defaults; confirmed by `test_research_config_default_mode_is_fact` and `test_research_config_default_options_is_3` |
| 5 | Omitting research config fields leaves existing behavior unchanged (non-breaking) | ✓ VERIFIED | All fields optional; MiniLegionConfig instantiates with defaults when research field omitted; RSM-04 confirmed |
| 6 | Config default mode is "fact" and default options is 3 — matches current behavior | ✓ VERIFIED | Confirmed by unit tests and direct inspection: ResearchConfig().default_mode == "fact", default_options == 3 |
| 7 | Research command accepts --mode and --options flags and applies config defaults | ✓ VERIFIED | commands.py lines 638-646 define flags; lines 672-675 apply config defaults; lines 678-685 validate bounds |

**Score:** 7/7 truths verified (100%)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `minilegion/core/schemas.py` | ResearchSchema with 18 fields (11 fact + 7 brainstorm) | ✓ VERIFIED | 18 fields confirmed; all 7 brainstorm fields present at lines 106-112: problem_framing (str\|None), facts (list[str]), assumptions (list[str]), candidate_directions (list[dict]\|None), tradeoffs (list[str]), risks (list[str]), recommendation (str\|None); class docstring updated |
| `minilegion/cli/commands.py` | Post-validate_with_retry recommendation enforcement block | ✓ VERIFIED | Lines 738-747: `if mode == "brainstorm" and config.research.require_recommendation: if not research_data.recommendation: typer.echo(...) raise typer.Exit(code=1)` |
| `minilegion/core/config.py` | ResearchConfig with 5 fields + validator + integration | ✓ VERIFIED | Confirmed in initial verification (Plan 16-01); unchanged |
| `minilegion/schemas/research.schema.json` | JSON schema matching Pydantic model_json_schema() output | ✓ VERIFIED | Regenerated in commit be0b664; 155-line file with all 18 fields documented; `test_schema_matches_model` now passes; description, candidate_directions, nullable types, and additionalProperties all match Pydantic output exactly |
| `minilegion/prompts/researcher.md` | Dual prompts (FACT + BRAINSTORM) with mode-aware template | ✓ VERIFIED | Confirmed in initial verification (Plan 16-01); unchanged |
| `tests/test_cli_brief_research.py` | 11 tests covering RSM-01/02/03/04 (6 original + 5 new) | ✓ VERIFIED | All 11 tests PASS: 6 original (Plan 16-01) + 5 new (Plan 16-02): test_brainstorm_fields_preserved_by_model_dump, test_fact_mode_fields_unaffected_by_brainstorm_addition, test_recommendation_required_in_brainstorm_mode_command, test_recommendation_empty_string_rejected_in_brainstorm_mode, test_recommendation_not_required_in_fact_mode |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| MiniLegionConfig.research | research() command | config.research.default_mode/default_options | ✓ WIRED | Lines 673-675 apply defaults from config fields |
| research() CLI args | render_prompt() | mode parameter | ✓ WIRED | Line 716 passes mode=mode to render_prompt |
| render_prompt() | researcher.md template | {{#if mode}} blocks | ✓ WIRED | researcher.md lines 65-77 contain mode-aware conditional |
| LLM response | validate_with_retry() | ResearchSchema Pydantic model | ✓ WIRED | ResearchSchema now declares all brainstorm fields; model_dump_json() preserves all 18 fields — no silent data loss |
| validate_with_retry() | save_dual() | model_dump_json() | ✓ WIRED | Brainstorm fields declared in Pydantic model → preserved in JSON output; confirmed by direct round-trip test (no mocking) |
| research() brainstorm path | typer.Exit(1) | require_recommendation enforcement | ✓ WIRED | commands.py:739-747; test_recommendation_required_in_brainstorm_mode_command confirms exit code 1 when recommendation=None |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RSM-01 | 16-01 | Backward compatibility: fact mode default, no regression | ✓ SATISFIED | default_mode="fact"; test_research_no_flags_uses_fact_mode_default PASSES; test_fact_mode_fields_unaffected_by_brainstorm_addition PASSES; fact fields unchanged |
| RSM-02 | 16-01 + 16-02 | Brainstorm output structure: 7 brainstorm fields including recommendation preserved | ✓ SATISFIED | All 7 brainstorm fields in ResearchSchema (commit 46c2777); model_dump_json() round-trip verified; test_brainstorm_fields_preserved_by_model_dump PASSES without mocking |
| RSM-03 | 16-01 + 16-02 | Schema validation + non-empty recommendation enforcement | ✓ SATISFIED | Post-validate_with_retry check in commands.py:739-747 (commit be0b664); exits code 1 for None or empty-string recommendation; test_recommendation_required and test_recommendation_empty_string both PASS |
| RSM-04 | 16-01 | Config non-breaking with optional research fields | ✓ SATISFIED | All research config fields optional; require_recommendation=True default triggers enforcement; test_recommendation_not_required_in_fact_mode confirms fact mode unaffected |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | No blockers or warnings in Plan 16-02 modified files |

**Pre-existing test failures (confirmed NOT regressions from Phase 16):** 4 tests fail in the full suite. All 4 were confirmed to fail identically on commit `e3e4bd9` (before any Plan 16-02 changes) — they are pre-existing failures unrelated to this phase:
- `TestArchiveStateUpdates::test_archive_adds_history_entry` — state `history` key missing (pre-existing)
- `TestBriefCommand::test_brief_approval_accepted_transitions_state` — stage transition issue (pre-existing)
- `TestResearchCommand::test_research_approval_accepted_transitions_state` — stage transition issue (pre-existing)
- `TestResearchCommand::test_research_state_current_stage_is_research_after_approval` — stage transition issue (pre-existing)

### Human Verification Required

None — all gaps verified programmatically.

### Gap Closure Summary

Both gaps from the initial verification are fully closed:

**Gap 1 — RSM-02 BLOCKED (CLOSED):** `ResearchSchema` in `minilegion/core/schemas.py` now has 18 total fields (11 fact + 7 brainstorm). All 7 brainstorm fields (`problem_framing`, `facts`, `assumptions`, `candidate_directions`, `tradeoffs`, `risks`, `recommendation`) are declared as optional with correct defaults (`str|None=None` for scalars, `Field(default_factory=list)` for arrays). `model_dump_json()` now preserves all brainstorm fields — no silent data loss. Verified by direct Pydantic round-trip test `test_brainstorm_fields_preserved_by_model_dump` which bypasses all mocking.

**Gap 2 — RSM-03 BLOCKED (CLOSED):** Post-validation recommendation enforcement added at `commands.py:738-747`. When `mode == "brainstorm"` and `config.research.require_recommendation` is True, any `recommendation` value that is `None` or an empty string causes exit code 1 with a clear error message. Verified by `test_recommendation_required_in_brainstorm_mode_command` (None → exit 1) and `test_recommendation_empty_string_rejected_in_brainstorm_mode` (empty string → exit 1). Fact mode is unaffected — `test_recommendation_not_required_in_fact_mode` confirms exit code 0.

**Bonus fix auto-applied in Plan 16-02:** `minilegion/schemas/research.schema.json` was regenerated from `ResearchSchema.model_json_schema()` to achieve exact byte-level match with the Pydantic model, fixing a pre-existing `test_schema_matches_model` failure introduced in Plan 16-01. The JSON schema file is now the single source of truth and the contract test enforces ongoing sync.

**Final test results:** 11/11 `TestResearchBrainstormMode` PASS; 698/702 total suite PASS (4 pre-existing failures confirmed unrelated to Phase 16).

---

_Verified: 2026-03-12T02:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
_Re-verification: Yes — after Plan 16-02 gap closure_
