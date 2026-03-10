# Phase 5 Verification: Prompts & Dual Output

**Phase Goal:** Every LLM role has a tested prompt template and every artifact is saved in both JSON and Markdown formats

**Verified:** 2026-03-10
**Result:** PASS — all 4 success criteria met

---

## Success Criteria Verification

### SC-1: Five prompt files exist in `prompts/` directory each with SYSTEM and USER_TEMPLATE sections
**Status: PASS**

Files confirmed present and committed (commit `5c17f0b`):
- `minilegion/prompts/researcher.md` — SYSTEM (1424 chars) + USER_TEMPLATE (201 chars)
- `minilegion/prompts/designer.md` — SYSTEM (1713 chars) + USER_TEMPLATE (274 chars)
- `minilegion/prompts/planner.md` — SYSTEM (1446 chars) + USER_TEMPLATE (234 chars)
- `minilegion/prompts/builder.md` — SYSTEM (1316 chars) + USER_TEMPLATE (211 chars)
- `minilegion/prompts/reviewer.md` — SYSTEM (1462 chars) + USER_TEMPLATE (276 chars)

All 5 files contain `<!-- SYSTEM -->` and `<!-- USER_TEMPLATE -->` markers. `load_prompt(role)` returns non-empty `(system, user_template)` tuple for all 5 roles. Verified by `TestLoadPrompt` (5 tests).

### SC-2: All prompts enforce JSON-only output with anchoring at start and end
**Status: PASS**

Runtime check: for each of 5 roles, `load_prompt(role)[0][:300]` contains "JSON" and `[-300:]` contains "JSON". All system prompts begin with "You MUST respond with valid JSON only" and end with "CRITICAL: Your entire response must be a single valid JSON object." Verified by `TestJsonAnchoring` (10 tests via parametrize).

### SC-3: `{{placeholder}}` variables in USER_TEMPLATE are replaced at call time
**Status: PASS**

`render_prompt("Hello {{name}}!", name="World")` returns `"Hello World!"`. All 5 USER_TEMPLATE sections contain the correct role-specific placeholders:
- researcher: `{{brief_content}}`, `{{codebase_context}}`, `{{project_name}}`
- designer: `{{brief_content}}`, `{{research_json}}`, `{{focus_files_content}}`, `{{project_name}}`
- planner: `{{brief_content}}`, `{{research_json}}`, `{{design_json}}`, `{{project_name}}`
- builder: `{{plan_json}}`, `{{source_files}}`, `{{project_name}}`
- reviewer: `{{diff_text}}`, `{{plan_json}}`, `{{design_json}}`, `{{conventions}}`, `{{project_name}}`

Unresolved placeholders raise `ConfigError`. Verified by `TestRenderPrompt` (7 tests) and `TestPromptPlaceholders` (5 parametrized tests).

### SC-4: Every LLM-produced artifact saved as both `.json` and `.md` — Markdown generated programmatically
**Status: PASS**

`save_dual(data, json_path, md_path)` writes both files atomically using `write_atomic()`. Runtime confirmation: JSON parses with `json.loads()`, MD starts with `# Research Report`. 5 render functions produce structured Markdown (not raw JSON dumps) from Pydantic model fields. `_RENDERERS` registry covers all 5 schema types. `ValueError` raised for unregistered types. Verified by `TestSaveDual` (5 tests) and per-schema test classes (14 tests).

---

## Test Results

```
tests/test_prompt_loader.py — 34 passed
tests/test_renderer.py      — 20 passed
Full suite                  — 379 passed, 0 failed
```

## Requirements Status

| Requirement | Description | Status |
|-------------|-------------|--------|
| PRMT-01 | 5 role prompts with SYSTEM + USER_TEMPLATE sections | COMPLETE |
| PRMT-02 | JSON-only output anchoring at start and end | COMPLETE |
| PRMT-03 | Prompts stored as .md files in prompts/ directory | COMPLETE |
| PRMT-04 | USER_TEMPLATE uses {{placeholder}} variable injection | COMPLETE |
| DUAL-01 | save_dual() writes both .json and .md atomically | COMPLETE |
| DUAL-02 | Markdown generated from parsed JSON, not by LLM | COMPLETE |

## Commits

| Hash | Description |
|------|-------------|
| `e90bdb4` | feat(05-02): dual-output renderer with per-schema markdown generation |
| `5c17f0b` | feat(05-01): prompt templates and loader with variable injection |

---

**Phase 5 goal achieved.** Infrastructure ready for pipeline stages (Phases 6-10).
