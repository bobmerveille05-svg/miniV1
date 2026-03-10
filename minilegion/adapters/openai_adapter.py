"""OpenAI LLM adapter using the chat completions API.

Provides OpenAIAdapter — a concrete LLMAdapter implementation that sends
prompts via the OpenAI SDK and returns structured LLMResponse objects.

Key behaviors:
- Lazy client initialization (created on first call, not at construction)
- API key read from env var specified in MiniLegionConfig.api_key_env
- All SDK errors wrapped in LLMError with exception chaining
- No SDK-level retries (max_retries=0) — retry lives in core/retry.py
"""

import os

import openai
from openai import OpenAI

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError


class OpenAIAdapter(LLMAdapter):
    """OpenAI LLM adapter using the chat completions API.

    Lazy client initialization — the OpenAI client is created on
    first call, not at construction time. This avoids requiring
    the API key at import/construction time.
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
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
            max_retries=0,
        )
        return self._client

    def call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        """Send a prompt and receive a structured response."""
        return self._do_call(
            system_prompt,
            user_message,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format=None,
        )

    def call_for_json(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        """Send a prompt requesting JSON-formatted output.

        Passes response_format={"type": "json_object"} to the OpenAI SDK
        to enforce JSON mode.
        """
        return self._do_call(
            system_prompt,
            user_message,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format={"type": "json_object"},
        )

    def _do_call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None,
        timeout: int | None,
        response_format: dict | None,
    ) -> LLMResponse:
        """Shared implementation for call() and call_for_json()."""
        client = self._get_client()

        kwargs: dict = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        if max_tokens is not None:
            kwargs["max_completion_tokens"] = max_tokens
        if timeout is not None:
            kwargs["timeout"] = float(timeout)
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise LLMError(
                f"Authentication failed — check your API key "
                f"({self._config.api_key_env}): {exc}"
            ) from exc
        except openai.APITimeoutError as exc:
            effective_timeout = timeout or self._config.timeout
            raise LLMError(
                f"Request timed out after {effective_timeout}s: {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc

        return self._map_response(response)

    def _map_response(self, response) -> LLMResponse:
        """Map SDK ChatCompletion to LLMResponse."""
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
