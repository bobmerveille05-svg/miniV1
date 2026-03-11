# Phase 1: Action immediate: harden config with small_model, tool_permissions confirm default, recommended_models vs all_models, model_aliases, context_auto_compact, and provider_healthcheck before research - Research

**Researched:** 2026-03-11
**Domain:** MiniLegion config hardening and pre-research safety gates
**Confidence:** HIGH

<user_constraints>
## User Constraints

### Locked Decisions
- Phase scope is config hardening and pre-research runtime safety only.
- Add `small_model` to config as a first-class field.
- `tool_permissions` must default to `confirm`.
- Distinguish curated `recommended_models` from fuller `all_models`.
- Support `model_aliases` that resolve to canonical model IDs.
- Add `context_auto_compact` to control pre-prompt context shrinking.
- Run `provider_healthcheck` before any research-stage scanner or LLM work.
- Requirements in scope: `CFG-01`, `CFG-02`, `CFG-03`, `CFG-04`, `CFG-05`, `CFG-06`.

### OpenCode's Discretion
- Exact field types and validation rules.
- Exact CLI interaction for recommended-vs-all model selection.
- Exact compaction threshold and compaction format.
- Exact provider healthcheck implementation details, as long as it is fast, deterministic, and fail-fast.

### Deferred Ideas (OUT OF SCOPE)
- Broad pipeline-wide healthchecks beyond the `research` stage.
- Dynamic online model catalog fetching.
- Major config migrations or a config file format change.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CFG-01 | Add explicit `small_model` config with safe default/fallback behavior. | Use schema-first config extension in `minilegion/core/config.py`; keep backward-compatible defaults and test via `tests/test_config.py`. |
| CFG-02 | Enforce `tool_permissions` with default `confirm`. | Use typed literal/validator in `MiniLegionConfig`; surface invalid values through `load_config()` error path. |
| CFG-03 | Separate curated `recommended_models` from broader `all_models`. | Keep both catalogs in CLI layer, treat recommended as UX default and all-models as optional expansion path. |
| CFG-04 | Resolve `model_aliases` to canonical model IDs before persistence. | Add deterministic alias resolution utility in `minilegion/cli/config_commands.py`; persist canonical IDs only. |
| CFG-05 | Support config-driven `context_auto_compact` in research flow. | Add deterministic compaction step between `scan_codebase()` and `render_prompt()` in `minilegion/cli/commands.py`. |
| CFG-06 | Enforce `provider_healthcheck` before research work begins. | Add reusable core utility and invoke it immediately after `load_config()` and before preflight/scanner/adapter work. |
</phase_requirements>

## Summary

MiniLegion already has the right architectural seams for this phase: config is centralized in `minilegion/core/config.py`, provider selection is centralized in `minilegion/adapters/factory.py`, interactive setup lives in `minilegion/cli/config_commands.py`, and `research()` is a single linear orchestration point in `minilegion/cli/commands.py`. The safest plan is to extend those seams rather than introduce new ones.

The main planning insight is that this phase is not about new provider capability; it is about making existing capability explicit, validated, and safe before any research-stage LLM work. That means three concrete layers: schema defaults and validation in `MiniLegionConfig`, interactive provider/model UX in `config_commands.py`, and a fast fail-fast runtime gate in `research()` via a new `provider_health.py` helper. Keep everything deterministic and local-first.

There is also one existing config-adjacent bug to account for during planning: both `minilegion/cli/commands.py` and `minilegion/core/pipeline.py` reference `config.scan_max_file_size`, but the config model only defines `scan_max_file_size_kb`. This mismatch should be treated as a known pitfall when adding `context_auto_compact`, because the new work touches the same prompt-budget boundary.

**Primary recommendation:** Extend `MiniLegionConfig` with validated hardening fields, keep model catalogs and alias resolution in the CLI layer, and add a reusable `run_provider_healthcheck(config)` gate that runs in `research()` before preflight, scanning, or adapter setup.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `>=3.10` | Runtime, typing, pathlib | Project baseline from `pyproject.toml` |
| Pydantic | `>=2.12.0` | Config schema, defaults, validation | Existing project-wide schema standard; official docs confirm default `extra='ignore'` and `model_validate_json()` behavior |
| Typer | `>=0.24.0` | Interactive CLI flows | Existing command system and test harness already use Typer |
| pytest | `>=8.0` | Unit and CLI regression coverage | Existing validation strategy is pytest-first |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openai | `>=1.0` | OpenAI and OpenAI-compatible adapter path | For provider runtime checks tied to configured remote providers |
| stdlib `urllib` | Python stdlib | Ollama HTTP probing | For lightweight local health checks without adding dependencies |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic field validation | Manual JSON dict checks | Faster to prototype, but breaks consistency with the rest of MiniLegion |
| Static CLI-only health checks | Adapter instantiation as the only check | Too late; wastes scanner and prompt work before failure |
| Recommended list as the only catalog | Dynamic provider API listing | More current, but adds network dependence and nondeterminism to config flows |

