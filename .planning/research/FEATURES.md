# Features Research — MiniLegion

**Domain:** LLM-assisted developer workflow / spec-driven CLI protocol tools
**Researched:** 2026-03-09
**Confidence:** MEDIUM-HIGH (based on analysis of Aider, Cline, OpenHands, Devika, GSD, Claude Code, Cursor, and community patterns)

## Competitive Landscape (Context for Feature Decisions)

The LLM-assisted coding tool space in 2026 has split into two camps:

1. **Conversational agents** (Aider, Cline, Claude Code, Cursor): Chat-driven, low ceremony, fast iteration. The user types what they want and the LLM acts. Minimal structured artifacts.
2. **Agentic platforms** (OpenHands, Devin, Devika): Full autonomy — sandboxed environments, browser use, terminal execution, minimal human involvement per step.

**MiniLegion occupies a deliberate third position:** A _protocol-driven workflow_ with mandatory human gates, structured artifacts at every stage, and verifiable state transitions. This is not a competitor to Aider (speed) or OpenHands (autonomy) — it competes on **rigor, auditability, and portability**.

## Table Stakes

Features users expect from _any_ LLM-assisted code tool. Missing = unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Multi-LLM support (adapter pattern)** | Every tool (Aider, Cline, OpenHands) supports 5+ providers. Users refuse lock-in. | Med | OpenAI adapter for MVP; abstract base class makes this table stakes even with one impl. Pattern matters more than breadth at launch. |
| **CLI entrypoint with clear commands** | Aider, Claude Code, and OpenHands CLI all have intuitive command structures. Users expect `pip install && run`. | Low | 8 commands (init/brief/research/design/plan/execute/review/status) is correct. |
| **File creation and editing** | Every tool creates/edits files. Without this, no value delivered. | Med | MiniLegion does this via Builder role producing JSON patches. Structured patches are the correct approach. |
| **Codebase context awareness** | Aider has repo-map (tree-sitter AST). Cline reads file structure + ASTs. OpenHands scans projects. Users expect the tool to "understand" their code. | High | `deep_context.py` scanner addresses this. Critical that it produces usable context without blowing token budgets. |
| **Configuration file** | Every tool has config: Aider (`.aider.conf.yml`), Cline (settings), OpenHands (`config.toml`). Users need to set API keys, model preferences, timeouts. | Low | `minilegion.config.json` is correct. Keep flat and simple for Sprint 1. |
| **Undo / rollback capability** | Aider has `/undo` (git-based). Cline has checkpoints with compare/restore. Users need a safety net. | Med | MiniLegion's state-immutability-on-non-approval IS the undo mechanism. If you reject, nothing changed. This is better than after-the-fact undo. |
| **Clear feedback on what changed** | Aider shows diffs. Cline shows diff views. Users need to see what the AI did. | Low | Dual MD+JSON output serves this — MD is the human-readable diff equivalent. Execution log captures changes. |
| **Error handling with retries** | LLMs produce malformed output. Every tool handles this. | Low | Max 2 retries on JSON parse failure is correct and bounded. |
| **Status / progress visibility** | Users need to know where they are in the process. | Low | `status` command reading `STATE.json` addresses this. |

## Differentiators

