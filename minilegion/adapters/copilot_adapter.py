"""GitHub Models LLM adapter (accessed via GitHub Personal Access Token).

Uses the OpenAI-compatible GitHub Models inference endpoint with a GitHub PAT
retrieved from the credential store (set via `minilegion auth login copilot`).

API endpoint: https://models.inference.ai.azure.com
Docs: https://docs.github.com/en/github-models
"""

from __future__ import annotations

import openai
from openai import OpenAI

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.auth import get_token
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import AuthError, LLMError

_COPILOT_BASE_URL = "https://models.inference.ai.azure.com"


class CopilotAdapter(LLMAdapter):
    """LLM adapter for GitHub Models via the OpenAI-compatible inference API.

    Retrieves the GitHub PAT from the credential store. The token is
    fetched lazily on first call so construction never triggers I/O.
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        try:
            token = get_token("copilot")
        except AuthError as exc:
            raise LLMError(
                f"GitHub Models authentication required. "
                f"Run: minilegion auth login copilot\n({exc})"
            ) from exc

        self._client = OpenAI(
            api_key=token,
            base_url=_COPILOT_BASE_URL,
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
            kwargs["max_completion_tokens"] = max_tokens
        if timeout is not None:
            kwargs["timeout"] = float(timeout)
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise LLMError(
                f"GitHub Models authentication failed. "
                f"Run: minilegion auth login copilot\n({exc})"
            ) from exc
        except openai.APITimeoutError as exc:
            effective_timeout = timeout or self._config.timeout
            raise LLMError(
                f"Request timed out after {effective_timeout}s: {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMError(f"GitHub Models API error: {exc}") from exc

        return self._map_response(response)

    def _map_response(self, response) -> LLMResponse:
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
