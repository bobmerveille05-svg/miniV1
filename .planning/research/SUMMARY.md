# Research Summary: MiniLegion

**Domain:** LLM-orchestration CLI workflow protocol
**Researched:** 2026-03-09
**Overall confidence:** HIGH

## Executive Summary

MiniLegion is a file-centric, multi-engine, LLM-assisted work protocol implementing a structured pipeline (brief > research > design > plan > execute > review > archive) with human approval gates. The architecture research reveals that this type of tool is best structured as a 4-layer system: Protocol (prompts + schemas) > Orchestrator (CLI + state machine + guardrails) > LLM Adapters (abstract interface) > Repo (filesystem I/O).

The Python ecosystem has mature, stable tooling for every component needed. Typer (CLI, built on Click), Pydantic (validation + schema definition), and the OpenAI Python SDK are all production-grade — just 3 production dependencies. The state machine is simple enough to implement with Python's built-in Enum + a dict transition table — no external state machine library is needed. The most critical architectural decision is enforcing the "state unchanged if not approved" invariant, which requires computing new state as Python objects and only writing to disk after approval.

Real-world LLM CLI tools like Aider demonstrate that flat project layouts (not src/), adapter patterns for multi-LLM support, and separation of prompts from orchestration logic are proven patterns. MiniLegion's 6-role system with dual output (MD + JSON) is more structured than most existing tools, making the guardrails and validation layers especially important.

The build order should follow dependency chains: state representation first, then guardrails/validation (safety before LLM calls), then the adapter layer, then prompts, and finally the CLI orchestrator that wires everything together.

## Key Findings

**Stack:** Python + Typer (CLI) + Pydantic (validation + schemas) + openai SDK (LLM) — 3 production dependencies, zero unnecessary ones
**Architecture:** 4-layer with 8 components. State machine via Enum + dict transition table. Pipeline stages follow a uniform 6-step flow.
**Critical pitfall:** State mutation before approval. Must compute state as Python objects, write only on approval.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation** - State enums, transition table, file I/O, config loading, exceptions
   - Addresses: STATE.json management, config file, state invariant
   - Avoids: Building anything that depends on state before state is defined

2. **Safety Layer** - Guardrails, JSON validation, schemas, approval gates
   - Addresses: Pre-flight checks, JSON schemas, scope lock, retry logic, approval gates
   - Avoids: Letting LLM output through without validation

3. **LLM Integration** - Adapter ABC + OpenAI concrete implementation
   - Addresses: OpenAI adapter, abstract base, runtime portability
   - Avoids: Coupling orchestrator to specific LLM provider

4. **Protocol Layer** - Prompt templates for all 6 roles
   - Addresses: 6 roles, dual output format
   - Avoids: Prompt drift from schema definitions

5. **Assembly** - Orchestrator, CLI commands, run.py entrypoint
   - Addresses: CLI entrypoint with 8 commands, pipeline execution
   - Avoids: Building the compositor before components exist

6. **Extended Features** - Deep context, fast mode, archivist
   - Addresses: Deep context module, fast mode, deterministic archivist
   - Avoids: Scope creep in core pipeline

**Phase ordering rationale:**
- State must exist before guardrails can check it
- Guardrails and validation must exist before LLM output flows through
- Adapter must exist before prompts can be tested end-to-end
- Prompts must exist before orchestrator can compose the pipeline
- CLI is pure routing — depends on everything, nothing depends on it

**Research flags for phases:**
- Phase 3 (LLM Integration): Standard pattern, unlikely to need research
- Phase 4 (Protocol): May need deeper research on prompt engineering for structured JSON output
- Phase 6 (Deep Context): Likely needs research on Python AST/tree-sitter for codebase scanning

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified current, production-grade (Typer, Pydantic, openai SDK) |
| Features | HIGH | PROJECT.md is comprehensive; feature set is well-defined |
| Architecture | HIGH | Patterns verified across real-world tools (Aider, OpenAI SDK) |
| Pitfalls | MEDIUM | Based on domain patterns + training knowledge; LLM JSON reliability varies by model |

## Gaps to Address

- Prompt engineering patterns for reliable JSON output (phase-specific research needed)
- Deep context module design — tree-sitter vs AST vs regex for Python codebase scanning
- Markdown generation from JSON — template approach vs LLM-generated in Sprint 1
- Inter-phase coherence checks — exact comparison logic TBD during design