**Installation:**
```bash
pip install -e ".[dev]"
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── core/
│   ├── config.py           # Single source of truth for config fields/defaults
│   ├── provider_health.py  # NEW: deterministic provider readiness checks
│   └── context_scanner.py  # Existing scanner, compacted after scan
├── cli/
│   ├── config_commands.py  # Recommended/all catalog UX + alias resolution
│   └── commands.py         # research() orchestration and gating
└── adapters/
    └── *.py                # Existing provider-specific runtime behavior

tests/
├── test_config.py
├── test_config_commands.py
├── test_provider_health.py
└── test_cli_brief_research.py
```

### Pattern 1: Schema-First Config Hardening
**What:** Put all new config keys in `MiniLegionConfig` with typed defaults and narrow validation.
**When to use:** For any setting that changes runtime safety, CLI behavior, or prompt budgeting.
**Example:**
```python
# Source: D:\test cli\minilegion\core\config.py
from typing import Literal
from pydantic import BaseModel, Field

class MiniLegionConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    small_model: str = "gpt-4o-mini"
    tool_permissions: Literal["confirm", "allow", "deny"] = "confirm"
    recommended_models: dict[str, list[tuple[str, str]]] = Field(default_factory=dict)
    all_models: dict[str, list[tuple[str, str]]] = Field(default_factory=dict)
    model_aliases: dict[str, str] = Field(default_factory=dict)
    context_auto_compact: bool = True
    provider_healthcheck: bool = True
```

### Pattern 2: CLI Catalogs, Core Enforcement
**What:** Keep model browsing and alias UX in `config_commands.py`, but keep validity and runtime readiness in core code.
**When to use:** For any behavior that users interact with during `config init` or `config model` but which also affects runtime.
**Example:**
```python
# Source: D:\test cli\minilegion\cli\config_commands.py
RECOMMENDED_MODELS = {...}
ALL_MODELS = {...}

def resolve_model_alias(model_input: str, aliases: dict[str, str]) -> str:
    return aliases.get(model_input, model_input)
```

### Pattern 3: Pre-Research Fail-Fast Gate
**What:** Run provider healthcheck immediately after `load_config(project_dir.parent)` and before any other research work.
**When to use:** At the start of `research()`; later phases may reuse the helper, but Phase 1 should scope enforcement to research.
**Example:**
```python
# Source: D:\test cli\minilegion\cli\commands.py
config = load_config(project_dir.parent)
run_provider_healthcheck(config)
check_preflight(Stage.RESEARCH, project_dir)
codebase_context = scan_codebase(project_dir, config)
```

### Pattern 4: Deterministic Post-Scan Compaction
**What:** Compact oversize scanner output after scanning, not inside scanner internals.
**When to use:** When `config.context_auto_compact` is enabled and prompt input exceeds a fixed threshold.
**Example:**
```python
def compact_context(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... context auto-compacted ...]"
```

### Anti-Patterns to Avoid
- **Runtime truth in recommended catalog:** recommended is a curated UX list, not canonical provider support.
- **Healthcheck inside adapter call path only:** too late for this phase's fail-fast goal.
- **Compaction inside `scan_codebase()`:** makes scanner output less reusable and harder to test.
- **Custom per-command config parsing:** increases drift from `MiniLegionConfig`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config defaults/validation | Ad-hoc JSON merge logic | Pydantic defaults + validators | Existing standard; official docs confirm JSON validation and extra-key behavior |
| Provider dispatch | New if/else trees in CLI | `minilegion/adapters/factory.py` | Existing single provider map already defines supported providers |
| File persistence | Direct writes | `write_atomic()` | Existing crash-safe write pattern |
| Research retry handling | New retry loop | `validate_with_retry()` | Existing bounded retry + debug behavior should remain unchanged |
| Ollama probing transport | New HTTP client dependency | stdlib `urllib` | Existing Ollama adapter already uses it successfully |

**Key insight:** This phase should compose existing abstractions; it should not invent a second config system, second provider registry, or second research pipeline.

## Common Pitfalls

### Pitfall 1: Breaking Legacy Config Files
**What goes wrong:** Older `minilegion.config.json` files fail to load once new keys are added.
**Why it happens:** New fields are made required or validators assume presence instead of defaults.
**How to avoid:** Give every new field a default and validate semantics, not existence.
**Warning signs:** `load_config()` fails on partial JSON in `tests/test_config.py`.

