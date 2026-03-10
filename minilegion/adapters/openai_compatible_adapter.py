"""OpenAI-compatible LLM adapter.

Works with any endpoint that follows the OpenAI chat completions API:
Groq, Together AI, LM Studio, OpenRouter, Perplexity, etc.

Config example (minilegion.config.json):
    {
        "provider": "openai-compatible",
        "model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1"
    }
"""

import os

import openai
from openai import OpenAI

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError


class OpenAICompatibleAdapter(LLMAdapter):
    """Adapter for any OpenAI-compatible REST endpoint.

    Uses the OpenAI Python SDK with a custom base_url. Works with
    Groq, Together AI, LM Studio, OpenRouter, Perplexity, and others.
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        api_key = os.environ.get(self._config.api_key_env, "")
        if not api_key and not self._config.base_url:
            raise LLMError(
                f"API key not found. Set the {self._config.api_key_env} "
                f"environment variable."
            )

        # Some local endpoints (LM Studio) don't require a real key.
        api_key = api_key or "not-required"

        kwargs: dict = {
            "api_key": api_key,
            "timeout": float(self._config.timeout),
            "max_retries": 0,
        }
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url

        self._client = OpenAI(**kwargs)
        return self._client

    def call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
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
        client = self._get_client()

        kwargs: dict = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if timeout is not None:
            kwargs["timeout"] = float(timeout)
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise LLMError(
                f"Authentication failed — check {self._config.api_key_env}: {exc}"
            ) from exc
        except openai.APITimeoutError as exc:
            effective_timeout = timeout or self._config.timeout
            raise LLMError(
                f"Request timed out after {effective_timeout}s: {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMError(f"API error: {exc}") from exc

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
