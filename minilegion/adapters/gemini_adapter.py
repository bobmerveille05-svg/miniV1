"""Google Gemini LLM adapter using the google-genai SDK.

Requires: pip install google-genai

Config example (minilegion.config.json):
    {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "api_key_env": "GEMINI_API_KEY"
    }

Supported models: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash, etc.
"""

import os

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError


class GeminiAdapter(LLMAdapter):
    """Google Gemini adapter using the google-genai SDK.

    Lazy client initialization. JSON mode uses response_mime_type
    "application/json" which is natively supported by Gemini models.
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from google import genai  # type: ignore[import]
        except ImportError as exc:
            raise LLMError(
                "google-genai package not installed. Run: pip install google-genai"
            ) from exc

        api_key = os.environ.get(self._config.api_key_env)
        if not api_key:
            raise LLMError(
                f"API key not found. Set the {self._config.api_key_env} "
                f"environment variable."
            )

        self._client = genai.Client(api_key=api_key)
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
            from google.genai import types  # type: ignore[import]
        except ImportError as exc:
            raise LLMError(
                "google-genai package not installed. Run: pip install google-genai"
            ) from exc

        client = self._get_client()

        generation_config: dict = {}
        if max_tokens is not None:
            generation_config["max_output_tokens"] = max_tokens
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        config_kwargs: dict = {
            "system_instruction": system_prompt,
        }
        if generation_config:
            config_kwargs["generation_config"] = types.GenerateContentConfig(
                **generation_config
            )

        try:
            response = client.models.generate_content(
                model=self._config.model,
                contents=user_message,
                config=types.GenerateContentConfig(**config_kwargs)
                if config_kwargs
                else None,
            )
        except Exception as exc:
            # google-genai raises various exception types depending on error
            exc_str = str(exc)
            if "API_KEY" in exc_str or "UNAUTHENTICATED" in exc_str or "403" in exc_str:
                raise LLMError(
                    f"Authentication failed — check {self._config.api_key_env}: {exc}"
                ) from exc
            if "DEADLINE_EXCEEDED" in exc_str or "timeout" in exc_str.lower():
                raise LLMError(f"Gemini request timed out: {exc}") from exc
            raise LLMError(f"Gemini API error: {exc}") from exc

        return self._map_response(response)

    def _map_response(self, response) -> LLMResponse:
        """Map Gemini GenerateContentResponse to LLMResponse."""
        content = ""
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                content = "".join(
                    part.text
                    for part in candidate.content.parts
                    if hasattr(part, "text") and part.text
                )
            finish_reason = (
                str(candidate.finish_reason) if candidate.finish_reason else "stop"
            )
        else:
            finish_reason = "stop"

        usage = response.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            model=self._config.model,
            finish_reason=finish_reason,
        )
