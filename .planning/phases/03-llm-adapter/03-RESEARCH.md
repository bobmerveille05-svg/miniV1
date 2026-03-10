# Phase 3: LLM Adapter - Research

**Researched:** 2026-03-10
**Domain:** LLM API integration (OpenAI Python SDK, abstract adapter pattern)
**Confidence:** HIGH

## Summary

Phase 3 creates the adapter layer between MiniLegion's retry/validation logic (Phase 2) and the pipeline stages (Phases 6-10). The deliverables are: (1) an abstract base class `LLMAdapter` in `minilegion/adapters/base.py` defining the contract, (2) `LLMResponse`/`TokenUsage` dataclasses for structured returns, and (3) a concrete `OpenAIAdapter` in `minilegion/adapters/openai_adapter.py` using the `openai` Python SDK's `chat.completions.create()` endpoint.

The OpenAI SDK v2.24.0 (installed locally, verified) provides typed Pydantic response models (`ChatCompletion`, `CompletionUsage`), a clear error hierarchy (`APIError` → `APIStatusError`/`APIConnectionError` → specific errors), and built-in retry/timeout support that must be **disabled** at the SDK level since MiniLegion handles retry in `core/retry.py`. The adapter is a single-shot caller — it wraps SDK exceptions into `LLMError` and returns structured results.

**Primary recommendation:** Use Python `dataclass` for `LLMResponse`/`TokenUsage` (not Pydantic — these are not validated against schemas). Implement lazy client initialization with explicit API key check from `config.api_key_env`. Disable SDK-level retries (`max_retries=0`) to avoid double-retry with `validate_with_retry()`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Abstract base class `LLMAdapter` in `minilegion/adapters/base.py` using Python `abc.ABC` + `@abstractmethod`
- Primary method: `call(system_prompt: str, user_message: str, *, max_tokens: int | None = None, timeout: int | None = None) -> LLMResponse`
- `LLMResponse` is a dataclass/Pydantic model containing: `content: str` (raw text response), `usage: TokenUsage` (prompt_tokens, completion_tokens, total_tokens), `model: str` (actual model used), `finish_reason: str`
- `TokenUsage` is a simple dataclass: `prompt_tokens: int`, `completion_tokens: int`, `total_tokens: int`
- A convenience method `call_for_json(system_prompt, user_message, ...) -> LLMResponse` that adds `response_format` hint — concrete adapter decides how (OpenAI uses `response_format={"type": "json_object"}`)
- New adapter = subclass `LLMAdapter`, implement `call()` and `call_for_json()` — no other code changes needed
- Concrete class `OpenAIAdapter` in `minilegion/adapters/openai_adapter.py`
- Uses `openai` Python SDK, `client.chat.completions.create()` with `response_format={"type": "json_object"}` for structured output
- Lazy client initialization — `openai.OpenAI()` created on first call, not at adapter construction
- Reads API key from env var specified in `config.api_key_env` (default: `OPENAI_API_KEY`)
- Model from `config.model` (default: `gpt-4o`)
- Timeout from `config.timeout` or per-call override
- Missing API key: raise `LLMError` with clear message naming the expected env var — checked before any API call
- API errors (rate limits, server errors): catch `openai.APIError` and subclasses, wrap in `LLMError` with context
- Timeout: catch `openai.APITimeoutError`, wrap in `LLMError`
- Authentication failures: catch `openai.AuthenticationError`, wrap in `LLMError` with "check your API key" message
- Do NOT retry at the adapter level — retry logic lives in `core/retry.py` (Phase 2). Adapter is a single-shot caller.
- Integration pattern: `llm_call = lambda prompt: adapter.call_for_json(system_prompt, prompt).content`

