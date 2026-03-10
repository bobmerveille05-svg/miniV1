# Phase 3: LLM Adapter - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Abstract base class defining the LLM adapter contract (send prompt, receive structured response) and a concrete OpenAI adapter implementing that contract using the `openai` SDK. The adapter layer sits between the retry/validation logic (Phase 2) and the pipeline stages (Phases 6-10). This phase delivers the callable that `validate_with_retry()` wraps — it does NOT implement pipeline stages or prompt templates.

</domain>

<decisions>
## Implementation Decisions

### Abstract Base Class Contract
- Abstract base class `LLMAdapter` in `minilegion/adapters/base.py` using Python `abc.ABC` + `@abstractmethod`
- Primary method: `call(system_prompt: str, user_message: str, *, max_tokens: int | None = None, timeout: int | None = None) -> LLMResponse`
- `LLMResponse` is a dataclass/Pydantic model containing: `content: str` (raw text response), `usage: TokenUsage` (prompt_tokens, completion_tokens, total_tokens), `model: str` (actual model used), `finish_reason: str`
- `TokenUsage` is a simple dataclass: `prompt_tokens: int`, `completion_tokens: int`, `total_tokens: int`
- A convenience method `call_for_json(system_prompt, user_message, ...) -> LLMResponse` that adds `response_format` hint — concrete adapter decides how (OpenAI uses `response_format={"type": "json_object"}`)
- New adapter = subclass `LLMAdapter`, implement `call()` and `call_for_json()` — no other code changes needed

### OpenAI Adapter Implementation
- Concrete class `OpenAIAdapter` in `minilegion/adapters/openai_adapter.py`
- Uses `openai` Python SDK (already in pyproject.toml dependencies)
- Uses `client.chat.completions.create()` with `response_format={"type": "json_object"}` for structured output
- Lazy client initialization — `openai.OpenAI()` created on first call, not at adapter construction (avoids import-time API key requirement)
- Reads API key from env var specified in `config.api_key_env` (default: `OPENAI_API_KEY`)
- Model from `config.model` (default: `gpt-4o`)
- Timeout from `config.timeout` or per-call override

### Error Handling
- Missing API key: raise `LLMError` with clear message naming the expected env var — checked before any API call
- API errors (rate limits, server errors): catch `openai.APIError` and subclasses, wrap in `LLMError` with context
- Timeout: catch `openai.APITimeoutError`, wrap in `LLMError`
- Authentication failures: catch `openai.AuthenticationError`, wrap in `LLMError` with "check your API key" message
- Do NOT retry at the adapter level — retry logic lives in `core/retry.py` (Phase 2). Adapter is a single-shot caller.

### Integration with Phase 2 Retry Logic
- `validate_with_retry()` expects `Callable[[str], str]` — adapter provides this via a bound method or lambda
- Pattern: `llm_call = lambda prompt: adapter.call_for_json(system_prompt, prompt).content`
- This keeps the boundary clean — retry module doesn't know about adapters, adapter doesn't know about validation

### Token Usage Tracking
- `LLMResponse` includes token counts from the API response
- Caller (pipeline stages in future phases) can log/display token usage
- No persistent token tracking in this phase — just return the data

### OpenCode's Discretion
- Internal structure of the adapter module (helper functions, etc.)
- Exact error message wording (as long as it names the missing env var / error type)
- Whether to use dataclass or Pydantic model for LLMResponse/TokenUsage (dataclass preferred for simplicity — these are not validated against schemas)
- Test mocking strategy for OpenAI API calls

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MiniLegionConfig` (core/config.py): Has `provider`, `model`, `api_key_env`, `timeout`, `max_retries`, `engines`, `get_engine(role)` — adapter reads from this
- `LLMError` (core/exceptions.py): Already exists for LLM API call failures — adapter wraps API errors in this
- `validate_with_retry()` (core/retry.py): Expects `Callable[[str], str]` — adapter provides the callable
- `apply_fixups()` (core/fixups.py): Called by retry module, not by adapter directly
- `adapters/__init__.py`: Empty placeholder ready for adapter code

### Established Patterns
- Exception wrapping: `raise LLMError(...) from exc` (chain original exception)
- `BaseModel` with `Field()` for data classes (but dataclass is fine for response objects)
- `Stage(str, Enum)` pattern for string enums — not needed here

### Integration Points
- `core/retry.py` calls `llm_call(prompt)` — adapter.call_for_json provides this
- `core/config.py` provides API key env var name, model, timeout
- `core/exceptions.py` provides `LLMError` for error wrapping
- Pipeline stages (Phases 6-10) will construct adapter from config and pass to retry

</code_context>

<specifics>
## Specific Ideas

- REQUIREMENTS.md ADPT-01 specifies abstract base class with send prompt + receive response + structured output
- ADPT-02 specifies OpenAI SDK with `response_format` for structured JSON
- ADPT-03 specifies system prompt + user message + max_tokens + timeout → raw content + token usage
- ADPT-04 specifies API key from env var in config
- `openai` package already listed in pyproject.toml dependencies
- The `engines` dict in config maps role names to model strings — `get_engine(role)` falls back to default model

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-llm-adapter*
*Context gathered: 2026-03-10*
