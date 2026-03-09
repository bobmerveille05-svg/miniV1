# Pitfalls Research — MiniLegion

**Domain:** LLM orchestration pipeline / AI-assisted coding workflow protocol (Python)
**Researched:** 2026-03-09
**Confidence:** HIGH (domain pitfalls from direct build experience with systems of this type; confirmed against OpenAI Structured Outputs docs, jsonschema library behavior, MetaGPT paper, Lilian Weng's LLM Agent survey, and first-principles analysis of the PROJECT.md architecture)

---

## Critical Pitfalls (show-stoppers)

These cause rewrites, broken pipelines, or completely undermine the safety model.

---

### C1: Schema-Valid but Semantically Corrupt JSON ("Hallucinated Correctness")

**What goes wrong:**
The LLM produces JSON that passes `jsonschema.validate()` perfectly but contains semantically wrong content that silently propagates downstream. Classic examples specific to MiniLegion:

- `PLAN.json` has `"files_allowed": ["src/foo.py"]` but the plan steps actually describe touching `src/bar.py` — schema valid, scope lock bypassed at the data level
- `EXECUTION_LOG.json` lists `"status": "success"` with an empty `"patches"` array — schema valid, builder silently did nothing
- `REVIEW.json` has `"verdict": "approved"` with `"issues": ["Critical: design violated"]` — contradictory fields both valid by schema
- `DESIGN.json` references a `"component"` name that never appears in `RESEARCH.json` — cross-artifact coherence broken

**Why it happens:**
JSON Schema validates *structure* and *types*, not *semantic consistency*. The model satisfies token constraints (correct keys, correct types) while the actual values are plausible-sounding fabrications. OpenAI's Structured Outputs guarantees schema conformance, not truthfulness. (Source: OpenAI Structured Outputs docs — "ensures the model will always generate responses that adhere to your supplied JSON schema" — nothing about semantic correctness.)

**Consequences:**
- Scope lock appears enforced but is semantically bypassed
- STATE.json records approvals for artifacts that are factually empty or contradictory
- Inter-phase coherence checks (research↔design, design↔plan) become meaningless if the schemas are too permissive
- Trust in the pipeline breaks when a user discovers a "passing" artifact is garbage

**Prevention:**
1. **Semantic cross-validators** (not schema validators) — post-schema checks that verify:
   - `files_allowed` in PLAN.json is a subset of `files_scanned` in RESEARCH.json
   - Every `component` referenced in PLAN.json appears in DESIGN.json's `components` array
   - `EXECUTION_LOG.json` `status == "success"` requires `patches` array to be non-empty
   - `REVIEW.json` `verdict == "approved"` is incompatible with `issues` array containing severity ≥ "critical"
2. Add a `"reasoning"` or `"confidence"` field to each artifact schema — forces the LLM to justify decisions, exposing when it's filling fields vacuously
3. Display artifact diffs to humans at approval gates; never show just "schema valid ✓"

**Detection (warning signs):**
- LLM produces JSON on the first attempt with no retries — suspiciously easy
- `files_allowed` list is identical across different tasks with different scopes
- Approval is given quickly without human actually reading the artifact

**Phase address:** Core schemas + pre-flight validation layer (Sprint 1, any phase touching schema design)

---

### C2: STATE.json Corruption on Partial Failure

**What goes wrong:**
The orchestrator crashes or is interrupted between writing a new artifact file and updating `STATE.json`. Or the orchestrator updates `STATE.json` first, then the LLM call fails — now state claims a phase is complete when its artifact doesn't exist or is truncated.

Specific scenarios for MiniLegion:
- `RESEARCH.md` written, then `RESEARCH.json` write fails midway → STATE updated to `research_complete: true` → Planner reads corrupt/missing RESEARCH.json
- Human approves design, STATE updated, then process crashes before writing DECISIONS.md → STATE and files are desynchronized
- Retry logic runs, writes a second valid JSON file, but the first partial write was already registered in STATE

**Why it happens:**
File I/O is not transactional. Python's `open(f, 'w')` creates-then-writes; a crash mid-write leaves a zero-byte or partial file. Without atomic write semantics, any multi-step artifact write followed by state update is vulnerable. The project's own constraint ("state unchanged if output not approved") requires extremely careful implementation — it's easy to accidentally flip STATE first.

**Consequences:**
- Subsequent stages get fed empty/partial context → LLM produces garbage output
- Pre-flight checks pass ("RESEARCH.json exists") but the content is truncated
- Pipeline becomes impossible to resume without manual STATE repair
- Trust in "state only transitions on approval" collapses if partial writes occur

**Prevention:**
1. **Atomic file writes** — always write to `<file>.tmp`, verify the write, then `os.rename()` (atomic on POSIX; near-atomic on Windows NTFS for same-volume moves)
2. **Write-then-validate-then-update-STATE** order, never the reverse
3. **Artifact integrity checksums** — store file hash in STATE alongside completion flags; pre-flight checks verify hash, not just file existence
4. **Recovery mode** — on startup, scan for `.tmp` files and truncated artifacts, emit a clear error message with repair instructions rather than silently proceeding

**Detection (warning signs):**
- `.tmp` files appearing in `project-ai/` directory
- STATE says `research_complete: true` but RESEARCH.json is 0 bytes or missing
- Pre-flight passes but LLM output is wildly off-base (suggests bad context injection)

**Phase address:** Archivist implementation + all file-write code in every role (Sprint 1 foundation)

---

### C3: Scope Lock Bypass via Path Normalization Mismatch

**What goes wrong:**
The Builder includes a file in `EXECUTION_LOG.json` as `touched_files: ["./src/foo.py"]`, but the mechanical scope check compares against `files_allowed: ["src/foo.py"]` — `./src/foo.py` ≠ `src/foo.py` as raw strings, so the check passes when it shouldn't (or fails when it should pass). Variants:

- Absolute vs. relative paths: `/project/src/foo.py` vs `src/foo.py`
- Windows vs. POSIX separators: `src\foo.py` vs `src/foo.py`
- Trailing slash: `src/dir/` vs `src/dir`
- Symlink resolution: `src/utils/../foo.py` vs `src/foo.py`
- Case sensitivity on case-insensitive filesystems (Windows): `src/Foo.py` vs `src/foo.py`

**Why it happens:**
String comparison is the most obvious implementation for scope checking, but file paths have many canonical forms. The LLM may use a different convention than the schema expects.

**Consequences:**
- Builder touches files outside scope — the entire mechanical scope lock fails at its one job
- Or: Builder is blocked from touching legitimate files — pipeline stalls with confusing errors

**Prevention:**
1. **Normalize all paths before comparison**: `os.path.normpath(os.path.relpath(path, project_root))` applied to both `files_allowed` and `touched_files` before the set comparison
2. **Store canonical paths in schemas** — all schemas enforce `"pattern": "^[a-z0-9/_.-]+$"` (no `./`, no `\`, no `..`) with explicit normalization at write time
3. **Test the scope lock with adversarial inputs** — include path normalization edge cases in the test suite

**Detection (warning signs):**
- Scope lock consistently rejects valid paths the Builder is trying to touch
- The LLM produces paths starting with `./` in execution logs
- Windows-specific test failures where path separators differ

**Phase address:** Scope lock implementation (Sprint 1, execute command)

---

### C4: Inter-Phase Coherence Drift ("Telephone Effect")

**What goes wrong:**
Each LLM call receives only its immediate predecessor's artifact as context. By the time execution happens, the PLAN.json may contradict DESIGN.json, which itself loosely interpreted RESEARCH.json. No single stage is obviously wrong, but the cumulative drift makes the output irrelevant to the original brief.

Specific drift vectors for MiniLegion's 7-stage pipeline:
- Researcher identifies 5 key files; Designer only references 3; Planner only plans changes to 1
- Designer invents a component not suggested by Researcher; Planner builds it; Reviewer approves because they only see design↔execution, not research↔design drift
- Brief specifies "add authentication"; by the execution stage, the plan is adding a logging middleware

**Why it happens:**
LLMs are stateless between calls. Each role only sees what it's given. The PROJECT.md mentions "inter-phase coherence checks (research↔design, design↔plan, design↔review)" but if these are implemented as separate LLM calls or simple text comparisons, the LLM performing the coherence check can itself hallucinate a positive result.

**Consequences:**
- The execution artifact doesn't match the brief — the pipeline produced the wrong thing rigorously
- Humans approve each stage locally correct, but the full pipeline output is wrong
- Reviewer validates against design but not brief — final product is design-compliant but brief-violating

**Prevention:**
1. **Brief injection at every stage** — every LLM prompt receives the original `BRIEF.md` content, not just its immediate predecessor
2. **Mechanical coherence checks, not LLM coherence checks** — check for shared identifiers (component names, file paths, function names) appearing across artifacts programmatically; flag missing cross-references for human review
3. **Structured ID linking** — require `DESIGN.json` to reference `research_ids` (IDs from RESEARCH.json findings) and `PLAN.json` to reference `design_component_ids`, enabling mechanical traceability

**Detection (warning signs):**
- PLAN.json `files_allowed` list is completely different from RESEARCH.json `files_scanned`
- Design component names do not appear anywhere in plan step descriptions
- Review verdict is "approved" but reviewer's `design_references` list is empty

**Phase address:** Prompt engineering for all roles (Sprint 1) + coherence check implementation

---

## Major Pitfalls (quality killers)

These degrade reliability, user trust, and maintainability without necessarily causing catastrophic failure.

---

### M1: Approval Fatigue Turning Gates into Rubber Stamps

**What goes wrong:**
MiniLegion has 5 approval gates (brief, research, design, plan, patch). Each gate presents the human with a large Markdown artifact to read and approve. After the first 2-3 tasks, users learn the pattern: artifacts look plausible, the pipeline has been reliable, so they approve without reading. The gates become a "press Y to continue" mechanic that adds latency without adding safety.

**Why it happens:**
Approval UX that requires reading long artifacts is cognitively expensive. Humans are loss-averse: the cost of reading is certain, the benefit of catching a bad artifact is uncertain. Once the pipeline has been "reliable enough," humans rationally reduce review depth.

**Consequences:**
- The human safety guarantee evaporates — scope violations, semantic corruption, and coherence drift all pass through
- The 5-gate pipeline becomes slower than a no-gate pipeline with no safety benefit
- Users start using `--fast` mode to skip gates entirely, defeating the protocol's purpose

**Prevention:**
1. **Diff-focused approval UI** — don't show the full artifact; show only what changed from the previous version or what the LLM specifically claims to be doing ("Builder says it will touch: X, Y, Z — confirm?")
2. **High-signal summary injection** — before each approval gate, emit a 3-line summary of the artifact's key claims (not a full display), letting the human spot-check the summary rather than read everything
3. **Escalation triggers** — if the artifact contains anomalies flagged by semantic validators (C1), display them prominently at the gate rather than burying them in the full artifact
4. **Never combine approval with "looks fine" prompts** — the prompt should surface specific risk signals: "Builder claims to touch 7 files; 2 are outside research scope — approve?"

**Detection (warning signs):**
- Average approval time per gate drops below 5 seconds
- Users explicitly ask "can I just auto-approve?"
- Semantic violations are being approved without comment

**Phase address:** Approval gate UX (Sprint 1, human-facing output design)

---

### M2: LLM Markdown Wrapper Pollution in "Pure JSON" Responses

**What goes wrong:**
Despite instructions to return "pure JSON — no markdown wrappers," LLMs reliably produce:
```
```json
{ "key": "value" }
```
```
or add preamble text: `"Here is the JSON output:\n\n{ ... }"` — especially after a retry when the model is trying to be "helpful." The retry logic strips wrappers correctly once, but the second retry produces a different wrapper format, and the naive strip logic fails.

**Why it happens:**
LLMs are trained on enormous amounts of documentation, tutorials, and chat logs where JSON is presented in markdown code blocks. The "pure JSON" instruction fights deep training priors. This is especially common when:
- The LLM is explaining what it's doing (adds natural language prefix)
- The response is very long (model "resets" to markdown mid-generation)
- Temperature > 0 causes non-deterministic formatting choices

**Consequences:**
- `json.loads()` raises `JSONDecodeError`, triggering retries
- After 2 retries with the same wrapper format, the pipeline fails with an unhelpful error
- Debug logs are littered with JSON parse errors making real errors harder to spot

**Prevention:**
1. **Defensive extraction before parse** — always apply a wrapper-stripping step before `json.loads()`:
   ```python
   # Strip ```json...``` or ``` ``` wrappers
   text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.MULTILINE)
   text = re.sub(r'\n?```\s*$', '', text.strip(), flags=re.MULTILINE)
   # Strip leading natural language
   match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
   if match: text = match.group(0)
   ```
2. **Use OpenAI's `response_format: {type: "json_object"}` or Structured Outputs** — forces valid JSON at the API level, eliminating most wrapper issues for the OpenAI adapter
3. **Log all raw responses before stripping** — so failures can be diagnosed

**Detection (warning signs):**
- High rate of `json.loads()` exceptions in the first try (before retries)
- Parse errors clustered around specific prompt templates (those not using `json_object` mode)
- Retry count consistently hitting 1 on every call (wrapper stripped once, always works on retry)

**Phase address:** All LLM adapter `call()` implementations + JSON parsing utilities (Sprint 1, adapter layer)

---

### M3: Adapter Abstraction Leakage

**What goes wrong:**
The OpenAI adapter is built first, and its specific behaviors bleed into the orchestrator code:
- Response parsing assumes OpenAI's `choices[0].message.content` structure
- Timeout handling assumes OpenAI's specific `openai.Timeout` exception class
- Token counting uses OpenAI's `tiktoken` library hardcoded in orchestrator logic
- Retry logic is written to handle OpenAI's `RateLimitError` specifically
- Config uses OpenAI-specific field names like `"model": "gpt-4o"` in ways the base class doesn't abstract

When a second adapter (Anthropic, local Ollama, etc.) is added, the orchestrator code needs surgery to become truly adapter-agnostic.

**Why it happens:**
MVP pressure. "It works with OpenAI, ship it." The abstract base class is defined but the orchestrator calls into adapter-specific behavior without noticing.

**Consequences:**
- The "runtime-independent" promise is false — adding any new adapter requires touching orchestrator code
- The base.py contract is incomplete — it defines the happy path but not error types, retry signals, or metadata
- Technical debt compounds: each new OpenAI-specific behavior added in Sprint 1 is a future breaking change

**Prevention:**
1. **Define the full adapter contract in base.py from the start**, including:
   - Return type: `AdapterResponse(content: str, tokens_used: int, finish_reason: str)`
   - Exception hierarchy: `AdapterError`, `AdapterRateLimitError`, `AdapterTimeoutError` — adapter-specific exceptions converted to these before leaving the adapter
   - No adapter-specific types should appear in orchestrator code
2. **Adapter contract test**: write a `test_adapter_contract.py` that exercises every method of `base.py` against both a mock and the real OpenAI adapter — any leakage fails the contract test
3. **Config isolation**: `minilegion.config.json` per-role engine settings should use provider-agnostic model identifiers or a mapping layer — orchestrator never sees `"gpt-4o"` directly

**Detection (warning signs):**
- `from openai import ...` appearing in `orchestrator/` or `core/` (not in `adapters/openai.py`)
- `except openai.RateLimitError` in non-adapter code
- `tiktoken` imported outside the adapter layer

**Phase address:** Adapter base class definition (Sprint 1 foundation); verify before implementing second adapter

---

### M4: Infinite Revise Loop Disguised as Bounded

**What goes wrong:**
The project specifies "max 2 revise iterations, then escalate." But the revise counter is tracked in transient state (Python variable, not persisted to STATE.json). If the process is restarted after a failure during a revise cycle, the counter resets to 0 — the "bounded" loop becomes unbounded across restarts. Additionally:
- The "escalate to human" path has no defined behavior — what does escalation look like? What does the human do? If it's undefined, the code throws an exception and the user has no recovery path
- Revise count per task is not stored in STATE.json, so the Archivist can't verify the loop was respected

**Why it happens:**
Revise loop bounds are easy to implement for the happy path (simple counter), and the failure mode (restarts, crashes) is only discovered during integration testing.

**Consequences:**
- Runaway LLM calls consuming tokens when the model consistently fails to produce valid output
- No human recovery path when escalation triggers
- Pipeline hangs or crashes with no actionable message

**Prevention:**
1. **Persist revise count to STATE.json** — `"revise_count": {"design": 1, "plan": 0}` — updated atomically on each revise attempt
2. **Escalation path must be concrete** — when max revisions hit: write a `BLOCKED.md` artifact with the last artifact + failure reason + suggested human action, update STATE to `"blocked": true`, exit cleanly with a non-zero return code and clear message
3. **Retry and revise are distinct** — retry (JSON parse failure, max 2) and revise (semantic failure, max 2) must have separate counters and separate escalation behaviors

**Detection (warning signs):**
- Same LLM stage running more than twice in a single session
- No `revise_count` field in STATE.json
- Escalation path raises `NotImplementedError`

**Phase address:** Revise loop implementation (Sprint 1, all roles that can loop)

---

### M5: Deep Context Module Producing Oversized Prompts

**What goes wrong:**
`core/deep_context.py` scans the codebase to build context for the Researcher. For large repos (or repos with generated files, `node_modules`, binary assets, build artifacts), this produces a context payload too large to fit in the LLM's context window. Symptoms:
- OpenAI API returns a `context_length_exceeded` error
- Or worse: the API silently truncates the context, and the LLM produces research findings about only the last N files it saw, without signaling that it missed earlier files

**Why it happens:**
Deep scanning without filtering produces unbounded output. `project-ai/` itself grows over time — each phase adds `.md` and `.json` artifacts, which then get scanned in subsequent tasks, creating a feedback loop.

**Consequences:**
- Researcher produces incomplete or wrong findings (undetected context truncation)
- API errors block the pipeline with no clear recovery path
- The feedback loop makes the problem worse with each task

**Prevention:**
1. **Hard context budget in deep_context.py** — calculate estimated tokens before the LLM call; if budget exceeded, prioritize by file recency and relevance, log what was excluded
2. **Exclude `project-ai/` from deep scans** — MiniLegion's own artifacts should never be scanned as codebase context (they're not the codebase being modified)
3. **Configurable exclude patterns** in `minilegion.config.json` — `"scan_exclude": ["*.lock", "node_modules/", "dist/", ".git/"]`
4. **Surface token count at research stage** — display to human before the LLM call so they can abort if unexpected

**Detection (warning signs):**
- `context_length_exceeded` errors from the OpenAI adapter
- RESEARCH.json `files_scanned` count is significantly lower than actual codebase file count
- Research findings only reference files added recently (truncation artifact)

**Phase address:** `core/deep_context.py` implementation (Sprint 1, research command)

---

## Minor Pitfalls (debt accumulators)

These create maintainability problems and slow development velocity over time.

---

### N1: Schema Version Lock-In

**What goes wrong:**
RESEARCH.json, PLAN.json, etc. are written without a `"schema_version"` field. After Sprint 1, a field is added (or renamed) in a schema. Existing `project-ai/` directories from previous tasks now contain artifacts with the old schema. Pre-flight checks fail on old directories with confusing errors ("required field 'new_field' missing").

**Prevention:**
- Add `"schema_version": "1.0"` to every artifact schema from day one
- Pre-flight checks should include a schema version gate with a clear migration message, not a raw ValidationError

**Phase address:** Schema design (Sprint 1 start)

---

### N2: `NO_ADD.md` Contract Creep via "Refinements"

**What goes wrong:**
A team member adds "just a small improvement" to a Sprint 1 feature that's technically within scope but expands it beyond the 24-element contract. Each individual change seems reasonable; collectively they expand scope by 30%, delay completion, and undermine the benchmark test (comparing against GSD at 30 days).

**Why it happens:**
"Refinement" is cognitively distinct from "addition" — it feels like fixing what's there, not adding something new. The NO_ADD.md contract needs to explicitly cover refinements to existing features, not just new features.

**Prevention:**
- `NO_ADD.md` must explicitly cover: no new parameters, no new behaviors on existing commands, no new validation rules beyond those already specified
- Any change to Sprint 1 requirements requires explicit decision record in DECISIONS.md with a rationale
- Keep a "deferred" list actively maintained — every idea that arises goes to deferred, not into the sprint

**Phase address:** Sprint 1 governance (ongoing)

---

### N3: Config File Undocumented Defaults

**What goes wrong:**
`minilegion.config.json` has many fields with defaults assumed by the code but not written in the config. When users create a minimal config, they get unexpected behavior from assumed defaults. When the code is read later, it's unclear what the "real" defaults are.

**Prevention:**
- Ship a complete `minilegion.config.example.json` with every field documented and defaulted
- Use a config dataclass/Pydantic model with explicit defaults — never rely on "if key missing, use X" scattered across the codebase

**Phase address:** Config implementation (Sprint 1)

---

### N4: Dry-Run Not Verifying Scope Lock

**What goes wrong:**
The `--dry-run` flag for the execute command shows what would be done but skips the mechanical scope lock check. Users run dry-run to verify safety, then run for real — but the scope lock check only runs in the real execution, finding a violation the user didn't see in dry-run. The dry-run gave false safety assurance.

**Prevention:**
- Dry-run must run all validation (including scope lock check, pre-flight, schema validation) and only skip the actual file writes
- Emit a clear "DRY RUN: would write X, Y, Z — WITHIN SCOPE ✓" message per planned change

**Phase address:** Execute command dry-run implementation (Sprint 1)

---

### N5: State File Encoding/Locking on Windows

**What goes wrong:**
MiniLegion runs on developer machines which may be Windows. Python's default file encoding (CP1252 on Windows) differs from UTF-8. If any artifact contains non-ASCII characters (code comments, user-provided brief text, non-English content), STATE.json writes will either silently corrupt data or raise `UnicodeEncodeError`.

Additionally, Windows file locking prevents atomic rename in some scenarios, breaking the atomic-write strategy from C2.

**Prevention:**
- All file opens must use `open(f, 'w', encoding='utf-8')`; add a project-wide lint rule
- For Windows atomic writes: use `tempfile.NamedTemporaryFile(delete=False)`, write, close, then `os.replace()` (which is atomic on Windows for same-drive moves, unlike `os.rename()` which may fail if dest exists)

**Phase address:** All file I/O utilities (Sprint 1 foundation)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| JSON schema design | Schemas too permissive → C1 silent corruption | Add semantic cross-validators beyond jsonschema; add `"reasoning"` fields |
| Archivist implementation | Partial write + STATE update mismatch → C2 corruption | Atomic writes; write-verify-then-update-STATE order; checksums in STATE |
| Scope lock (execute) | Path normalization mismatch → C3 bypass | `os.path.normpath` + `os.path.relpath` before all comparisons; canonical path enforcement in schema |
| Prompt design (all roles) | Brief context drift → C4 telephone effect | Inject BRIEF.md into every role's prompt; mechanical ID traceability across artifacts |
| Approval gate UX | Approval fatigue → M1 rubber stamp | Diff-focused display; anomaly escalation at gate; 3-line summaries |
| LLM adapter `call()` | Markdown wrappers → M2 parse failures | Defensive extraction always; use `json_object` mode on OpenAI; log raw responses |
| Adapter base class | OpenAI leakage → M3 non-portability | Define full contract (return types, exception hierarchy) in base.py before writing OpenAI adapter |
| Revise loop | Non-persistent counter → M4 unbounded loop | Persist revise counts to STATE.json; define concrete escalation path |
| `deep_context.py` | Context window overflow → M5 silent truncation | Hard token budget; exclude `project-ai/`; configurable scan excludes |
| Schema versioning | Schema evolution breaks old dirs → N1 | `schema_version` field from day one |
| Sprint scope | Refinement creep → N2 | NO_ADD.md covers refinements, not just additions |
| Dry-run | False safety signal → N4 | Dry-run runs all validation, only skips writes |
| File I/O on Windows | Encoding + locking issues → N5 | `encoding='utf-8'` everywhere; `os.replace()` for atomic moves |

---

## Sources

- OpenAI Structured Outputs documentation (https://platform.openai.com/docs/guides/structured-outputs) — confirmed: Structured Outputs guarantees schema adherence, NOT semantic correctness. MEDIUM-HIGH confidence.
- python-jsonschema documentation (https://python-jsonschema.readthedocs.io/en/stable/validate/) — confirmed: `jsonschema.validate()` validates structure/types, format checkers optional, no semantic validation. HIGH confidence.
- Lilian Weng, "LLM Powered Autonomous Agents" (https://lilianweng.github.io/posts/2023-06-23-agent/) — confirmed: "reliability of model outputs is questionable, as LLMs may make formatting errors" and context window limitation as primary LLM agent challenge. HIGH confidence (authoritative survey).
- MetaGPT paper (arXiv:2308.00352) — confirmed: "cascading hallucinations caused by naively chaining LLMs" — inter-phase coherence is the primary failure mode in multi-role LLM pipelines. HIGH confidence.
- MiniLegion PROJECT.md — primary source for MiniLegion-specific architecture decisions, constraints, and scope. HIGH confidence.
- Python `os.replace()` docs — confirmed: atomic on same-drive Windows moves. HIGH confidence.
- Domain expertise: pitfalls C1-C4 and M1-M5 derived from direct analysis of the PROJECT.md architecture combined with known LLM orchestration failure patterns. MEDIUM confidence (no MiniLegion build history yet — these are pre-build predictions).
