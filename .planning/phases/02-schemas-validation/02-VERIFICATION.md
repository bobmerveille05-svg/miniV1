---
phase: 02-schemas-validation
verified: 2026-03-10T12:15:00Z
status: passed
score: 8/8 must-haves verified
---

# Phase 2: Schemas & Validation Verification Report

**Phase Goal:** Pydantic models for all 6 machine-readable artifact types, JSON Schema generation, schema registry with validation function, pre-parse fixups for LLM output, and retry logic with error feedback and raw debug capture.
**Verified:** 2026-03-10T12:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All 6 artifact types have Pydantic models that accept valid data and reject invalid data with clear errors | ✓ VERIFIED | 5 models in `schemas.py` (ResearchSchema, DesignSchema, PlanSchema, ExecutionLogSchema, ReviewSchema) + ProjectState reused from `state.py`. All required fields enforce presence, list/dict fields default to empty. 33 schema tests pass including rejection tests. |
| 2 | JSON Schema files exist for all 6 artifacts and are valid JSON Schema documents | ✓ VERIFIED | 6 `.schema.json` files exist in `minilegion/schemas/`. Each has `"type": "object"` and `"properties"` keys. 30 JSON schema tests pass, including content matching against `model_json_schema()`. |
| 3 | Registry provides get_schema(), get_json_schema(), and validate() for all 6 artifact names | ✓ VERIFIED | `registry.py` exports `SCHEMA_REGISTRY` with 6 entries, plus 3 public functions. `get_schema("unknown")` raises `KeyError` with valid names listed. 42 registry tests pass. |
| 4 | validate() accepts both raw JSON strings and dicts and returns validated model instances | ✓ VERIFIED | `registry.py` line 93-95: isinstance routing — `model_validate_json` for str, `model_validate` for dict. Tests verify both paths. Live verification: `validate('research', {'project_overview': 'test'})` returns `ResearchSchema` instance. |
| 5 | Pre-parse fixups clean common LLM output quirks (markdown fences, trailing commas, BOM/control chars) before validation | ✓ VERIFIED | `fixups.py` implements 4 functions: `strip_bom_and_control`, `strip_markdown_fences`, `fix_trailing_commas`, `apply_fixups`. Pipeline order: BOM→fences→commas. 33 fixup tests pass including combined input producing valid JSON. |
| 6 | Invalid LLM output triggers retry with human-readable error feedback (not raw Pydantic dumps) | ✓ VERIFIED | `retry.py` `validate_with_retry` catches `PydanticValidationError`, calls `summarize_errors()` for concise feedback capped at 5 issues, appends to retry prompt with `"--- VALIDATION ERROR ---"` header. Tests verify second call receives error feedback in prompt. |
| 7 | After 2 retries, raw LLM output is saved to project-ai/debug/*_RAW_DEBUG_*.txt | ✓ VERIFIED | `save_raw_debug()` writes `{ARTIFACT}_RAW_DEBUG_{timestamp}.txt` with Windows-safe timestamps (`%Y%m%dT%H%M%S`). Content includes raw output + validation errors. Uses `write_atomic()`. Tests verify file creation, naming pattern, and content. |
| 8 | Retry logic uses config.max_retries as the single source of truth for retry count | ✓ VERIFIED | `retry.py` line 140: `for attempt in range(1 + config.max_retries)` — no hardcoded retry count. Tests verify with max_retries=1 (2 calls), max_retries=2 (3 calls), and max_retries=3 (4 calls). |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `minilegion/core/schemas.py` | 5 Pydantic models + nested sub-models + Verdict enum | ✓ VERIFIED | 155 lines. 5 top-level models, 6 nested sub-models (ArchitectureDecision, Component, PlanTask, ChangedFile, TaskResult, DesignConformity), Verdict enum. All field types match REQUIREMENTS.md specs. |
| `minilegion/core/registry.py` | SCHEMA_REGISTRY + get_schema/get_json_schema/validate | ✓ VERIFIED | 95 lines. Registry maps 6 names. validate() routes str/dict. ValidationError propagates (not caught). |
| `minilegion/core/fixups.py` | strip_markdown_fences, fix_trailing_commas, strip_bom_and_control, apply_fixups | ✓ VERIFIED | 100 lines. 4 functions exported. Pipeline chains in correct order. |
| `minilegion/core/retry.py` | validate_with_retry, summarize_errors, save_raw_debug | ✓ VERIFIED | 175 lines. All 3 functions implemented. Proper PydanticValidationError alias. Raises minilegion ValidationError after exhaustion. |
| `minilegion/schemas/research.schema.json` | JSON Schema for research | ✓ VERIFIED | Valid JSON, type: object, 11 properties matching ResearchSchema fields. |
| `minilegion/schemas/design.schema.json` | JSON Schema for design | ✓ VERIFIED | Valid JSON, type: object, $defs for ArchitectureDecision/Component. |
| `minilegion/schemas/plan.schema.json` | JSON Schema for plan | ✓ VERIFIED | Valid JSON, type: object, $defs for PlanTask. |
| `minilegion/schemas/execution_log.schema.json` | JSON Schema for execution_log | ✓ VERIFIED | Valid JSON, type: object, $defs for ChangedFile/TaskResult. |
| `minilegion/schemas/review.schema.json` | JSON Schema for review | ✓ VERIFIED | Valid JSON, type: object, $defs for DesignConformity/Verdict. |
| `minilegion/schemas/state.schema.json` | JSON Schema for state | ✓ VERIFIED | Valid JSON, type: object, $defs for HistoryEntry. Reuses ProjectState from state.py. |
| `minilegion/schemas/generate.py` | JSON Schema generation script | ✓ VERIFIED | 36 lines. Imports SCHEMA_REGISTRY, writes all 6 files. Runnable as module. |
| `minilegion/schemas/__init__.py` | Package init | ✓ VERIFIED | Exists with docstring. |
| `tests/test_schemas.py` | Schema model tests | ✓ VERIFIED | 343 lines, 33 tests. Covers all 5 models + enums + nested models + roundtrip. |
| `tests/test_registry.py` | Registry function tests | ✓ VERIFIED | 153 lines, 42 tests (parametrized). Covers all 6 names, str/dict input, error cases. |
| `tests/test_json_schemas.py` | JSON Schema file tests | ✓ VERIFIED | 65 lines, 30 tests (parametrized). Existence, validity, structure, model matching. |
| `tests/test_fixups.py` | Fixup function tests | ✓ VERIFIED | 224 lines, 33 tests. Individual + pipeline + edge cases. |
| `tests/test_retry.py` | Retry logic tests | ✓ VERIFIED | 408 lines, 20 tests. Summarize errors, save debug, full retry loop, max_retries respected. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `registry.py` | `schemas.py` | imports all 5 schema classes | ✓ WIRED | Line 19-25: imports ResearchSchema, DesignSchema, PlanSchema, ExecutionLogSchema, ReviewSchema |
| `registry.py` | `state.py` | imports ProjectState as 6th schema | ✓ WIRED | Line 26: `from minilegion.core.state import ProjectState` |
| `generate.py` | `registry.py` | uses SCHEMA_REGISTRY | ✓ WIRED | Line 12: `from minilegion.core.registry import SCHEMA_REGISTRY` |
| `retry.py` | `registry.py` | calls validate() | ✓ WIRED | Line 34: `from minilegion.core.registry import validate`; used at line 150 |
| `retry.py` | `fixups.py` | calls apply_fixups() | ✓ WIRED | Line 33: `from minilegion.core.fixups import apply_fixups`; used at line 146 |
| `retry.py` | `file_io.py` | calls write_atomic() | ✓ WIRED | Line 32: `from minilegion.core.file_io import write_atomic`; used at line 102 |
| `retry.py` | `config.py` | reads config.max_retries | ✓ WIRED | Line 140: `range(1 + config.max_retries)` — not hardcoded |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SCHM-01 | 02-01 | Pydantic models define all 6 machine-readable artifact schemas | ✓ SATISFIED | 5 new models in `schemas.py` + ProjectState reused. All field specs from REQUIREMENTS.md matched. 33 schema tests pass. |
| SCHM-02 | 02-01 | JSON Schema files generated from Pydantic models for external tool consumption | ✓ SATISFIED | 6 `.schema.json` files pre-generated via `generate.py`. Tests confirm they match `model_json_schema()` output exactly. |
| SCHM-03 | 02-01, 02-02 | LLM output parsed and validated against schema immediately after each call | ✓ SATISFIED | `registry.validate()` provides the validation function. `fixups.apply_fixups()` pre-parses. `retry.validate_with_retry()` orchestrates fixup→validate→retry loop. All wired and tested. |
| SCHM-04 | 02-02 | Invalid JSON triggers retry with error feedback injected into next LLM call (max 2 retries) | ✓ SATISFIED | `validate_with_retry` catches `PydanticValidationError`, appends `summarize_errors()` output to retry prompt. Uses `config.max_retries` (default 2). Tests verify call count and feedback injection. |
| SCHM-05 | 02-02 | After max retries, raw LLM output saved to *_RAW_DEBUG.txt for diagnosis | ✓ SATISFIED | `save_raw_debug()` creates `{ARTIFACT}_RAW_DEBUG_{timestamp}.txt` in `project-ai/debug/`. Uses `write_atomic()`. File contains raw output + error summary. Tests verify creation and content. |

No orphaned requirements found — all 5 SCHM-* requirements mapped to Phase 2 in REQUIREMENTS.md are covered by plans 02-01 and 02-02.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO/FIXME/placeholder comments, no empty implementations, no stub returns found in any Phase 2 source files.

### Human Verification Required

No human verification items needed. All phase deliverables are pure logic (Pydantic models, string processing, validation orchestration) with no UI, visual, or external service dependencies. All behaviors are fully testable and tested programmatically.

### Test Results

```
233 passed in 3.36s
```

Full test suite (Phase 1 + Phase 2) passes with zero failures and zero regressions.

### Gaps Summary

No gaps found. All 8 observable truths verified, all 17 artifacts exist and are substantive, all 7 key links are wired, all 5 requirements are satisfied, and all 233 tests pass. Phase goal fully achieved.

---

_Verified: 2026-03-10T12:15:00Z_
_Verifier: OpenCode (gsd-verifier)_
