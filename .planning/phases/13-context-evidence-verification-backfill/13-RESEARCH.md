# Phase 13: Context Evidence + Verification Backfill - Research

**Researched:** 2026-03-11
**Domain:** MiniLegion context assembly evidence backfill + context completeness wiring
**Confidence:** MEDIUM

## User Constraints

### Locked Decisions
No `*-CONTEXT.md` file exists for this phase, so no locked user decisions were provided.

### OpenCode's Discretion
- Choose the concrete verification/backfill mechanism for Phase 2 requirement evidence.
- Choose how to wire `context.lookahead_tasks` and compact context behavior into the context assembly path.

### Deferred Ideas (OUT OF SCOPE)
None specified for this phase.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CTX-01 | `context <tool>` assembles portable block including compact plan and writes `project-ai/context/<tool>.md` | Current implementation writes file + sections, but does not consume `lookahead_tasks` and does not produce compact plan section; add deterministic plan lookahead extraction + tests + verification evidence.
| CTX-02 | `context <tool>` prints assembled context to stdout | Already implemented and tested; backfill explicit requirement mapping in verification doc with test evidence.
| CTX-03 | Adapter definition files exist in `project-ai/adapters/` | Already scaffolded by `init`; backfill requirement evidence with adapter file existence tests and smoke output proof.
| CTX-04 | Per-stage templates in `project-ai/templates/` | Already scaffolded; backfill evidence from init/template tests and context output inclusion checks.
| CTX-05 | Memory files created and injected | Already scaffolded/injected; backfill evidence from init + assembler tests.
| CTX-06 | ADR-0007 exists with required fields | ADR exists; backfill requirement mapping with section-level verification references.
| CFG-08 | Config accepts context fields including `lookahead_tasks` | Schema exists, but `lookahead_tasks` is unused in assembler path; wire field consumption and test it.
| CFG-09 | New config fields have documented defaults and omitted fields match defaults | Runtime default behavior is tested; add/confirm docs for context defaults and tie to verification table.
</phase_requirements>

## Summary

Phase 13 is primarily a traceability-and-integration repair phase, not a greenfield feature phase. The v1.1 audit marks all CTX/CFG requirements as orphaned because Phase 2 lacks a phase-level `02-VERIFICATION.md` with requirement IDs, even though much of the implementation and tests already exist. The highest leverage outcome is to restore auditable requirement evidence for CTX-01..06 and CFG-08/09 using a single canonical verification artifact that maps each requirement to concrete code paths and passing tests.

There is also one real functional gap to close: `context.lookahead_tasks` exists in config but is never consumed by the context assembly path. `assemble_context()` currently builds sections for state/artifact/template/memory/adapter, but no compact plan/lookahead section is emitted. This is the exact status->context completeness break called out by the milestone audit.

The plan should therefore split execution into two tracks: (1) evidence backfill for already-implemented CTX features, and (2) targeted context completeness implementation for `lookahead_tasks` + compact plan behavior, with deterministic output and tests. Keep changes additive and aligned with existing patterns (pure assembler, CLI owns writes, atomic file writes, graceful degradation).

**Primary recommendation:** Treat Phase 13 as a dual deliverable: produce a machine-auditable Phase 2 verification document and implement deterministic compact-plan lookahead wiring in `assemble_context()` backed by focused tests.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.10 | Runtime + CLI implementation | Existing project baseline in `pyproject.toml`; all pipeline code is Python.
| Typer | >=0.24.0 | CLI command surface (`minilegion ...`) | Already used across all commands; existing tests use `CliRunner`.
| Pydantic | >=2.12.0 | Config/state/schema validation | Current source of truth for config and artifact contracts.
| pytest | >=8.0 | Automated verification | Existing test infrastructure and command patterns already in place.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `pathlib` + atomic writes | built-in | Safe filesystem operations | Always for context output and scaffold writes.
| `typer.testing.CliRunner` | Typer testing helper | CLI behavior tests | For `context` stdout/file and `init` scaffolding checks.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One phase verification file with requirement table | Spread evidence across summary notes only | Fails current audit model; IDs remain hard to prove automatically.
| Deterministic compact plan from `PLAN.json` + execution state | Heuristic/freeform summarization | Harder to test and audit; less reproducible.

**Installation:**
```bash
pip install -e .[dev]
```

## Architecture Patterns

### Recommended Project Structure
```
.planning/
├── REQUIREMENTS.md                              # requirement source of truth
├── v1.1-MILESTONE-AUDIT.md                      # gap findings and affected flows
└── phases/
    ├── 02-context-adapters/
    │   └── 02-VERIFICATION.md                   # backfilled requirement evidence
    └── 13-context-evidence-verification-backfill/
        ├── 13-RESEARCH.md
        └── 13-PLAN*.md / 13-VERIFICATION.md

minilegion/
├── core/context_assembler.py                    # pure context composition logic
├── core/config.py                               # ContextConfig contract
└── cli/commands.py                              # context command writes + stdout

tests/
├── test_context_assembler.py                    # context completeness tests
├── test_init.py                                 # adapters/templates/memory scaffolding tests
└── test_config.py                               # CFG-08/CFG-09 defaults + parsing
```

