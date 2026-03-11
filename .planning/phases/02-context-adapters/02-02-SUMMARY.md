---
phase: 02-context-adapters
plan: "02"
subsystem: context-adapters-scaffold
tags: [context, adapters, templates, memory, init, scaffold, adr]
dependency_graph:
  requires: [minilegion/core/context_assembler.py, minilegion/cli/commands.py, minilegion/core/file_io.py]
  provides: [project-ai/adapters/ scaffold, project-ai/templates/ scaffold, project-ai/memory/ scaffold, ADR-0007]
  affects: [minilegion/cli/commands.py, tests/test_init.py, tests/test_context_assembler.py]
tech_stack:
  added: []
  patterns: [in-code static content constants, idempotent init scaffolding, per-stage template seeding]
key_files:
  created:
    - .planning/milestones/v1.1-ADR-0007.md
  modified:
    - minilegion/cli/commands.py
    - tests/test_init.py
    - tests/test_context_assembler.py
decisions:
  - "Adapter and template content kept as module-level constants in commands.py (no external bundled files) — simpler packaging"
  - "init command extended (not replaced): adds adapters/templates/memory after existing prompts/ creation"
  - "STAGE_TEMPLATES dict covers all 8 Stage enum values so any pipeline stage has a template"
  - "Memory scaffold files seeded with instruction-comment content so new users understand the format immediately"
  - "ADR-0007 verified complete with all 5 required sections — no content gap-fill needed"
metrics:
  duration: "~8 min"
  completed: "2026-03-11"
  tasks_completed: 2
  tests_added: 12
  files_created: 1
  files_modified: 3
  baseline_tests: 656
  final_tests: 668
requirements: [CTX-03, CTX-04, CTX-05, CTX-06]
---

# Phase 2 Plan 02: Context Adapters + Scaffold Summary

**One-liner:** `minilegion init` now seeds `project-ai/adapters/` (5 tool-specific files), `project-ai/templates/` (8 stage templates), and `project-ai/memory/` (3 scaffold files) as in-code constants, so `minilegion context <tool>` immediately produces rich, non-stub output on any freshly initialized project.

## What Was Built

### `minilegion/cli/commands.py` (modified)

Added 5 groups of module-level constants:

**Adapter constants** (CTX-03):
- `ADAPTER_BASE` — generic "how to use this context" instructions for any AI tool
- `ADAPTER_CLAUDE` — Claude-specific senior engineer framing
- `ADAPTER_CHATGPT` — ChatGPT single-source-of-truth framing
- `ADAPTER_COPILOT` — Copilot Chat scope-aware framing
- `ADAPTER_OPENCODE` — OpenCode authoritative task framing

**Stage template dict** (CTX-04):
- `STAGE_TEMPLATES: dict[str, str]` — maps all 8 stage names (`init`, `brief`, `research`, `design`, `plan`, `execute`, `review`, `archive`) to short markdown instructions describing what the AI should produce

**Memory scaffold constants** (CTX-05):
- `MEMORY_DECISIONS` — decisions.md scaffold with date/decision/rationale format hint
- `MEMORY_GLOSSARY` — glossary.md scaffold with term/definition format hint
- `MEMORY_CONSTRAINTS` — constraints.md scaffold with constraint/why format hint

**Extended `init()` function**: After creating `prompts/`, the command now also:
```python
(project_ai / "adapters").mkdir()
write_atomic(project_ai / "adapters" / "_base.md", ADAPTER_BASE)
write_atomic(project_ai / "adapters" / "claude.md", ADAPTER_CLAUDE)
write_atomic(project_ai / "adapters" / "chatgpt.md", ADAPTER_CHATGPT)
write_atomic(project_ai / "adapters" / "copilot.md", ADAPTER_COPILOT)
write_atomic(project_ai / "adapters" / "opencode.md", ADAPTER_OPENCODE)

(project_ai / "templates").mkdir()
for stage_name, content in STAGE_TEMPLATES.items():
    write_atomic(project_ai / "templates" / f"{stage_name}.md", content)

(project_ai / "memory").mkdir()
write_atomic(project_ai / "memory" / "decisions.md", MEMORY_DECISIONS)
write_atomic(project_ai / "memory" / "glossary.md", MEMORY_GLOSSARY)
write_atomic(project_ai / "memory" / "constraints.md", MEMORY_CONSTRAINTS)
```

