# MiniLegion

A Python CLI tool implementing a file-centric, multi-engine, LLM-assisted work protocol. Every task flows through a structured pipeline with human approval gates at each stage.

```
brief → research → design → plan → execute → review → archive
```

## Features

- **Structured pipeline** — 7 stages with enforced transitions, never skippable without explicit flags
- **Human-in-the-loop** — approval gate after every stage; rejection leaves state byte-identical to before
- **Multi-provider LLM** — OpenAI, Anthropic, Google Gemini, Ollama (local), and any OpenAI-compatible endpoint (Groq, Together AI, LM Studio, etc.)
- **Schema-validated output** — all 6 artifact types validated via Pydantic; failed output triggers retry with error feedback
- **Atomic file I/O** — every write uses `write → fsync → os.replace`; interrupted writes never corrupt existing files
- **Coherence checks** — cross-phase validation catches scope drift between research, design, plan, and execution
- **Fast mode** — `--fast` flag skips research and design for quick iterations

## Requirements

- Python 3.10+
- At least one LLM provider API key (or a local Ollama instance)

## Installation

```bash
git clone https://github.com/bobmerveille05-svg/miniV1.git
cd miniV1
pip install -e .
```

Optional provider SDKs:

```bash
pip install anthropic          # for Anthropic Claude
pip install google-genai       # for Google Gemini
# Ollama requires no extra package — uses stdlib urllib
```

## Quick Start

```bash
# 1. Initialize a project
minilegion init my-feature

# 2. Write a brief (text or stdin)
cd my-feature
minilegion brief "Add a dark mode toggle to the settings page"

# 3. Run the full pipeline
minilegion research
minilegion design
minilegion plan
minilegion execute
minilegion review
minilegion archive
```

Each command pauses for your approval before mutating state.

## Configuration

Edit `project-ai/minilegion.config.json` in your project directory:

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key_env": "OPENAI_API_KEY",
  "timeout": 120,
  "max_retries": 2
}
```

### Provider examples

**OpenAI (default)**
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key_env": "OPENAI_API_KEY"
}
```

**Anthropic Claude**
```json
{
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022",
  "api_key_env": "ANTHROPIC_API_KEY"
}
```

**Google Gemini**
```json
{
  "provider": "gemini",
  "model": "gemini-1.5-flash",
  "api_key_env": "GEMINI_API_KEY"
}
```

**Ollama (local)**
```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "base_url": "http://localhost:11434"
}
```

**Groq (OpenAI-compatible)**
```json
{
  "provider": "openai-compatible",
  "model": "llama-3.3-70b-versatile",
  "api_key_env": "GROQ_API_KEY",
  "base_url": "https://api.groq.com/openai/v1"
}
```

**LM Studio (local, no key required)**
```json
{
  "provider": "openai-compatible",
  "model": "local-model",
  "base_url": "http://localhost:1234/v1"
}
```

### Per-role engine assignment

Use different models for different pipeline roles:

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key_env": "OPENAI_API_KEY",
  "engines": {
    "planner": "gpt-4o",
    "builder": "gpt-4o"
  }
}
```

### Scanner limits

Control how much codebase context is scanned:

```json
{
  "scan_max_depth": 5,
  "scan_max_files": 200,
  "scan_max_file_size_kb": 100
}
```

## Commands

| Command | Description |
|---------|-------------|
| `minilegion init <name>` | Create a new project |
| `minilegion status` | Show current stage, approvals, and task progress |
| `minilegion brief <text>` | Write or pipe a project brief |
| `minilegion research` | Scan codebase and generate research artifacts |
| `minilegion design` | Generate architecture decisions |
| `minilegion plan` | Decompose work into tasks |
| `minilegion execute` | Apply patches with per-patch approval |
| `minilegion review` | Review execution against design and conventions |
| `minilegion archive` | Finalize the pipeline cycle |

### Flags

```bash
minilegion brief --stdin                  # read brief from stdin
minilegion plan --fast                    # skip research + design stages
minilegion plan --skip-research-design    # same as --fast
minilegion execute --dry-run              # show what would change, no writes
minilegion execute --task 3               # run only task 3
```

## Project Structure

After `minilegion init my-feature`, the project looks like:

```
my-feature/
└── project-ai/
    ├── minilegion.config.json   # provider, model, limits
    ├── STATE.json               # current stage and approvals
    ├── BRIEF.md                 # your task description
    ├── RESEARCH.json / .md      # codebase analysis
    ├── DESIGN.json / .md        # architecture decisions
    ├── PLAN.json / .md          # task decomposition
    ├── EXECUTION_LOG.json / .md # applied patches
    ├── REVIEW.json / .md        # review verdict
    ├── DECISIONS.md             # archived decisions
    └── prompts/                 # customizable prompt templates
```

All artifacts are saved in both JSON (machine-readable) and Markdown (human-readable) formats.

## Pipeline Details

### Approval gates

Every stage ends with a Y/N prompt. Rejecting at any gate:
- Leaves `STATE.json` byte-identical to before the command ran
- Does not advance the stage
- Exits with code 0 (not an error)

### Revise loop

If `review` produces a `"revise"` verdict, the pipeline automatically re-enters `execute` with corrective actions injected into the builder prompt. The loop stops after 2 iterations and escalates to the user.

### Coherence checks

`archive` runs cross-phase coherence validation:
- Research → Design: recommended files were considered
- Design → Plan: every component has at least 1 task
- Plan → Execute: no out-of-scope files touched
- Execute → Review: verdict consistency

Errors block archival; warnings are reported but allow continuation.

### Fast mode

```bash
minilegion plan --fast
```

Skips research and design stages. The planner receives the directory tree and brief only. Skipped stages are recorded in `STATE.json` so downstream commands don't require the missing artifacts.

## Development

```bash
pip install -e ".[dev]"
pytest
```

All 581 tests pass with no real API calls (fully mocked).

## License

MIT