### Pattern 1: Pure Assembler + CLI-Owned I/O
**What:** Keep `assemble_context()` pure (string composition), and keep file output in CLI command via `write_atomic()`.
**When to use:** Any context payload changes (new sections, compaction rules, lookahead extraction).
**Example:**
```python
# Source: minilegion/core/context_assembler.py + minilegion/cli/commands.py
block = assemble_context(tool, project_dir, config)
write_atomic(project_dir / "context" / f"{tool}.md", block)
typer.echo(block)
```

### Pattern 2: Graceful Degradation for Optional Context Inputs
**What:** Missing adapters/templates/memory/plan should never crash context assembly.
**When to use:** Lookahead/compact-plan wiring where `PLAN.json` or execution artifacts may be absent.
**Example:**
```python
# Source: minilegion/core/context_assembler.py
if template_path.exists():
    ...
else:
    parts.append(f"## Stage Template\n\n_No template defined for stage {current_stage}._\n")
```

### Pattern 3: Requirement-ID-First Verification Tables
**What:** Verification docs must include explicit requirement IDs and evidence rows.
**When to use:** Backfilling orphaned Phase 2 evidence so audits can parse CTX/CFG coverage.
**Example:**
```markdown
| Requirement | Status | Evidence |
|-------------|--------|----------|
| CTX-01 | ✅ | tests/test_context_assembler.py::... |
```

### Anti-Patterns to Avoid
- **Evidence in prose only:** A narrative summary without a requirement-ID table is not audit-proof.
- **Config-only completion claims:** Defining `lookahead_tasks` in schema without runtime consumption leaves CTX-01 incomplete.
- **Non-deterministic compaction:** Freeform truncation/summarization without stable rules produces flaky tests and unverifiable outputs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI file writes | ad hoc open/write logic in command | `write_atomic()` | Existing project safety contract for crash-safe writes.
| Config parsing/default merges | custom JSON merge logic | `MiniLegionConfig` + `ContextConfig` | Already validated and tested for backward compatibility.
| CLI integration harness | custom subprocess wrappers | `typer.testing.CliRunner` | Faster, stable, already used in this codebase.
| Plan schema parsing | dict indexing everywhere | `PlanSchema` / existing schema models | Centralized validation prevents shape drift.

**Key insight:** Most Phase 13 risk is not implementation complexity; it is evidence and determinism drift. Reuse existing typed contracts and test harnesses to keep proof auditable.

## Common Pitfalls

### Pitfall 1: Closing code gap without closing audit gap
**What goes wrong:** `lookahead_tasks` gets wired, but CTX/CFG IDs remain absent from verification tables.
**Why it happens:** Treating code completion and requirement evidence as separate optional tasks.
**How to avoid:** Make `02-VERIFICATION.md` backfill a first-class deliverable with one row per required ID.
**Warning signs:** Audit still reports "orphaned" despite passing tests.

### Pitfall 2: Negative claims from stale files only
**What goes wrong:** Assuming a feature is missing because old summary docs omit it.
**Why it happens:** Not cross-checking code + tests + audit report together.
**How to avoid:** Use 3-source proof per requirement (implementation path, test, verification table).
**Warning signs:** Conflicts between roadmap status, summaries, and audit output.

### Pitfall 3: Token/character compaction ambiguity
**What goes wrong:** New compact-plan behavior mixes token semantics with char truncation inconsistently.
**Why it happens:** `max_injection_tokens` is currently enforced as char length in assembler.
**How to avoid:** Preserve current char-based deterministic approach unless a dedicated tokenization change is scoped.
**Warning signs:** Fragile tests around length thresholds.

### Pitfall 4: Breaking old projects lacking context scaffolding
**What goes wrong:** Context command fails when adapters/templates/memory are absent.
**Why it happens:** Assuming all projects were initialized post-Phase 2.
**How to avoid:** Keep graceful fallback behavior for missing optional files.
**Warning signs:** `minilegion context` exits non-zero on older projects.

## Code Examples

Verified patterns from project sources:

### Context command write + stdout contract (CTX-01/02)
```python
# Source: minilegion/cli/commands.py:1266
project_dir = find_project_dir()
config = load_config(project_dir.parent)
block = assemble_context(tool, project_dir, config)
write_atomic(project_dir / "context" / f"{tool}.md", block)
typer.echo(block)
```

### Config defaults and backward compatibility (CFG-08/09)
```python
# Source: minilegion/core/config.py:218
class ContextConfig(BaseModel):
    max_injection_tokens: int = 3000
    lookahead_tasks: int = 2
    warn_threshold: float = 0.7

class MiniLegionConfig(BaseModel):
    context: ContextConfig = Field(default_factory=ContextConfig)
```