### OpenCode's Discretion
- Internal structure of the adapter module (helper functions, etc.)
- Exact error message wording (as long as it names the missing env var / error type)
- Whether to use dataclass or Pydantic model for LLMResponse/TokenUsage (dataclass preferred for simplicity)
- Test mocking strategy for OpenAI API calls

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADPT-01 | Abstract base class defines the LLM adapter contract (send prompt, receive response, structured output support) | `abc.ABC` + `@abstractmethod` pattern; `LLMAdapter` with `call()` and `call_for_json()` methods; `LLMResponse`/`TokenUsage` dataclasses |
| ADPT-02 | OpenAI adapter implements the base class using `openai` SDK with `response_format` for structured JSON output | `client.chat.completions.create()` with `response_format={"type": "json_object"}`; SDK v2.24.0 verified; `ChatCompletion` response model mapped to `LLMResponse` |
| ADPT-03 | Adapter accepts system prompt + user message + max_tokens + timeout and returns raw content + token usage | `messages=[{"role": "system", ...}, {"role": "user", ...}]`; `max_tokens` → `max_completion_tokens` param; `timeout` as float; `CompletionUsage` fields mapped to `TokenUsage` |
| ADPT-04 | Adapter reads API key from environment variable specified in config | Lazy init checks `os.environ.get(config.api_key_env)` before constructing `openai.OpenAI(api_key=...)` client; missing raises `LLMError` |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `openai` | >=1.0,<3.0 (locally: 2.24.0) | OpenAI API client | Official SDK with typed responses (Pydantic models), structured error hierarchy, timeout support |
| `abc` (stdlib) | N/A | Abstract base class | Python standard library — zero dependency cost |
| `dataclasses` (stdlib) | N/A | `LLMResponse`/`TokenUsage` data containers | Lightweight, no validation needed (these are output, not input schemas) |
| `os` (stdlib) | N/A | Environment variable access | Read API key from env |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock` | N/A (stdlib) | Mock OpenAI SDK in tests | All adapter tests — never call real API |
| `pytest` | >=8.0 | Test runner | Already in dev dependencies |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dataclass` for LLMResponse | Pydantic `BaseModel` | Pydantic adds validation overhead unnecessary for output containers; dataclass is simpler and matches CONTEXT.md preference |
| `response_format={"type": "json_object"}` | `response_format={"type": "json_schema", "json_schema": {...}}` | JSON Schema mode is more strict but requires passing schema definition; `json_object` is simpler and sufficient since MiniLegion validates separately in `core/retry.py` |

**Installation:**
```bash
# openai needs to be added to pyproject.toml dependencies (currently missing!)
# pyproject.toml lists only typer and pydantic — openai must be added
pip install openai>=1.0
```

**CRITICAL NOTE:** `openai` is NOT listed in `pyproject.toml` dependencies. It is installed locally but must be added to `[project] dependencies` during this phase:
```toml
dependencies = [
    "typer>=0.24.0",
    "pydantic>=2.12.0",
    "openai>=1.0",
]
```

## Architecture Patterns

### Recommended Project Structure
```
minilegion/
├── adapters/
│   ├── __init__.py         # Re-exports LLMAdapter, LLMResponse, TokenUsage, OpenAIAdapter
│   ├── base.py             # LLMAdapter ABC, LLMResponse, TokenUsage dataclasses
│   └── openai_adapter.py   # OpenAIAdapter concrete implementation
```

### Pattern 1: Abstract Base Class with Dataclass Returns
**What:** `LLMAdapter` defines the contract via `abc.ABC` + `@abstractmethod`. Return types are `dataclass` objects, not raw dicts.
**When to use:** Always — this is the core pattern for the phase.
**Example:**
```python
# minilegion/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    """Token usage statistics from an LLM response."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from an LLM call."""
    content: str
    usage: TokenUsage
    model: str
    finish_reason: str


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""

    @abstractmethod
    def call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        """Send a prompt and receive a structured response."""
        ...

    @abstractmethod
    def call_for_json(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        """Send a prompt requesting JSON-formatted output."""
        ...
```

