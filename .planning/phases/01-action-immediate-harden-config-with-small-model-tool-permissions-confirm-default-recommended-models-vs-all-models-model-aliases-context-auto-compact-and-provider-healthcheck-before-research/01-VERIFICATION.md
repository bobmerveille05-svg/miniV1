---
phase: 01-action-immediate-harden-config-with-small-model-tool-permissions-confirm-default-recommended-models-vs-all-models-model-aliases-context-auto-compact-and-provider-healthcheck-before-research
verified: 2026-03-11T12:00:00Z
status: human_needed
score: 7/7 must-haves verified
human_verification:
  - test: "Confirm README.md lines 186-187 do not mislead users about context_auto_compact and provider_healthcheck"
    expected: "The README should reflect that both flags are already active (not 'reserved for later'), since Plan 02 wired them fully"
    why_human: "The doc inaccuracy is minor and non-blocking to code correctness, but a human should decide if the wording should be updated before marking docs complete"
---

# Phase 01: Config Hardening — Verification Report

**Phase Goal:** Harden configuration and pre-research runtime safety so provider/model setup is explicit, validated, and fail-fast before any research-stage LLM work.
**Verified:** 2026-03-11T12:00:00Z
**Status:** human_needed (all automated checks passed; one minor doc wording issue flagged for human review)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Users can configure both primary and small-model defaults without breaking existing config files. | ✓ VERIFIED | `MiniLegionConfig.small_model = "gpt-4o-mini"` with `_normalize_small_model` validator; `load_config()` returns defaults for missing keys — confirmed by `tests/test_config.py` legacy backfill tests |
| 2 | Tool permissions default to `confirm` and reject unsupported values at config-load time. | ✓ VERIFIED | `tool_permissions: Literal["confirm", "allow", "deny"] = "confirm"` in `config.py:228`; `test_load_config_rejects_invalid_tool_permissions` test covers invalid value path |
| 3 | Config CLI reads the configured recommended/full model catalogs and clearly separates the recommended path from the full catalog. | ✓ VERIFIED | `_choose_model()` / `_prompt_model_source()` / `_get_catalog()` in `config_commands.py`; `test_recommended_catalog_is_default_path` and `test_can_switch_to_full_catalog` both pass |
| 4 | Alias input resolves to canonical model IDs before config is written back to disk. | ✓ VERIFIED | `_resolve_model_input()` in `config_commands.py:117-135`; `test_alias_input_persists_canonical_model` and `test_alias_input_updates_to_canonical_model` pass |
| 5 | Research reads `provider_healthcheck` from config and refuses to start when the check is enabled and the configured provider is not ready. | ✓ VERIFIED | `commands.py:328-329` and `pipeline.py:165-166` both gate on `config.provider_healthcheck` before calling `run_provider_healthcheck(config)`; 4 dedicated tests in `TestResearchHealthcheckGate` pass |
| 6 | When `provider_healthcheck` is enabled, the healthcheck runs before preflight, scanner work, prompt rendering, or LLM calls. | ✓ VERIFIED | Ordering confirmed in `commands.py:328-332` (healthcheck → `check_preflight` → `scan_codebase` → `render_prompt` → `validate_with_retry`); `test_healthcheck_called_before_scanner_when_enabled` asserts ordering via call-order list |
| 7 | Oversized scanned context is compacted deterministically when config enables auto-compaction. | ✓ VERIFIED | Compaction at `commands.py:339-348` and `pipeline.py:172-182` — 50,000 char threshold with explicit `[CONTEXT TRUNCATED: ...]` marker; `TestResearchContextCompaction` (3 tests) all pass |

