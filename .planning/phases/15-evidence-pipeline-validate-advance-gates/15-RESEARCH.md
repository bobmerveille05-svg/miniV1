# Phase 15: Evidence Pipeline + Validate/Advance Gates - Research

**Researched:** 2026-03-12
**Domain:** Validation evidence contracts, stage progression gates, and workflow strictness config
**Confidence:** MEDIUM

<user_constraints>
## User Constraints

No phase-level `*-CONTEXT.md` exists for Phase 15, so there are no locked decisions to copy verbatim.

### Locked Decisions
- None provided.

### OpenCode's Discretion
- Full implementation approach for `validate <step>` and `advance` semantics.
- Exact strictness behavior for `workflow.strict_mode` and `workflow.require_validation` beyond baseline requirement text.

### Deferred Ideas (OUT OF SCOPE)
- Rollback/doctor behavior changes (Phase 17).
- Research brainstorm mode (Phase 16).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EVD-01 | `project-ai/evidence/` exists and each `validate <step>` writes `*.validation.json` with required fields | Defines canonical evidence schema, file naming, and atomic write path. |
| EVD-02 | Every validate invocation creates/overwrites evidence file | Recommends overwrite semantics and deterministic filename per step. |
| EVD-03 | Evidence is machine-readable for downstream `advance`/`doctor` | Recommends typed model + JSON file contract and reusable read helper. |
| VAD-01 | Stage-producing commands update artifacts but do not auto-advance stage | Identifies all current auto-advance sites and prescribes decoupling pattern. |
| VAD-02 | `minilegion validate <step>` validates artifact, writes evidence, reports pass/fail, no stage change | Defines command behavior, accepted steps, status output, and exit codes. |
| VAD-03 | `minilegion advance` requires passing current-step evidence, then updates state and appends history event | Defines gate algorithm and integration with `StateMachine` + `append_event`. |
| VAD-04 | `minilegion advance` fails non-zero with clear message when no passing evidence | Prescribes refusal conditions and UX wording conventions. |
| CFG-07 | Config schema accepts `workflow.strict_mode` + `workflow.require_validation` with defaults true | Defines config model additions and compatibility-safe defaults. |
</phase_requirements>

## Summary

Phase 15 is a behavior-semantics refactor, not just a new command addition. The current pipeline commands (`brief`, `research`, `design`, `plan`, `execute`, `review`) still auto-transition `STATE.json` after approval, which directly violates VAD-01. The codebase already has strong primitives you should reuse: `StateMachine` for legal transitions, `append_event()` for append-only audit events, `write_atomic()` for durable JSON writes, and Typer + pytest patterns for deterministic CLI behavior.

The safest architecture is to add a dedicated evidence model and I/O helper (parallel to `core/history.py`), then split responsibilities: stage commands produce artifacts and approvals only; `validate <step>` reads current artifacts and writes `project-ai/evidence/<step>.validation.json`; `advance` is the sole stage mutator and reads evidence as a gate. This preserves auditability, makes progression machine-checkable, and creates a clean integration seam for Phase 17 doctor checks.

Config scope is the biggest hidden risk. `CFG-07` requires optional, non-breaking config fields with defaults true. Existing config loading already supports backward-compatible defaults via Pydantic model defaults, so implement strictness controls as an additive `WorkflowConfig` submodel. Keep behavior deterministic: missing config key must behave exactly like explicit `true` for both `strict_mode` and `require_validation`.

