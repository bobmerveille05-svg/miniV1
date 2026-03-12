---
phase: 16-research-brainstorm-mode
verified: 2026-03-12T00:00:00Z
status: gaps_found
score: 4/7 must-haves verified
gaps:
  - truth: "Brainstorm output validates against schema with recommendation always present and non-empty"
    status: failed
    reason: "ResearchSchema Pydantic model lacks brainstorm-specific fields (problem_framing, facts, assumptions, candidate_directions, tradeoffs, risks, recommendation). Only JSON schema file updated. Extra fields allowed but dropped by model_dump_json()."
    artifacts:
      - path: "minilegion/core/schemas.py"
        issue: "ResearchSchema missing 7 brainstorm fields. Only fact mode fields (11) defined. Need to add optional fields for brainstorm mode."
      - path: "minilegion/core/registry.py"
        issue: "ResearchSchema in registry still points to incomplete Pydantic model. Brainstorm data will validate but fields will be lost in model_dump_json()."
    missing:
      - "Add optional brainstorm fields to ResearchSchema: problem_framing (str), facts (list[str]), assumptions (list[str]), candidate_directions (list[dict]), tradeoffs (list[str]), risks (list[str]), recommendation (str)"
      - "Mark recommendation as required/non-empty in brainstorm mode context (Python code validation, not JSON schema)"
  - truth: "Brainstorm output validates against schema with 8 required brainstorm fields plus shared fields"
    status: partial
    reason: "JSON schema file has all 19 fields documented (11 shared + 8 brainstorm). Pydantic model only has 11 shared fields. Validation silently succeeds but fields are dropped."
    artifacts:
      - path: "minilegion/schemas/research.schema.json"
        issue: "Complete and correct - includes all brainstorm fields with proper structure"
      - path: "minilegion/core/schemas.py"
        issue: "Incomplete - missing brainstorm field definitions"
    missing:
      - "Sync Pydantic ResearchSchema with JSON schema file to include all brainstorm fields as optional"
---

# Phase 16: Research Brainstorm Mode Verification Report

**Phase Goal:** Add brainstorm exploration mode to research stage with bounded candidate directions, schema-validated recommendation output, and non-breaking config defaults.

**Verified:** 2026-03-12T00:00:00Z
**Status:** GAPS_FOUND
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `minilegion research` (no flags) produces identical output to v1.0 codebase scan (fact mode) | ✓ VERIFIED | Default mode="fact" (config default), no regression in existing fact mode fields (11 fields preserved), approval gate unchanged |
| 2 | `minilegion research --mode brainstorm --options 3` produces structured output with 8 required fields including recommendation | ✗ FAILED | JSON schema has fields but Pydantic ResearchSchema lacks them. Brainstorm fields not preserved in model_dump_json() output. |
| 3 | Brainstorm output validates against schema with recommendation always present and non-empty | ✗ FAILED | ResearchSchema allows extra fields but doesn't preserve them. Validation succeeds but recommendation field is dropped from output. |
| 4 | Config accepts research.default_mode, default_options, min/max_options, require_recommendation — all optional | ✓ VERIFIED | ResearchConfig created with all 5 fields, all have proper defaults, integrated into MiniLegionConfig with Field(default_factory=) |
| 5 | Omitting research config fields leaves existing behavior unchanged (non-breaking) | ✓ VERIFIED | MiniLegionConfig instantiates with all defaults when research field omitted, default_mode="fact" ensures backward compatibility |
| 6 | Config default mode is "fact" and default options is 3 — matches current behavior | ✓ VERIFIED | ResearchConfig().default_mode == "fact", ResearchConfig().default_options == 3 |
| 7 | Research command accepts --mode and --options flags and applies config defaults | ✓ VERIFIED | Flags defined in commands.py lines 634-646, config defaults applied lines 672-675, validation lines 678-685 |