### `tests/test_init.py` (modified, +9 tests)

Added `TestInitContextScaffolding` class:
- `test_init_creates_adapters_dir` — adapters/ directory exists
- `test_init_creates_claude_adapter` — adapters/claude.md exists and is non-empty
- `test_init_creates_all_adapter_files` — all 5 adapter files present
- `test_init_creates_templates_dir` — templates/ directory exists
- `test_init_creates_research_template` — templates/research.md exists and non-empty
- `test_init_creates_all_stage_templates` — all 8 stage templates present
- `test_init_creates_memory_dir` — memory/ directory exists
- `test_init_creates_decisions_memory` — memory/decisions.md exists and non-empty
- `test_init_creates_all_memory_files` — all 3 memory files present

### `tests/test_context_assembler.py` (modified, +3 tests)

Added `TestAssembleContextAfterInit` class verifying end-to-end integration:
- `test_adapter_file_included_after_init` — after init, context output uses real claude adapter (not stub text)
- `test_template_included_after_init` — after init, context output includes `minilegion brief` from init stage template
- `test_memory_included_after_init` — after init, context output has `## Memory` section with all 3 scaffold files

### `.planning/milestones/v1.1-ADR-0007.md` (staged)

Confirmed all required sections present:
- `## Context` — 6 structural gaps that motivated v1.1
- `## Decision` — 7-slice v1.1 Portable Kernel table
- `## Consequences` — Positive + Negative subsections
- `## Rejected Alternatives` — 3 rejected approaches
- `## Success Criterion` — 72-hour break + 2-minute resume scenario
- `**Status:** Accepted`

No content gaps found — ADR was written correctly during roadmap planning.

## Integration Smoke Test

```
minilegion init ml-smoke-test
minilegion context claude
```

Output confirmed:
1. ✅ No exception raised
2. ✅ `## Current State` section in stdout
3. ✅ `project-ai/context/claude.md` written
4. ✅ `project-ai/adapters/claude.md` present (non-empty, Claude framing)
5. ✅ `project-ai/templates/init.md` present
6. ✅ `project-ai/memory/decisions.md` present
7. ✅ `## Memory` section in context output (scaffold files read)
8. ✅ `## Adapter Instructions` uses real claude.md content (not stub)

## Test Results

| Metric | Value |
|---|---|
| Baseline tests | 656 |
| New tests added | 12 (9 init + 3 assembler integration) |
| Final test count | 668 |
| Regressions | 0 |
| Test duration | ~23s |

## Requirements Satisfied

| Req | Status | Verification |
|-----|--------|--------------|
| CTX-01 | ✅ (02-01) | `context claude` writes `project-ai/context/claude.md` |
| CTX-02 | ✅ (02-01) | Same command prints block to stdout |
| CTX-03 | ✅ (02-02) | `project-ai/adapters/` has all 5 files after init |
| CTX-04 | ✅ (02-02) | `project-ai/templates/` has 8 stage templates after init |
| CTX-05 | ✅ (02-02) | `project-ai/memory/` has 3 scaffold files after init |
| CTX-06 | ✅ (02-02) | ADR-0007 complete with all required sections |
| CFG-08 | ✅ (02-01) | ContextConfig has max_injection_tokens, lookahead_tasks, warn_threshold |
| CFG-09 | ✅ (02-01) | Omitting context key from config JSON gives identical behavior |

## Commits

| Hash | Description |
|---|---|
| `d3172b1` | feat(02-02): add adapter/template/memory constants and wire into init |
| `ca3c6ce` | feat(02-02): verify and stage ADR-0007; regression gate 668 tests passing |

## Deviations from Plan

None — plan executed exactly as written.

Adapter content defined in plan was transcribed verbatim. All 8 stage templates and 3 memory scaffolds match plan specification. Init wiring follows the exact code pattern specified in the plan.

## Self-Check: PASSED

| Check | Result |
|---|---|
| `minilegion/cli/commands.py` modified | FOUND |
| `tests/test_init.py` extended | FOUND |
| `tests/test_context_assembler.py` extended | FOUND |
| `.planning/milestones/v1.1-ADR-0007.md` staged | FOUND |
| commit `d3172b1` | FOUND |
| commit `ca3c6ce` | FOUND |
| 668 tests passing, 0 failures | VERIFIED |
| Smoke test: all 6 checks pass | VERIFIED |