**Primary recommendation:** Implement a first-class evidence subsystem (`core/evidence.py` + schema), then decouple stage commands from state transitions, and finalize with `advance` as the only progression path guarded by evidence + workflow config.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.10 | Runtime, filesystem orchestration, command execution | Existing project baseline (`pyproject.toml`). |
| Typer | >=0.24.0 | `validate`/`advance` CLI commands and exit semantics | Existing command surface and test harness conventions. |
| Pydantic | >=2.12.0 | Evidence schema + config extension modeling | Already canonical for all artifacts and config models. |
| pytest | >=8.0 | Unit + CLI integration verification | Existing repo-wide validation framework. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `pathlib` | built-in | Evidence file pathing and stage-to-file mapping | Reading/writing `project-ai/evidence/*.validation.json`. |
| stdlib `json` | built-in | Stable JSON payload serialization | Evidence persistence + fixture generation in tests. |
| existing `write_atomic()` | local utility | Atomic evidence writes | Every evidence write and overwrite path. |
| existing `append_event()` | local utility | Advance audit trail emission | Every successful `advance`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Filesystem JSON evidence bundles | Store in `STATE.json` metadata | Simpler short-term but breaks machine-readable artifact boundary and pollutes state. |
| Reuse approval flags as gate source | Build `advance` gate from approvals only | Fails EVD-03 requirement; approvals do not encode validator/tool/date/checks. |
| Implicit validation inside `advance` | Auto-run checks at `advance` time | Violates validate/advance separation and blocks reusable evidence querying by doctor. |

**Installation:**
```bash
pip install -e .[dev]
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── core/
│   ├── evidence.py        # new: evidence schema + read/write helpers
│   ├── config.py          # workflow config extension (CFG-07)
│   └── state.py           # reuse Stage + StateMachine transitions
├── cli/
│   └── commands.py        # add validate/advance; remove auto-advance from stage commands
└── schemas/
    └── *.schema.json      # regenerate if evidence schema is added to registry

tests/
├── test_evidence.py             # new: evidence contract/read-write tests
├── test_cli_validate_advance.py # new: validate/advance command behavior
├── test_cli*.py                 # updates for no auto-advance semantics
└── test_config.py               # CFG-07 default + partial override coverage
```

### Pattern 1: Evidence as a First-Class Artifact
**What:** Introduce a typed evidence model and helper functions for write/read by step.
**When to use:** Every `validate <step>` invocation and every `advance` gate check.
**Example:**
```python
# Source: project pattern from core/history.py + REQUIREMENTS EVD-01
class ValidationEvidence(BaseModel):
    step: str
    status: Literal["pass", "fail"]
    checks_passed: list[str] = Field(default_factory=list)
    validator: str
    tool_used: str = "minilegion"
    date: str
    notes: str = ""
```

### Pattern 2: Single Stage Mutator (`advance`)
**What:** Only `advance` mutates `state.current_stage` forward.
**When to use:** All progression from init->brief->...->archive.
**Example:**
```python
# Source: minilegion/core/state.py FORWARD_TRANSITIONS + commands event helper
current = Stage(state.current_stage)
target = FORWARD_TRANSITIONS[current]
sm.transition(target)
state.current_stage = target.value
append_event(project_dir, HistoryEvent(...))
save_state(state, project_dir / "STATE.json")
```

### Pattern 3: Validate-Then-Write (No Stage Mutation)
**What:** `validate <step>` evaluates artifact presence/coherence and always writes evidence for that step.
**When to use:** Manual user validation loop before `advance`.
**Example:**
```python
# Source: EVD-02 contract
result = run_step_checks(step, project_dir, state)
write_evidence(project_dir, step, result)  # overwrite same <step>.validation.json
raise typer.Exit(code=0 if result.status == "pass" else 1)
```

### Anti-Patterns to Avoid
- **Dual truth for progression:** do not keep auto-transition logic in stage commands after adding `advance`.
- **Evidence inferred from approvals:** approval flags are not evidence bundles and cannot satisfy EVD-01/03.
- **Appending evidence filenames with sequence numbers:** requirement implies per-step overwrite semantics (`brief.validation.json`).
- **Config branching with implicit defaults in command code only:** defaults belong in `MiniLegionConfig` model to satisfy non-breaking CFG-07.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file persistence | ad hoc open/write logic in command handlers | `write_atomic()` | Existing reliability contract already used by state/history. |
| Transition validation | custom next-stage if/else chain in multiple places | `StateMachine` + `FORWARD_TRANSITIONS` | Centralizes legal transition semantics and avoids drift. |
| Artifact schema validation | loose dict checks in command functions | Pydantic models + registry patterns | Consistent with all current machine-readable artifacts. |
| CLI parsing tests | subprocess-based brittle assertions | `typer.testing.CliRunner` | Existing suite style with stable monkeypatch patterns. |

**Key insight:** Evidence + advance is a control-plane feature; reliability comes from reusing existing state/history/config primitives, not inventing parallel mechanisms.