**Score:** 4/7 truths verified (57%)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `minilegion/core/config.py` | ResearchConfig with 5 fields + validator + integration | ✓ VERIFIED | ResearchConfig class lines 237-256, all fields present with correct defaults, validator for normalize, integrated at line 291 |
| `minilegion/schemas/research.schema.json` | JSON schema supporting fact + brainstorm modes | ✓ VERIFIED | Schema complete with all 19 properties (11 fact + 8 brainstorm), correct structure for candidate_directions as objects with name/description |
| `minilegion/prompts/researcher.md` | Dual prompts (FACT + BRAINSTORM) with mode-aware template | ✓ VERIFIED | Both MODE sections present (lines 4-5, 23-34), mode-aware USER_TEMPLATE (lines 65-77 with {{#if mode == "brainstorm"}}) |
| `minilegion/cli/commands.py` | research() command with --mode and --options flags | ✓ VERIFIED | Flags defined, config defaults applied, validation implemented, render_prompt receives mode and num_options |
| `minilegion/core/schemas.py (ResearchSchema)` | Pydantic model with brainstorm fields | ✗ MISSING | Only fact mode fields (11) defined. Lacks: problem_framing, facts, assumptions, candidate_directions, tradeoffs, risks, recommendation |
| `tests/test_cli_brief_research.py` | 6 tests covering RSM-01/02/03/04 | ✓ VERIFIED | TestResearchBrainstormMode class with 6 tests all passing. Tests: fact mode default, brainstorm mode parameter, config defaults, options validation |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| MiniLegionConfig.research | research() command | config.research.default_mode/default_options | ✓ WIRED | Lines 673-675 apply defaults from config fields |
| research() CLI args | render_prompt() | mode parameter | ✓ WIRED | Line 716 passes mode=mode to render_prompt |
| render_prompt() | researcher.md template | {{#if mode}} blocks | ✓ WIRED | researcher.md lines 65-77 contain mode-aware conditional |
| LLM response | validate_with_retry() | schema validation | ⚠️ PARTIAL | Validation succeeds due to extra fields allowed, but brainstorm fields missing from Pydantic model cause loss in model_dump_json() |
| validate_with_retry() | save_dual() | model_dump_json() | ✗ BROKEN | save_dual uses model_dump_json() which drops extra brainstorm fields not in Pydantic model |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RSM-01 | 16-01 | Backward compatibility: fact mode default, no regression | ✓ SATISFIED | default_mode="fact" with all existing fact fields preserved, tests verify no flags → fact mode |
| RSM-02 | 16-01 | Brainstorm output structure: 8 fields including recommendation | ✗ BLOCKED | JSON schema has structure but Pydantic model lacks brainstorm field definitions. Output will not contain brainstorm-specific data. |
| RSM-03 | 16-01 | Schema validation + non-empty recommendation | ✗ BLOCKED | ResearchSchema lacks recommendation field definition. Validation silently succeeds but field is dropped from output. |
| RSM-04 | 16-01 | Config non-breaking with optional research fields | ✓ SATISFIED | All research config fields optional with sensible defaults, omission uses all defaults, no config required for existing workflows |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| minilegion/core/schemas.py | 90-103 | ResearchSchema incomplete — fact mode only | 🛑 BLOCKER | Brainstorm data validated but not preserved. RESEARCH.json will lack recommendation, problem_framing, etc. Goal RSM-02/RSM-03 fails. |
| minilegion/core/renderer.py | (save_dual) | model_dump_json() silently drops unmodeled fields | 🛑 BLOCKER | Extra brainstorm fields allowed in validation but lost in output. Silent data loss. |
| tests/test_cli_brief_research.py | 1050, 1070 | Mock validate_with_retry — tests don't catch schema gap | ⚠️ WARNING | Test uses mock data and mocks validate_with_retry. Never validates brainstorm data through actual Pydantic model. False positive test pass. |

### Human Verification Required

None required if gaps are closed.

### Gaps Summary

**Critical Issue: Pydantic ResearchSchema out of sync with JSON schema**

The JSON schema file (`minilegion/schemas/research.schema.json`) has been properly updated with all 8 brainstorm-specific fields (problem_framing, facts, assumptions, candidate_directions, tradeoffs, risks, recommendation, plus open_questions). However, the **Pydantic model in `minilegion/core/schemas.py`** was not updated to include these fields.

**Current state:**
- ✓ JSON schema: Complete with 19 fields (11 fact + 8 brainstorm)
- ✗ Pydantic ResearchSchema: Only 11 fact fields
- ✗ Validation pathway broken: Extra fields accepted but dropped by `model_dump_json()`

**Impact:**
1. **RSM-02 fails:** Brainstorm output will not contain the 8 required brainstorm-specific fields
2. **RSM-03 fails:** Recommendation field (critical for brainstorm mode) won't be in saved RESEARCH.json
3. **Silent data loss:** Validation succeeds but output is incomplete
4. **Tests pass but goal fails:** Mocked validate_with_retry hides the actual schema gap

**Required fix:**
Add these 7 optional fields to ResearchSchema in `minilegion/core/schemas.py`:
```python
problem_framing: str | None = None
facts: list[str] = Field(default_factory=list)
assumptions: list[str] = Field(default_factory=list)
candidate_directions: list[dict] | None = None  # [{name: str, description: str}, ...]
tradeoffs: list[str] = Field(default_factory=list)
risks: list[str] = Field(default_factory=list)
recommendation: str | None = None
```

Plus add validation (in Python code, since JSON schema can't enforce conditional requirements):
- In brainstorm mode: recommendation must be non-empty string
- recommendation presence can be validated in commands.py after validate_with_retry returns

---

_Verified: 2026-03-12T00:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
