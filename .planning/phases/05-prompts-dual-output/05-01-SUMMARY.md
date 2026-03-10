---
phase: 05-prompts-dual-output
plan: 01
subsystem: prompts
tags: [importlib-resources, jinja-style-templates, prompt-engineering, markdown]

# Dependency graph
requires:
  - phase: 02-schemas-validation
    provides: Pydantic schema models that prompt output must conform to
  - phase: 03-llm-adapter
    provides: LLMAdapter.call_for_json() that consumes rendered prompts
provides:
  - 5 role prompt templates (.md) with SYSTEM + USER_TEMPLATE sections
  - load_prompt() function for runtime prompt file loading via importlib.resources
  - render_prompt() function for {{placeholder}} variable injection
  - pyproject.toml package-data config for prompt .md inclusion in wheels
affects: [06-brief-research, 07-design, 08-plan, 09-execute, 10-review-revise]

# Tech tracking
tech-stack:
  added: [importlib.resources]
  patterns: [marker-delimited prompt files, package-data inclusion, regex variable injection]

key-files:
  created:
    - minilegion/prompts/loader.py
    - minilegion/prompts/researcher.md
    - minilegion/prompts/designer.md
    - minilegion/prompts/planner.md
    - minilegion/prompts/builder.md
    - minilegion/prompts/reviewer.md
    - tests/test_prompt_loader.py
  modified:
    - pyproject.toml

key-decisions:
  - "importlib.resources for prompt loading — works in both editable installs and packaged wheels"
  - "<!-- SYSTEM --> and <!-- USER_TEMPLATE --> markers for section splitting — human-readable and grep-friendly"
  - "re.sub with {{placeholder}} syntax — simpler than Jinja2, no extra dependency"
  - "ConfigError raised on missing files, missing markers, and unresolved placeholders"
  - "JSON anchoring at START and END of every system prompt — doubles enforcement"

patterns-established:
  - "Prompt file format: <!-- SYSTEM --> section + <!-- USER_TEMPLATE --> section in .md files"
  - "load_prompt(role) → (system_prompt, user_template) tuple pattern"
  - "render_prompt(template, **vars) → substituted string with unresolved placeholder detection"
  - "Behavioral anchoring per role: explore/design/decompose/build/identify constraints"

requirements-completed: [PRMT-01, PRMT-02, PRMT-03, PRMT-04]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Phase 5 Plan 01: Prompt Templates & Loader Summary

**5 role prompt templates with importlib.resources loader and {{placeholder}} variable injection**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-10T14:45:00Z
- **Completed:** 2026-03-10T16:09:03Z
- **Tasks:** 2 (prompt files + loader, comprehensive test suite)
- **Files modified:** 8

## Accomplishments
- 5 role-specific prompt templates (researcher, designer, planner, builder, reviewer) each with SYSTEM and USER_TEMPLATE sections
- Prompt loader module using importlib.resources for package-portable file loading
- {{placeholder}} variable injection with unresolved placeholder detection
- JSON-only output enforcement with dual anchoring (start + end of every system prompt)
- 34 tests covering all prompt loading, rendering, error paths, JSON anchoring, and behavioral constraints

## Task Commits

Each task was committed atomically:

1. **Task 1: Prompt loader, 5 prompt files, pyproject.toml** - `5c17f0b` (feat)
2. **Task 2: Comprehensive test suite** - included in `5c17f0b` (TDD — tests written alongside implementation)

_Note: Tests were created as part of the TDD cycle within Task 1's commit_

## Files Created/Modified
- `minilegion/prompts/loader.py` - load_prompt() and render_prompt() functions
- `minilegion/prompts/researcher.md` - Researcher role prompt with explore-don't-design constraint
- `minilegion/prompts/designer.md` - Designer role prompt with design-don't-plan constraint
- `minilegion/prompts/planner.md` - Planner role prompt with decompose-don't-design constraint
- `minilegion/prompts/builder.md` - Builder role prompt with build-don't-redesign constraint
- `minilegion/prompts/reviewer.md` - Reviewer role prompt with identify-don't-correct constraint
- `pyproject.toml` - Added [tool.setuptools.package-data] for *.md inclusion
- `tests/test_prompt_loader.py` - 34 tests across 5 test classes

## Decisions Made
- Used `importlib.resources.files()` API (Python 3.9+) instead of `pkg_resources` — modern, fast, supports editable installs
- `re.sub` for placeholder replacement instead of string.Template — cleaner {{var}} syntax, error detection on unresolved vars
- Each prompt file is self-contained and human-readable as a standalone .md file

## Deviations from Plan
None - plan executed as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Prompt loading infrastructure ready for pipeline stages (Phases 6-10)
- All 5 roles can be loaded, rendered with variables, and passed to LLM adapter
- pyproject.toml configured so prompts survive `pip install`

---
*Phase: 05-prompts-dual-output*
*Completed: 2026-03-10*