### Existing compaction pattern to mirror for context completeness
```python
# Source: minilegion/cli/commands.py:482
_CONTEXT_COMPACT_THRESHOLD = 50_000
if config.context_auto_compact and len(codebase_context) > _CONTEXT_COMPACT_THRESHOLD:
    codebase_context = codebase_context[:_CONTEXT_COMPACT_THRESHOLD] + "...marker..."
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 2 marked "complete" via plan summaries only | v1.1 audit requires requirement-ID verification evidence | 2026-03-11 audit | Summary-only proof is insufficient; backfill needed.
| Context schema includes `lookahead_tasks` only | Runtime context assembly does not consume it | Phase 2 implementation | CTX-01 completeness gap in status->context flow.
| Research flow has explicit deterministic compaction gate | Context flow has artifact truncation + warn threshold but no compact-plan section | Phase 1 + Phase 2 | Behavior inconsistency across context producers.

**Deprecated/outdated:**
- "Phase 2 is fully verified" as a milestone claim is outdated under the current strict 3-source audit standard.

## Open Questions

1. **Exact compact-plan source for lookahead section**
   - What we know: `lookahead_tasks` exists; `PLAN.json` and `EXECUTION_LOG.json` schemas exist; no current assembler usage.
   - What's unclear: Whether lookahead should be derived from pending `PLAN.json.tasks`, from `state.completed_tasks`, or both.
   - Recommendation: Use pending `PLAN.json.tasks` filtered by executed task IDs when available; fallback to top N planned tasks.

2. **CFG-09 documentation location requirement**
   - What we know: Defaults are in code and behavior tests; README currently does not document `context.*` fields.
   - What's unclear: Whether requirement expects README-level docs specifically.
   - Recommendation: Add context defaults to user-facing config docs and cite exact section in verification evidence.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/test_context_assembler.py tests/test_config.py tests/test_init.py -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CTX-01 | Context includes complete portable payload including compact plan/lookahead | unit + CLI integration | `python -m pytest tests/test_context_assembler.py -q` | ✅ (needs new assertions) |
| CTX-02 | `context <tool>` prints output to stdout | CLI integration | `python -m pytest tests/test_context_assembler.py -q` | ✅ |
| CTX-03 | Adapter files scaffolded | integration | `python -m pytest tests/test_init.py -q` | ✅ |
| CTX-04 | Stage templates scaffolded | integration | `python -m pytest tests/test_init.py -q` | ✅ |
| CTX-05 | Memory files scaffolded and injected | unit + integration | `python -m pytest tests/test_init.py tests/test_context_assembler.py -q` | ✅ |
| CTX-06 | ADR-0007 contains required sections | manual/doc check | `python -m pytest tests/ -x -q` (plus doc inspection) | ✅ (doc exists) |
| CFG-08 | `context.*` fields accepted by schema and consumed by runtime | unit | `python -m pytest tests/test_config.py tests/test_context_assembler.py -q` | ✅ (runtime usage gap) |
| CFG-09 | Defaults apply when omitted and are documented | unit + doc check | `python -m pytest tests/test_config.py -q` (plus doc inspection) | ✅ (doc gap likely) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_context_assembler.py tests/test_config.py -q`
- **Per wave merge:** `python -m pytest tests/test_context_assembler.py tests/test_config.py tests/test_init.py -q`
- **Phase gate:** `python -m pytest tests/ -x -q` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_context_assembler.py` - add lookahead/compact-plan behavior tests tied to `context.lookahead_tasks`
- [ ] `.planning/phases/02-context-adapters/02-VERIFICATION.md` - add requirement-ID evidence table for CTX-01..06, CFG-08..09
- [ ] README context config docs - add `context.max_injection_tokens`, `context.lookahead_tasks`, `context.warn_threshold` defaults and semantics for CFG-09 evidence

## Sources

### Primary (HIGH confidence)
- `D:\test cli\.planning\REQUIREMENTS.md` - CTX/CFG requirement definitions and Phase 13 traceability mapping
- `D:\test cli\.planning\ROADMAP.md` - Phase 13 scope, dependency, and plan intents
- `D:\test cli\.planning\v1.1-MILESTONE-AUDIT.md` - orphaned evidence findings and status->context flow break
- `D:\test cli\minilegion\core\context_assembler.py` - current context assembly behavior and missing lookahead usage
- `D:\test cli\minilegion\core\config.py` - `ContextConfig` defaults and schema contract
- `D:\test cli\minilegion\cli\commands.py` - `context` command write/stdout path and research compaction reference behavior
- `D:\test cli\tests\test_context_assembler.py` - existing CTX behavior coverage
- `D:\test cli\tests\test_init.py` - adapter/template/memory scaffolding coverage
- `D:\test cli\tests\test_config.py` - CFG-08/09 behavior coverage
- `D:\test cli\pyproject.toml` - test framework and dependency baseline

### Secondary (MEDIUM confidence)
- `D:\test cli\.planning\phases\02-context-adapters\02-01-SUMMARY.md` - implementation decisions and prior test counts
- `D:\test cli\.planning\phases\02-context-adapters\02-02-SUMMARY.md` - scaffold behavior summary and requirement claims

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - directly derived from `pyproject.toml` and active code/tests
- Architecture: MEDIUM - patterns are clear in codebase, but compact-plan semantics require a final design choice
- Pitfalls: HIGH - directly confirmed by milestone audit findings and current implementation gaps

**Research date:** 2026-03-11
**Valid until:** 2026-04-10