## Common Pitfalls

### Pitfall 1: Partial decoupling (VAD-01 still violated)
**What goes wrong:** Some stage commands stop advancing, others still mutate state.
**Why it happens:** Transition logic is duplicated in each command function today.
**How to avoid:** Remove all per-stage `sm.transition(...)` + `state.current_stage = ...` writes except rollback paths that are intentionally backward.
**Warning signs:** Tests still asserting `current_stage` changed immediately after running `brief`/`research`/etc.

### Pitfall 2: Gate checks stale or wrong step
**What goes wrong:** `advance` reads the wrong evidence file (e.g., target stage instead of current stage).
**Why it happens:** Confusing “current stage” vs “next stage” semantics.
**How to avoid:** Gate against evidence for `state.current_stage` artifact completion before moving to the next stage.
**Warning signs:** `advance` fails despite passing validate on current step, or advances without validating the current step.

### Pitfall 3: CFG-07 breaks older configs
**What goes wrong:** Existing `minilegion.config.json` without `workflow` fails validation.
**Why it happens:** Added required config fields without model defaults.
**How to avoid:** Add `WorkflowConfig` with defaults true and `workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)`.
**Warning signs:** `load_config(...)` raises `ConfigError` on old test fixtures.

### Pitfall 4: Evidence schema drift from tests/registry
**What goes wrong:** New evidence model exists but registry/schema tests become inconsistent.
**Why it happens:** Schema registry and generated `minilegion/schemas/*.schema.json` not updated together.
**How to avoid:** If evidence is added to registry, update tests and regenerate schema files in the same change.
**Warning signs:** `tests/test_registry.py` or `tests/test_json_schemas.py` failures.

## Code Examples

Verified patterns from this repo:

### Append-only history event after lifecycle action
```python
# Source: minilegion/cli/commands.py
append_event(
    project_dir,
    HistoryEvent(
        event_type="plan",
        stage=state.current_stage,
        timestamp=datetime.now().isoformat(),
        actor="system",
        tool_used="minilegion",
        notes="Plan completed and approved",
    ),
)
```

### Atomic JSON write contract
```python
# Source: minilegion/core/file_io.py
write_atomic(path, json.dumps(payload, indent=2))
```