### Pattern 2: Lazy Client Initialization with API Key Validation
**What:** OpenAI client is NOT created in `__init__` — it's created on first `call()`/`call_for_json()` invocation. API key is validated from env var before client creation.
**When to use:** `OpenAIAdapter` — avoids requiring API key at import time, enables testing construction without env vars.
**Example:**
```python
# minilegion/adapters/openai_adapter.py
import os
from openai import OpenAI
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError
from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage


class OpenAIAdapter(LLMAdapter):
    """OpenAI LLM adapter using the chat completions API."""

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client: OpenAI | None = None  # Lazy init

    def _get_client(self) -> OpenAI:
        """Get or create the OpenAI client, validating API key first."""
        if self._client is not None:
            return self._client

        api_key = os.environ.get(self._config.api_key_env)
        if not api_key:
            raise LLMError(
                f"API key not found. Set the {self._config.api_key_env} "
                f"environment variable."
            )

        self._client = OpenAI(
            api_key=api_key,
            timeout=float(self._config.timeout),
            max_retries=0,  # No SDK-level retries — retry lives in core/retry.py
        )
        return self._client
```

### Pattern 3: Exception Wrapping with Chaining
**What:** All `openai.*Error` exceptions are caught and re-raised as `LLMError` using `raise ... from exc` to preserve the exception chain.
**When to use:** Every API call in `OpenAIAdapter`.
**Example:**
```python
import openai

try:
    response = client.chat.completions.create(...)
except openai.AuthenticationError as exc:
    raise LLMError(
        f"Authentication failed — check your API key "
        f"({self._config.api_key_env}): {exc}"
    ) from exc
except openai.APITimeoutError as exc:
    raise LLMError(f"Request timed out after {timeout}s: {exc}") from exc
except openai.APIError as exc:
    raise LLMError(f"OpenAI API error: {exc}") from exc
```

### Pattern 4: Integration with validate_with_retry
**What:** The adapter provides the `Callable[[str], str]` that `validate_with_retry()` expects via a lambda that binds the system prompt.
**When to use:** Pipeline stages (Phases 6-10) — not implemented in this phase but the interface is designed for it.
**Example:**
```python
# Future usage in pipeline stages:
adapter = OpenAIAdapter(config)
llm_call = lambda prompt: adapter.call_for_json(system_prompt, prompt).content

result = validate_with_retry(
    llm_call=llm_call,
    prompt=user_prompt,
    artifact_name="research",
    config=config,
    project_dir=project_dir,
)
```

### Anti-Patterns to Avoid
- **Retrying at adapter level:** Adapter is a single-shot caller. Retry logic lives exclusively in `core/retry.py`. Setting `max_retries=0` on the OpenAI client prevents SDK-level retries from conflicting.
- **Creating client in `__init__`:** Forces API key to exist at construction time, breaking tests and import-time safety.
- **Catching `Exception` broadly:** Only catch `openai.APIError` and its subclasses. Let unexpected errors (TypeError, etc.) propagate naturally.
- **Returning raw SDK response objects:** Always map to `LLMResponse`/`TokenUsage` dataclasses to keep the adapter boundary clean.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client for OpenAI API | Custom `requests`/`httpx` calls | `openai` SDK | Handles auth headers, request formatting, response parsing, error codes, retries, streaming, rate limit headers |
| Response type mapping | Manual dict parsing | SDK's `ChatCompletion` Pydantic model | Typed fields (`choices[0].message.content`, `usage.prompt_tokens`) with IDE autocomplete |
| Error classification | Status code parsing | SDK's error hierarchy (`AuthenticationError`, `RateLimitError`, etc.) | Catches all edge cases (connection errors, timeouts, malformed responses) |
| JSON output mode | Prompt-only JSON instructions | `response_format={"type": "json_object"}` | API-level enforcement ensures valid JSON output; prompt instructions alone are unreliable |

**Key insight:** The OpenAI SDK does all the heavy lifting. The adapter's job is thin: construct messages, call API, map response, wrap errors. Don't add complexity beyond this.

## Common Pitfalls