### Pitfall 2: Invalid Permission Values Slip Through
**What goes wrong:** `tool_permissions` accepts an unsupported string and later logic branches unpredictably.
**Why it happens:** Untyped `str` fields with no validator or literal restriction.
**How to avoid:** Use a literal/validator at schema level and let `load_config()` wrap the validation failure.
**Warning signs:** Config writes succeed but CLI behavior is inconsistent.

### Pitfall 3: Catalog and Alias Logic Drift
**What goes wrong:** `config init` and `config model` resolve aliases or catalogs differently.
**Why it happens:** Separate inline logic in each command.
**How to avoid:** Add one shared selection/alias helper in `minilegion/cli/config_commands.py`.
**Warning signs:** Same alias maps to different values across commands.

### Pitfall 4: Healthcheck Runs Too Late
**What goes wrong:** Research scans files and renders prompts before failing on provider readiness.
**Why it happens:** Healthcheck is inserted near adapter construction instead of immediately after config load.
**How to avoid:** Place the gate before `check_preflight()`, `scan_codebase()`, and prompt rendering.
**Warning signs:** Failing healthcheck tests still show scanner or LLM mocks being called.

### Pitfall 5: Compaction Is Nondeterministic
**What goes wrong:** Research prompts vary unpredictably across runs, making tests brittle.
**Why it happens:** Heuristic summarization or order-dependent trimming.
**How to avoid:** Use deterministic truncation rules and explicit markers.
**Warning signs:** Snapshot-like tests intermittently fail on compacted text.

### Pitfall 6: Existing File-Size Contract Remains Inconsistent
**What goes wrong:** New prompt-budget work hides the fact that current code references `config.scan_max_file_size` while config defines `scan_max_file_size_kb`.
**Why it happens:** Existing mismatch in `minilegion/cli/commands.py` and `minilegion/core/pipeline.py`.
**How to avoid:** Normalize on one field contract during this phase or at minimum add tests that catch the mismatch.
**Warning signs:** Attribute errors or uncapped reads in builder/research-adjacent code.

## Code Examples

Verified patterns from repository and official docs:

### Backward-Compatible JSON Config Loading
```python
# Source: D:\test cli\minilegion\core\config.py
def load_config(project_dir: Path) -> MiniLegionConfig:
    config_path = project_dir / "project-ai" / "minilegion.config.json"
    if not config_path.exists():
        return MiniLegionConfig()

    raw = config_path.read_text(encoding="utf-8")
    return MiniLegionConfig.model_validate_json(raw)
```

### Pydantic Extra-Key Behavior
```python
# Source: https://docs.pydantic.dev/latest/concepts/models/
from pydantic import BaseModel

class Model(BaseModel):
    x: int

model = Model(x=1, y="ignored")
assert model.model_dump() == {"x": 1}
```

### Ollama JSON Mode
```python
# Source: https://github.com/ollama/ollama/blob/main/docs/api.md
payload = {
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Respond using JSON"}],
    "format": "json",
    "stream": False,
}
```

### Existing Research Orchestration Seam
```python
# Source: D:\test cli\minilegion\cli\commands.py
config = load_config(project_dir.parent)
check_preflight(Stage.RESEARCH, project_dir)
codebase_context = scan_codebase(project_dir, config)
system_prompt, user_template = load_prompt("researcher")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Minimal config: provider/model/env/timeout only | Schema-backed config with scanner limits and CLI model setup | v1.0 | Good foundation for adding hardened fields |
| Single recommended model list per provider | Recommended vs all-model split with alias resolution | Phase 1 target | Safer UX, clearer canonical persistence |
| Provider failure on first real adapter call | Pre-research provider health gate | Phase 1 target | Faster feedback and lower wasted work |
| Raw scanner output sent directly to prompt | Config-driven deterministic auto-compaction | Phase 1 target | More predictable prompt budgets |

**Deprecated/outdated:**
- Treating `RECOMMENDED_MODELS` as the whole provider catalog.
- Letting research begin before provider readiness is known.

## Open Questions

1. **Should `recommended_models`, `all_models`, and `model_aliases` live in persisted config or be defaults merged from code?**
   - What we know: The phase explicitly names them as config hardening targets, but current catalogs live in `config_commands.py` constants.
   - What's unclear: Whether users are expected to edit these catalogs manually.
   - Recommendation: Persist them in config with code defaults; CLI should merge defaults when fields are absent for backward compatibility.

2. **How strict should provider healthcheck be?**
   - What we know: The goal says fail-fast before research-stage LLM work.
   - What's unclear: Whether to perform only local config/env checks or also lightweight network probes.
   - Recommendation: Phase 1 should do deterministic local checks for all providers, plus a lightweight local HTTP readiness probe for Ollama only.

3. **What should trigger compaction?**
   - What we know: `context_auto_compact` should protect prompt budgets before research.
   - What's unclear: Exact threshold unit: chars, bytes, or section counts.
   - Recommendation: Use a simple character threshold in Phase 1 because scanner output is text and easy to test deterministically.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=8.0` |