### Config backward-compatible defaulting
```python
# Source: minilegion/core/config.py pattern
class MiniLegionConfig(BaseModel):
    context: ContextConfig = Field(default_factory=ContextConfig)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stage command both creates artifact and advances state | Decouple artifact generation from progression via validate + advance | Planned in v1.1 Phase 15 | Enables re-validation loops and deterministic progression gates. |
| Approval booleans implicitly represent readiness | Machine-readable per-step evidence bundles represent validation state | Planned in v1.1 Phase 15 | Allows downstream commands to query status without rerunning checks. |
| Config has no workflow strictness toggles | `workflow.strict_mode` + `workflow.require_validation` defaults true | Planned in v1.1 Phase 15 | Restores explicit strictness controls without breaking existing configs. |

**Deprecated/outdated:**
- Auto-advancing `current_stage` inside stage-producing commands is now legacy behavior and must be removed for VAD compliance.

## Open Questions

1. **Exact semantics of `workflow.strict_mode` beyond `require_validation`**
   - What we know: CFG-07 requires field acceptance with default true.
   - What's unclear: Whether strict mode should also enforce step-name matching, artifact freshness checks, or only command refusal style.
   - Recommendation: Keep strict_mode focused on hard gate behavior and precise erroring; treat richer policy checks as follow-up.

2. **What checks `validate <step>` performs per stage in Phase 15**
   - What we know: EVD/VAD require pass/fail evidence and no state mutation.
   - What's unclear: Minimal check set per step (existence-only vs schema + coherence checks).
   - Recommendation: Start with deterministic artifact presence + schema validation checks; include check names in `checks_passed` for auditability.

3. **How to handle `validate` for `init` and `archive` stages**
   - What we know: Requirements list stage-producing commands from brief->review.
   - What's unclear: Whether command should support all `Stage` values or a subset.
   - Recommendation: Restrict to stages that have verifiable artifacts in this phase and return clear unsupported-step errors.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/test_evidence.py tests/test_cli_validate_advance.py tests/test_config.py -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVD-01 | Validate writes evidence file with required contract fields | unit | `python -m pytest tests/test_evidence.py::TestEvidenceWrite -q` | ❌ Wave 0 |
| EVD-02 | Re-validating same step overwrites `<step>.validation.json` | unit | `python -m pytest tests/test_evidence.py::TestEvidenceOverwrite -q` | ❌ Wave 0 |
| EVD-03 | Evidence read path is machine-consumable for `advance` | unit + CLI | `python -m pytest tests/test_evidence.py::TestEvidenceRead tests/test_cli_validate_advance.py::TestAdvance -q` | ❌ Wave 0 |
| VAD-01 | Stage-producing commands no longer mutate `current_stage` | CLI integration | `python -m pytest tests/test_cli_brief_research.py tests/test_cli_design.py tests/test_cli_plan.py tests/test_cli_execute.py tests/test_cli_review.py -q` | ✅ (needs updates) |
| VAD-02 | `validate <step>` returns pass/fail and writes evidence without stage change | CLI integration | `python -m pytest tests/test_cli_validate_advance.py::TestValidate -q` | ❌ Wave 0 |
| VAD-03 | `advance` requires passing evidence then advances + appends history event | CLI integration | `python -m pytest tests/test_cli_validate_advance.py::TestAdvancePass -q` | ❌ Wave 0 |
| VAD-04 | `advance` exits non-zero with clear message when evidence missing/failing | CLI integration | `python -m pytest tests/test_cli_validate_advance.py::TestAdvanceReject -q` | ❌ Wave 0 |
| CFG-07 | `workflow.strict_mode` and `workflow.require_validation` are optional with defaults true | unit | `python -m pytest tests/test_config.py::TestWorkflowConfig -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_evidence.py tests/test_cli_validate_advance.py -q`
- **Per wave merge:** `python -m pytest tests/test_evidence.py tests/test_cli_validate_advance.py tests/test_config.py tests/test_cli_brief_research.py tests/test_cli_design.py tests/test_cli_plan.py tests/test_cli_execute.py tests/test_cli_review.py -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_evidence.py` - evidence model contract, overwrite semantics, read helper behavior
- [ ] `tests/test_cli_validate_advance.py` - command registration, validate pass/fail, advance gate behavior
- [ ] `tests/test_config.py` - add `TestWorkflowConfig` for CFG-07 defaults and partial overrides
- [ ] Update `tests/test_cli.py` command registration list to include `validate` and `advance`
- [ ] Update stage command tests that currently assert immediate state advancement after approval

## Sources

### Primary (HIGH confidence)
- `D:\test cli\.planning\REQUIREMENTS.md` - EVD/VAD/CFG requirement contracts
- `D:\test cli\.planning\ROADMAP.md` - phase goal, plan split, and success criteria
- `D:\test cli\.planning\v1.1-MILESTONE-AUDIT.md` - concrete gap statements this phase must close
- `D:\test cli\minilegion\cli\commands.py` - current command behavior and auto-advance coupling
- `D:\test cli\minilegion\core\state.py` - transition model and forward stage mapping
- `D:\test cli\minilegion\core\history.py` - append-only event write/read patterns
- `D:\test cli\minilegion\core\config.py` - existing config defaulting and compatibility approach
- `D:\test cli\minilegion\core\file_io.py` - atomic write contract
- `D:\test cli\tests\test_cli.py` and stage-specific CLI tests - expected command/testing style and required updates
- `D:\test cli\tests\test_config.py` - config regression and defaulting verification conventions
- `D:\test cli\minilegion\schemas\generate.py` + `D:\test cli\tests\test_json_schemas.py` - schema registry/file coupling constraints

### Secondary (MEDIUM confidence)
- None needed; project-local evidence was sufficient for planning-level decisions.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - fully grounded in `pyproject.toml` and current runtime/test usage.
- Architecture: MEDIUM - requirements are clear, but strict-mode behavioral depth is not fully specified.
- Pitfalls: HIGH - directly derived from present command coupling and existing test expectations.

**Research date:** 2026-03-12
**Valid until:** 2026-04-11