### Pitfall 1: Double Retry
**What goes wrong:** If `max_retries` is left at the SDK default (2), the SDK retries rate-limit/server errors internally. Combined with `validate_with_retry`'s retries, a single bad call could trigger 3×3 = 9 API calls.
**Why it happens:** The OpenAI SDK defaults `max_retries=2` for all clients.
**How to avoid:** Set `max_retries=0` when constructing `openai.OpenAI()`.
**Warning signs:** Unexpectedly high API usage, slow error propagation.

### Pitfall 2: `max_tokens` vs `max_completion_tokens`
**What goes wrong:** The `max_tokens` parameter is a legacy name. The current SDK parameter is `max_completion_tokens`. Using `max_tokens` still works but may be deprecated.
**Why it happens:** OpenAI renamed the parameter; old tutorials use `max_tokens`.
**How to avoid:** Use `max_completion_tokens` in the SDK call. The adapter's public API can still accept `max_tokens` as the parameter name (it's more intuitive for callers), but internally map it to `max_completion_tokens`.
**Warning signs:** Deprecation warnings from the SDK.

### Pitfall 3: Missing `system` Role in JSON Mode
**What goes wrong:** When using `response_format={"type": "json_object"}`, OpenAI requires the prompt to mention "JSON" somewhere in the system or user message. If neither message mentions JSON, the API returns an error.
**Why it happens:** API-level requirement documented in OpenAI docs.
**How to avoid:** In `call_for_json()`, ensure the system prompt or user message includes the word "JSON". The pipeline's prompt templates (Phase 5) will handle this, but the adapter should NOT silently modify prompts.
**Warning signs:** `BadRequestError` with message about JSON format requirement.

### Pitfall 4: API Key Validation Timing
**What goes wrong:** If API key validation happens only inside the SDK constructor, the error message is generic ("The api_key client option must be set..."). Users won't know which env var to set.
**Why it happens:** The SDK reads from `OPENAI_API_KEY` by default, but MiniLegion uses `config.api_key_env` which could be custom.
**How to avoid:** Check `os.environ.get(config.api_key_env)` BEFORE constructing the client, and raise `LLMError` with the specific env var name.
**Warning signs:** Users getting SDK's default error message instead of MiniLegion's.

### Pitfall 5: Frozen Dataclass with Mutable Fields
**What goes wrong:** Using `frozen=True` on `LLMResponse` while `TokenUsage` is a separate dataclass — if `TokenUsage` is not also frozen, the immutability guarantee is incomplete.
**Why it happens:** Forgetting to make both dataclasses frozen.
**How to avoid:** Make both `TokenUsage` and `LLMResponse` use `@dataclass(frozen=True)`.
**Warning signs:** Tests that mutate response objects unexpectedly passing.

### Pitfall 6: OpenAI SDK Timeout Type
**What goes wrong:** The SDK's `timeout` parameter expects `float | httpx.Timeout | None`, not `int`. Passing `int` works due to Python's number coercion, but the per-request `timeout` in `client.chat.completions.create()` also expects a float.
**Why it happens:** Config stores `timeout` as `int`, SDK expects `float`.
**How to avoid:** Cast: `timeout=float(self._config.timeout)` when constructing client, and `timeout=float(timeout)` for per-request overrides.
**Warning signs:** Type checker warnings in strict mode.

## Code Examples

Verified patterns from official SDK (v2.24.0, locally installed):

### Complete OpenAI Call with JSON Mode
```python
# Source: OpenAI Python SDK v2.24.0, verified locally
import openai
from openai import OpenAI

client = OpenAI(api_key="sk-...", max_retries=0, timeout=120.0)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Respond in JSON."},
        {"role": "user", "content": "List 3 colors"},
    ],
    response_format={"type": "json_object"},
    max_completion_tokens=1000,
    timeout=60.0,  # Per-request override
)

# Response structure (verified):
# response.choices[0].message.content  -> str (JSON text)
# response.choices[0].finish_reason    -> "stop" | "length" | "tool_calls" | "content_filter"
# response.model                       -> str (actual model used, e.g., "gpt-4o-2024-08-06")
# response.usage.prompt_tokens         -> int
# response.usage.completion_tokens     -> int
# response.usage.total_tokens          -> int
```