Features that set MiniLegion apart. These are NOT found (or not found well) in competing tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Mandatory human approval gates (5 points)** | Cline asks permission per-action (noisy). Aider auto-commits (risky). OpenHands runs autonomously. MiniLegion's 5 explicit gates (brief, research, design, plan, patch) are **the right granularity** — coarse enough to not be annoying, fine enough to catch problems before they cascade. | Med | This is MiniLegion's core differentiator. The gates are at _phase transitions_, not at individual operations. No other tool does this. |
| **Dual output: MD + JSON per stage** | No competitor produces structured machine-parseable artifacts alongside human-readable ones at every pipeline stage. Aider produces code diffs. Cline produces chat logs. OpenHands produces action logs. None produce schema-validated JSON research/design/plan/review artifacts. | Med | This enables downstream automation, CI integration, and audit trails that no competitor offers. |
| **Explicit pipeline stages (brief→research→design→plan→execute→review→archive)** | Most tools collapse everything into "chat → code." Devika has planning but no explicit research/design separation. MiniLegion's pipeline enforces that plans are grounded in research and constrained by design decisions — preventing the #1 failure mode of AI coding (acting on false assumptions). | High | 7 stages is ambitious for Sprint 1 but the architecture doc already accounts for it. The extended pipeline IS the product. |
| **Mechanical scope lock** | No competitor does this. Aider edits whatever it wants. Cline asks permission per file (but doesn't enforce a pre-declared scope). OpenHands operates in a sandbox (different approach). MiniLegion's `files_allowed` → `changed_files` mechanical check is unique and critical for trust. | Med | File-list comparison is unambiguous. This is a trust feature — users can know the AI won't silently modify unexpected files. |
| **Schema-validated LLM output** | Most tools parse LLM output loosely (regex for code blocks, etc.). MiniLegion requires pure JSON validated against schemas. This catches hallucinated fields, missing required data, and structural errors. | Med | JSON-only responses + schema validation is stricter than any competitor. Combined with retry logic, this creates reliable structured output. |
| **Inter-phase coherence checks** | No competitor validates that a plan is consistent with its design, or that a review checks against the design constraints. MiniLegion's research↔design, design↔plan, design↔review checks are unique. | High | This is what "prove the workflow" means. Each phase's output must be consistent with its inputs. Novel feature. |
| **Deterministic Archivist (no LLM)** | Every competitor uses LLMs for everything. MiniLegion's Archivist is purely deterministic — state transitions and decision recording are too important to be probabilistic. | Low | Correct architectural decision. State management must be reliable. |
| **Role-based separation of concerns** | 6 roles with distinct prompts and responsibilities. No competitor has this level of role decomposition. Devika has "agents" but they're not as crisply separated. | Med | Each role gets tailored prompts, reducing prompt bloat and improving output quality through specialization. |
| **File-centric state (no database)** | State lives entirely in `project-ai/` as files. Any tool can read it. Git tracks it. No setup required. This is fundamentally more portable than Aider's git-only history, OpenHands' Docker state, or Devika's SQLite. | Low | This is a design philosophy differentiator. "View the state with `cat`" is a feature. |
| **Bounded revise loop (max 2)** | Most tools loop infinitely (Aider's auto-fix, Cline's retry). MiniLegion caps at 2 revisions then escalates to human. Prevents runaway token spend and infinite loops. | Low | Bounded iteration is a trust and cost feature. |

## Anti-Features (Sprint 1)

Things to deliberately NOT build. Each has a reason grounded in competitive analysis.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **GUI / Web interface** | OpenHands, Devika, and Cursor all have GUIs. Building one is a 3-6 month effort that distracts from the protocol. MiniLegion's value is in the protocol, not the UI. | CLI + file artifacts. Users read MD files in their editor. |
| **IDE integration** | Cline is a VSCode extension. Cursor IS an IDE. This is their turf and a massive engineering effort. | CLI is IDE-agnostic. Users run MiniLegion in a terminal alongside any editor. |
| **Auto-commit to git** | Aider auto-commits every change. This feels magic but removes human control over commit boundaries. | Suggest commits, don't make them (D11 decision). The human decides when to commit. |
| **Browser / web browsing** | Cline and Devika browse the web. This requires Playwright/headless Chrome, adds massive complexity, and is tangential to the "prove the workflow" mission. | External web search is out of scope. Researcher role works with codebase context only in Sprint 1. |
| **Terminal command execution** | Cline and OpenHands execute commands in terminals. This is powerful but introduces security risks and sandbox complexity. | Builder produces JSON patches. The human applies them. No shell execution. |
| **Voice input** | Aider supports voice-to-code. Nice but orthogonal to protocol rigor. | Text-based CLI input only. |
| **Rich TUI / interactive prompts** | Fancy terminal UIs add dependency weight and complexity. | Plain text prompts. `input()` for approval gates. |
| **Parallel multi-builder** | OpenHands scales to 1000s of agents. This is Sprint 3+ at earliest. | Single sequential pipeline. One LLM call at a time. |
| **Model profiles per step** | Using different models for different roles (cheap model for research, expensive for code). Smart optimization but premature. | Single model configured globally in Sprint 1. Per-role engines in config schema but not enforced. |
| **MCP / tool extensibility** | Cline's MCP integration is powerful but requires a protocol server infrastructure. | Fixed tool set. No plugin system. |
| **Session logging / history** | Nice for debugging but not core to proving the pipeline works. | Defer to MVP+. State.json captures current state, not history. |
| **Unit test framework** | Testing the tool itself. Important but not Sprint 1 priority. | Manual testing against the pipeline. Tests in Sprint 2. |
| **Multi-file simultaneous LLM calls** | Sending research + design to LLM in parallel. Optimization, not correctness. | Sequential pipeline. Each stage waits for the previous. |

## Feature Complexity Map

| Complexity | Features |
|------------|----------|
| **Low** | CLI entrypoint, config file, status command, deterministic Archivist, bounded revise loop, error retries, file-centric state |
| **Medium** | Human approval gates, dual MD+JSON output, scope lock enforcement, schema-validated output, role-based prompts, Builder JSON patches, OpenAI adapter, pre-flight checks |
| **High** | Deep context / codebase scanning, inter-phase coherence checks, full 7-stage pipeline orchestration, fast mode (skip stages safely) |

## Dependencies Between Features

```
                    ┌──────────────┐
                    │  CLI + Init  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Config File  │
                    └──────┬───────┘
                           │
                ┌──────────▼──────────┐
                │  OpenAI Adapter     │
                │  (LLM base class)   │
                └──────────┬──────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐     ┌──────▼──────┐    ┌─────▼─────┐
    │ JSON    │     │ Pre-flight  │    │  Deep     │
    │ Schemas │     │ Checks      │    │  Context  │
    └────┬────┘     └──────┬──────┘    └─────┬─────┘
         │                 │                 │
         └────────┬────────┘                 │
                  │                          │
         ┌────────▼────────┐                 │
         │  Role Prompts   │◄────────────────┘
         │  (6 roles)      │
         └────────┬────────┘
                  │
    ┌─────────────┼──────────────────┐
    │             │                  │
┌───▼──┐   ┌─────▼─────┐    ┌───────▼───────┐
│Brief │   │Research    │    │Approval Gates │
│      │   │→Design    │    │(5 points)     │
│      │   │→Plan      │    │               │
│      │   │→Execute   │    │               │
│      │   │→Review    │    │               │
└───┬──┘   └─────┬─────┘    └───────┬───────┘
    │             │                  │
    │      ┌──────▼──────┐           │
    │      │ Scope Lock  │           │
    │      │ Enforcement │           │
    │      └──────┬──────┘           │
    │             │                  │
    └─────────────┼──────────────────┘
                  │
         ┌────────▼────────┐
         │ Coherence       │
         │ Checks          │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Archivist       │
         │ (deterministic) │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ Status Command  │
         └─────────────────┘
```

### Critical Path Dependencies

1. **Config → Adapter → Everything else**: Nothing works without config loading and LLM connection
2. **JSON Schemas → Role Prompts → Pipeline stages**: Schemas must exist before prompts can instruct the LLM to produce schema-compliant output
3. **Pre-flight Checks → Approval Gates**: Pre-flight validates that the previous stage was approved before allowing the next
4. **Deep Context → Researcher role**: The Researcher needs codebase scanning to produce useful output
5. **Scope Lock depends on Plan output**: The Plan defines `files_allowed`; the Builder's output is checked against it
6. **Coherence Checks depend on multiple stages existing**: Can only check research↔design consistency once both artifacts exist
7. **Archivist depends on all stages**: Archives the final state after review approval

### Build Order Implication

Build from the bottom up:
1. **Foundation** (config, adapter, schemas) — unlocks everything
2. **Core pipeline** (brief → plan → execute) — minimum viable workflow
3. **Extended pipeline** (research, design, review) — full rigor
4. **Safety features** (scope lock, coherence checks, approval gates) — trust layer
5. **Convenience** (status, fast mode, dry-run) — usability

## MVP Recommendation

**Prioritize (must ship):**
1. CLI entrypoint with 8 commands (table stakes)
2. OpenAI adapter with abstract base (table stakes + portability foundation)
3. JSON schemas for all artifacts (differentiator foundation)
4. 5 human approval gates (core differentiator)
5. Brief → Plan → Execute → Review pipeline (minimum viable workflow)
6. Scope lock enforcement (trust differentiator)
7. Dual MD+JSON output (differentiator)
8. Deterministic Archivist (reliability)

**High-value additions if time allows:**
- Research + Design stages (extends pipeline to full rigor)
- Inter-phase coherence checks (proves the workflow)
- Deep context scanner (codebase awareness)

**Defer:**
- Fast mode: Requires the full pipeline to exist before you can skip parts of it
- Multi-LLM adapters: OpenAI-first, add others when users ask
- Per-role engine config: Config schema supports it, but enforce single-engine in Sprint 1

## Sources

- Aider GitHub (41.7k stars): https://github.com/Aider-AI/aider — Confidence: HIGH (direct observation)
- Aider docs: https://aider.chat/docs/usage.html — Confidence: HIGH
- Cline GitHub (58.8k stars): https://github.com/cline/cline — Confidence: HIGH (direct observation)
- OpenHands GitHub (68.8k stars): https://github.com/OpenHands/OpenHands — Confidence: HIGH (direct observation)
- Devika GitHub (19.5k stars): https://github.com/stitionai/devika — Confidence: HIGH (direct observation)
- GSD protocol (benchmark target): Known from PROJECT.md context — Confidence: MEDIUM (training data)
- Claude Code, Cursor, Continue features: Confidence: MEDIUM (training data, well-documented tools)