| Config file | `pyproject.toml` |
| Quick run command | `python -m pytest tests/test_config.py tests/test_config_commands.py tests/test_provider_health.py tests/test_cli_brief_research.py -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | `small_model` exists with default/fallback semantics | unit | `python -m pytest tests/test_config.py -k small_model -q` | ❌ Wave 0 |
| CFG-02 | `tool_permissions` defaults to `confirm` and rejects invalid values | unit | `python -m pytest tests/test_config.py -k tool_permissions -q` | ❌ Wave 0 |
| CFG-03 | CLI exposes recommended-vs-all model selection | cli | `python -m pytest tests/test_config_commands.py -k "recommended or all" -q` | ❌ Wave 0 |
| CFG-04 | Aliases resolve to canonical model IDs before save | cli | `python -m pytest tests/test_config_commands.py -k alias -q` | ❌ Wave 0 |
| CFG-05 | Research compacts oversized context when enabled | integration | `python -m pytest tests/test_cli_brief_research.py -k compact -q` | ❌ Wave 0 |
| CFG-06 | Research healthcheck runs before scanner/LLM and fails fast | unit+integration | `python -m pytest tests/test_provider_health.py tests/test_cli_brief_research.py -k healthcheck -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_config.py tests/test_config_commands.py tests/test_provider_health.py tests/test_cli_brief_research.py -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config.py` needs coverage for all new config fields, defaults, and validation failures.
- [ ] `tests/test_config_commands.py` needs coverage for recommended/all catalog branching and alias resolution.
- [ ] `tests/test_provider_health.py` needs to be created for fast provider-readiness unit tests.
- [ ] `tests/test_cli_brief_research.py` needs ordering tests proving healthcheck runs before preflight/scanner/LLM.
- [ ] A targeted regression should cover the `scan_max_file_size` vs `scan_max_file_size_kb` contract mismatch if Phase 1 touches prompt-size logic.

## Sources

### Primary (HIGH confidence)
- Repository: `minilegion/core/config.py` - current config schema and `load_config()` behavior.
- Repository: `minilegion/cli/config_commands.py` - provider/model catalogs and current interactive UX.
- Repository: `minilegion/cli/commands.py` - current `research()` ordering and orchestration seam.
- Repository: `minilegion/adapters/factory.py` - canonical supported-provider map.
- Repository: `minilegion/adapters/openai_adapter.py` - remote provider env requirements.
- Repository: `minilegion/adapters/openai_compatible_adapter.py` - local-vs-remote base URL behavior.
- Repository: `minilegion/adapters/ollama_adapter.py` - default Ollama base URL and `urllib` transport.
- Repository: `minilegion/adapters/gemini_adapter.py` - SDK and env requirements.
- Repository: `minilegion/adapters/anthropic_adapter.py` - SDK and env requirements.
- Repository: `tests/test_config.py`, `tests/test_config_commands.py`, `tests/test_cli_brief_research.py`, `tests/test_adapters.py` - current expected behaviors and test style.
- Official docs: `https://docs.pydantic.dev/latest/concepts/models/` - `model_validate_json()`, default handling, extra-data behavior.
- Official docs: `https://docs.pydantic.dev/latest/api/config/` - `ConfigDict.extra`, strictness, validation configuration.
- Official docs: `https://github.com/ollama/ollama/blob/main/docs/api.md` - `/api/chat`, `format: "json"`, default local endpoint conventions.

### Secondary (MEDIUM confidence)
- `README.md` - current user-facing config contract and provider examples.
- `.planning/ROADMAP.md` - phase goal and in-scope requirement IDs.
- `.planning/PROJECT.md` and `.planning/STATE.md` - milestone context and architecture continuity.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - based on `pyproject.toml`, repository usage, and official Pydantic docs.
- Architecture: HIGH - grounded in existing orchestration seams and repository patterns.
- Pitfalls: HIGH - based on concrete code paths, existing tests, and one verified config-field mismatch.

**Research date:** 2026-03-11
**Valid until:** 2026-04-10