### Mapping SDK Response to LLMResponse
```python
def _map_response(self, response: openai.types.chat.ChatCompletion) -> LLMResponse:
    """Map OpenAI ChatCompletion to LLMResponse."""
    choice = response.choices[0]
    usage = response.usage

    return LLMResponse(
        content=choice.message.content or "",
        usage=TokenUsage(
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
        ),
        model=response.model,
        finish_reason=choice.finish_reason,
    )
```

### Error Hierarchy (Verified Locally)
```python
# OpenAI SDK v2.24.0 error hierarchy (verified via inspection):
#
# openai.OpenAIError (base, NOT Exception subclass — it IS Exception)
# └── openai.APIError
#     ├── openai.APIConnectionError
#     │   └── openai.APITimeoutError
#     └── openai.APIStatusError
#         ├── openai.AuthenticationError  (401)
#         ├── openai.PermissionDeniedError (403)
#         ├── openai.NotFoundError        (404)
#         ├── openai.BadRequestError      (400)
#         ├── openai.UnprocessableEntityError (422)
#         ├── openai.RateLimitError       (429)
#         ├── openai.ConflictError        (409)
#         └── openai.InternalServerError  (>=500)
#
# Catch order: AuthenticationError → APITimeoutError → APIError (catches all)
```

### Test Mocking Strategy
```python
# Recommended: Mock at the OpenAI client method level
from unittest.mock import MagicMock, patch, PropertyMock
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types import CompletionUsage

def make_mock_completion(content="test", model="gpt-4o"):
    """Create a mock ChatCompletion response for testing."""
    return ChatCompletion(
        id="chatcmpl-test",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content=content,
                    role="assistant",
                ),
            )
        ],
        created=1234567890,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        ),
    )

# Usage in tests:
def test_call_returns_llm_response(self):
    adapter = OpenAIAdapter(MiniLegionConfig())
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_completion('{"key": "value"}')
    adapter._client = mock_client  # Bypass lazy init

    result = adapter.call("system", "user")
    assert result.content == '{"key": "value"}'
    assert result.usage.total_tokens == 30
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `openai.ChatCompletion.create()` (v0.x) | `client.chat.completions.create()` (v1.0+) | Nov 2023 | Method-based → client-based API; must use `OpenAI()` client instance |
| `max_tokens` param | `max_completion_tokens` param | 2024 | Old name still works but is deprecated path |
| `response_format={"type": "json_object"}` | Also `response_format={"type": "json_schema", ...}` | Aug 2024 | `json_schema` gives stricter guarantees, but `json_object` is simpler for our use case |
| `"role": "system"` | `"role": "developer"` (new option) | Late 2024 | SDK README shows `developer` role; `system` still works and is standard for our use case |
| SDK auto-retries default: 2 | Still 2 in v2.24.0 | Unchanged | Must set `max_retries=0` since MiniLegion handles retry |

**Deprecated/outdated:**
- `openai.ChatCompletion.create()` (v0.x style): Removed in v1.0. Use `client.chat.completions.create()`.
- Module-level `openai.api_key = "..."`: Removed in v1.0. Pass to `OpenAI(api_key=...)` constructor.

## Open Questions

1. **`openai` package not in pyproject.toml dependencies**
   - What we know: `openai` is installed locally (v2.24.0) but NOT listed in `pyproject.toml` `[project] dependencies`
   - What's unclear: Whether this was intentional (deferred to Phase 3) or an oversight
   - Recommendation: Add `"openai>=1.0"` to dependencies as part of this phase. This is required for the adapter to work.

2. **Should `call_for_json()` be abstract or concrete with template method?**
   - What we know: CONTEXT.md says both `call()` and `call_for_json()` should be `@abstractmethod` ("implement `call()` and `call_for_json()`")
   - What's unclear: Whether `call_for_json()` could have a default implementation that calls `call()` with an extra hint
   - Recommendation: Make both abstract per CONTEXT.md. Each provider handles JSON mode differently (OpenAI uses `response_format`, others may use prompt-only), so the base class shouldn't assume how.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_adapter.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADPT-01 | ABC contract: `LLMAdapter` cannot be instantiated directly; subclass must implement `call()` and `call_for_json()` | unit | `pytest tests/test_adapter.py::TestLLMAdapterABC -x` | ❌ Wave 0 |
| ADPT-01 | `LLMResponse` and `TokenUsage` dataclasses hold correct fields | unit | `pytest tests/test_adapter.py::TestDataclasses -x` | ❌ Wave 0 |
| ADPT-02 | `OpenAIAdapter.call_for_json()` passes `response_format={"type": "json_object"}` to SDK | unit | `pytest tests/test_openai_adapter.py::TestCallForJson -x` | ❌ Wave 0 |
| ADPT-02 | `OpenAIAdapter.call()` maps SDK response to `LLMResponse` correctly | unit | `pytest tests/test_openai_adapter.py::TestCall -x` | ❌ Wave 0 |
| ADPT-03 | System prompt, user message, max_tokens, timeout all passed to SDK | unit | `pytest tests/test_openai_adapter.py::TestCallParameters -x` | ❌ Wave 0 |
| ADPT-03 | Token usage mapped from `CompletionUsage` to `TokenUsage` | unit | `pytest tests/test_openai_adapter.py::TestTokenUsage -x` | ❌ Wave 0 |
| ADPT-04 | Missing API key raises `LLMError` naming the env var | unit | `pytest tests/test_openai_adapter.py::TestAPIKeyValidation -x` | ❌ Wave 0 |
| ADPT-04 | API key read from env var in config, not hardcoded | unit | `pytest tests/test_openai_adapter.py::TestAPIKeyFromConfig -x` | ❌ Wave 0 |
| — | API errors wrapped in `LLMError` with exception chaining | unit | `pytest tests/test_openai_adapter.py::TestErrorWrapping -x` | ❌ Wave 0 |
| — | Lazy client initialization (not created in `__init__`) | unit | `pytest tests/test_openai_adapter.py::TestLazyInit -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_adapter.py tests/test_openai_adapter.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_adapter.py` — covers ADPT-01 (ABC contract, dataclasses)
- [ ] `tests/test_openai_adapter.py` — covers ADPT-02, ADPT-03, ADPT-04 (OpenAI adapter, error wrapping, API key)
- [ ] No new conftest fixtures needed — existing `tmp_project_dir` and `sample_config_json` are reusable; add `make_mock_completion` helper

*(Existing test infrastructure covers framework/runner; only test files for new adapter code are needed)*

## Sources

### Primary (HIGH confidence)
- OpenAI Python SDK v2.24.0 — locally installed, error hierarchy inspected via `inspect` module
- OpenAI Python SDK README (GitHub, main branch) — constructor params, error handling, timeouts, retries
- OpenAI API Reference (platform.openai.com) — `ChatCompletion` model, `response_format` options, `CompletionUsage` fields
- Project source code — `core/retry.py`, `core/config.py`, `core/exceptions.py` read directly

### Secondary (MEDIUM confidence)
- OpenAI SDK `chat.completions.create()` signature — inspected locally, `response_format`, `timeout`, `max_completion_tokens` params verified
- `ChatCompletion.Choice` — `finish_reason` is `Literal["stop", "length", "tool_calls", "content_filter", "function_call"]` (verified from SDK source)
- `ResponseFormatJSONObject` — `TypedDict` with `type: Required[Literal["json_object"]]` (verified from SDK source)

### Tertiary (LOW confidence)
- None — all findings verified against local SDK installation or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `openai` SDK installed and inspected locally; all types and error classes verified
- Architecture: HIGH — patterns derived from locked CONTEXT.md decisions and verified SDK API
- Pitfalls: HIGH — double-retry, max_tokens deprecation, JSON mode requirements all verified against SDK source and docs

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable — OpenAI SDK v2.x is mature; `chat.completions` API is marked "supported indefinitely")