**Score: 7/7 truths verified**

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `minilegion/core/config.py` | Validated config schema with hardening fields and backward-compatible defaults | ✓ VERIFIED (substantive + wired) | All 7 new fields present with typed defaults; `_normalize_small_model` validator; `_default_recommended_models`, `_default_all_models`, `_default_model_aliases` factory functions; 281 lines — no stub |
| `minilegion/cli/config_commands.py` | Interactive provider/model selection helpers that read configured recommended/all catalogs and apply alias resolution | ✓ VERIFIED (substantive + wired) | `_choose_model`, `_prompt_model_source`, `_resolve_model_input`, `_require_catalog` fully implemented; reads `config.recommended_models`, `config.all_models`, `config.model_aliases`; 319 lines |
| `tests/test_config.py` | Regression coverage for new config defaults, validation, and legacy-file loading | ✓ VERIFIED (substantive + wired) | Covers `small_model`, `tool_permissions`, `context_auto_compact`, `provider_healthcheck`, legacy backfill, catalog shape — all pass |
| `tests/test_config_commands.py` | CLI coverage for catalog branching and alias persistence | ✓ VERIFIED (substantive + wired) | `TestConfigInit` + `TestConfigModel` cover recommended, full-catalog, alias, error paths — all 14 tests pass |
| `minilegion/core/provider_health.py` | Reusable provider-readiness checks with actionable failure messages | ✓ VERIFIED (substantive + wired) | `run_provider_healthcheck()`, `_check_ollama()`, `_check_openai_compatible()`, `_require_env_var()` fully implemented; 92 lines |
| `minilegion/cli/commands.py` | Research-stage wiring for config-driven healthcheck ordering and context compaction | ✓ VERIFIED (substantive + wired) | `run_provider_healthcheck` imported and called at line 329; compaction block at lines 339-348; `scan_max_file_size_kb * 1024` at line 140 |
| `minilegion/core/pipeline.py` | Service-layer parity for config-driven research gating and compaction behavior | ✓ VERIFIED (substantive + wired) | `run_provider_healthcheck` imported and called at line 166; compaction block at lines 172-182; `scan_max_file_size_kb * 1024` at line 92 |
| `tests/test_provider_health.py` | Unit coverage for provider health pass/fail branches | ✓ VERIFIED (substantive + wired) | 6 tests covering disabled/enabled pass/fail for openai, openai-compatible, ollama — all pass |
| `tests/test_cli_brief_research.py` | Research command ordering and compaction regression tests | ✓ VERIFIED (substantive + wired) | `TestResearchHealthcheckGate` (4 tests), `TestResearchContextCompaction` (3 tests), `TestScanMaxFileSizeNormalization` (1 test) — all pass; autouse `_noop_healthcheck` fixture on `TestResearchCommand` class prevents leakage |
| `README.md` | User-facing config contract updated | ⚠️ PARTIAL | All 7 new fields documented with JSON examples and field table; BUT lines 186-187 describe `context_auto_compact` and `provider_healthcheck` as "reserved config switch for later research work" when they are **already active and enforced** by Plan 02 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `minilegion/cli/config_commands.py` | `minilegion/core/config.py` | `load_config()`, `model_copy(update=...)`, `model_dump_json()` | ✓ WIRED | Import at line 15; `load_config` called at line 73; `model_copy` at lines 258, 311; `model_dump_json` at lines 265, 312 |
| `tests/test_config_commands.py` | `minilegion/cli/config_commands.py` | Typer `CliRunner` config init/model flows | ✓ WIRED | `runner.invoke(app, ["config", "init"/"model"])` present at lines 51, 141, 217 |
| `minilegion/cli/commands.py` | `minilegion/core/provider_health.py` | `research()` calls `run_provider_healthcheck(config)` after `load_config()` | ✓ WIRED | Import at line 34; call at line 329; ordering: `load_config` (325) → `run_provider_healthcheck` (329) → `check_preflight` (332) |
| `minilegion/cli/commands.py` | `minilegion.core.context_scanner.scan_codebase` | Scanner output compacted before `render_prompt()` when enabled | ✓ WIRED | `scan_codebase` at line 336; compaction block at 339-348; `render_prompt` at 354 — correct ordering |
| `minilegion/core/pipeline.py` | `minilegion/core/provider_health.py` | `run_research()` invokes `run_provider_healthcheck(config)` before preflight or adapter work | ✓ WIRED | Import at line 41; call at line 166; `check_preflight` at 168 — healthcheck runs first |
| `minilegion/core/pipeline.py` | `minilegion/core/context_scanner.py` | `run_research()` compacts scanned context before `render_prompt()` | ✓ WIRED | `scan_codebase` at line 170; compaction at 172-182; `render_prompt` at 186 — correct ordering |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CFG-01 | 01-01 | Add explicit `small_model` config with safe default/fallback behavior | ✓ SATISFIED | `config.py:223`, `_normalize_small_model` validator, `get_small_model()` method; `test_config.py` coverage |
| CFG-02 | 01-01 | Enforce `tool_permissions` with default `confirm` | ✓ SATISFIED | `Literal["confirm", "allow", "deny"] = "confirm"` at `config.py:228`; invalid-value rejection tested |
| CFG-03 | 01-01 | Separate curated `recommended_models` from broader `all_models` | ✓ SATISFIED | `_prompt_model_source()` and `_require_catalog()` in `config_commands.py`; catalog branching tests pass |
| CFG-04 | 01-01 | Resolve `model_aliases` to canonical model IDs before persistence | ✓ SATISFIED | `_resolve_model_input()` resolves alias then validates against `all_models`; alias persistence tests pass |
| CFG-05 | 01-02 | Support config-driven `context_auto_compact` in research flow | ✓ SATISFIED | Compaction in `commands.py:339-348` and `pipeline.py:172-182`; 3 compaction tests pass |
| CFG-06 | 01-02 | Enforce `provider_healthcheck` before research work begins | ✓ SATISFIED | `provider_health.py` module; wired in `commands.py:328-329` and `pipeline.py:165-166`; 6+4 tests pass |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `README.md` | 186-187 | Describes `context_auto_compact` and `provider_healthcheck` as "reserved config switch for **later** research work" | ⚠️ Warning | These features are live as of Plan 02 — the language implies they are stubs, which is incorrect but does not affect code behavior |
| `minilegion/core/pipeline.py` | 89 | Docstring says "or a placeholder message" | ℹ️ Info | Not a code stub — refers to the `"(no existing source files)"` fallback string in the docstring. Accurate. |

---

## Human Verification Required

### 1. README accuracy for `context_auto_compact` and `provider_healthcheck`

**Test:** Read `README.md` lines 186-187
**Expected:** Both fields should be documented as **active** (e.g., "deterministically truncates oversized context before LLM prompt rendering" and "fail-fast readiness check before research begins"), not "reserved for later"
**Why human:** The inaccuracy is in English prose — automated checks confirmed the code is correct and wired. Only a human can decide if the wording should be updated or if the current "reserved" framing is intentionally cautious

---

## Gaps Summary

No blocking gaps. All 7 observable truths are verified, all 6 requirements are satisfied, all key links are wired, and all 60 dedicated tests pass (613 full-suite tests pass).

The only outstanding item is a **minor documentation wording issue** in `README.md` lines 186-187, where `context_auto_compact` and `provider_healthcheck` are described as future/reserved rather than currently active. This does not block the phase goal and does not affect code correctness.

---

_Verified: 2026-03-11T12:00:00Z_
_Verifier: OpenCode (gsd-verifier)_
