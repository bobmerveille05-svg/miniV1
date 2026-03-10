"""Anthropic Claude LLM adapter using the anthropic SDK.

Requires: pip install anthropic

Config example (minilegion.config.json):
    {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key_env": "ANTHROPIC_API_KEY"
    }

Supported models: claude-3-5-sonnet-*, claude-3-5-haiku-*, claude-3-opus-*, etc.

JSON mode: Anthropic has no native json_object mode. Instead, we use
a prefill technique — the assistant turn is pre-seeded with "{" to
strongly encourage JSON output, then the "{" is prepended to the
response content.
"""

import os

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError

_JSON_SYSTEM_SUFFIX = (
    "\n\nYou must respond with valid JSON only. "
    "Do not include any text before or after the JSON object."
)


class AnthropicAdapter(LLMAdapter):
    """Anthropic Claude adapter using the anthropic SDK.

    Lazy client initialization. JSON mode uses the assistant prefill
    technique: seeding the assistant turn with "{" to ensure JSON output.
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise LLMError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        api_key = os.environ.get(self._config.api_key_env)
        if not api_key:
            raise LLMError(
                f"API key not found. Set the {self._config.api_key_env} "
                f"environment variable."
            )

        self._client = anthropic.Anthropic(
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
        return self._do_call(
            system_prompt,
            user_message,
            max_tokens=max_tokens,
            timeout=timeout,
            json_mode=False,
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
            json_mode=True,
        )

    def _do_call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None,
        timeout: int | None,
        json_mode: bool,
    ) -> LLMResponse:
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise LLMError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        client = self._get_client()

        # Anthropic requires max_tokens — default to a generous value.
        effective_max_tokens = max_tokens or 4096

        system = system_prompt
        messages = [{"role": "user", "content": user_message}]

        if json_mode:
            system = system_prompt + _JSON_SYSTEM_SUFFIX
            # Prefill assistant turn with "{" to enforce JSON
            messages.append({"role": "assistant", "content": "{"})

        kwargs: dict = {
            "model": self._config.model,
            "max_tokens": effective_max_tokens,
            "system": system,
            "messages": messages,
        }
        if timeout is not None:
            kwargs["timeout"] = float(timeout)

        try:
            response = client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise LLMError(
                f"Authentication failed — check {self._config.api_key_env}: {exc}"
            ) from exc
        except anthropic.APITimeoutError as exc:
            effective_timeout = timeout or self._config.timeout
            raise LLMError(
                f"Request timed out after {effective_timeout}s: {exc}"
            ) from exc
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc

        return self._map_response(response, json_mode=json_mode)

    def _map_response(self, response, *, json_mode: bool) -> LLMResponse:
        """Map Anthropic Message to LLMResponse."""
        content = ""
        if response.content:
            content = "".join(
                block.text
                for block in response.content
                if hasattr(block, "text") and block.text
            )

        # Re-attach the "{" prefill that Anthropic strips from its response
        if json_mode and not content.startswith("{"):
            content = "{" + content

        usage = response.usage
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage.input_tokens if usage else 0,
                completion_tokens=usage.output_tokens if usage else 0,
                total_tokens=(usage.input_tokens + usage.output_tokens) if usage else 0,
            ),
            model=response.model,
            finish_reason=response.stop_reason or "stop",
        )
