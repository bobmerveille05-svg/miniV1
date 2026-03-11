"""Ollama LLM adapter using the local HTTP REST API.

Talks directly to a running Ollama instance via its native /api/chat
endpoint. No external SDK required — uses only the standard library
urllib (via httpx-style requests through urllib.request).

Config example (minilegion.config.json):
    {
        "provider": "ollama",
        "model": "llama3.2",
        "base_url": "http://localhost:11434"
    }

The api_key_env field is ignored for Ollama (no auth required).
If base_url is not set, defaults to http://localhost:11434.
"""

import json
import urllib.error
import urllib.request
from typing import Any

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAdapter(LLMAdapter):
    """Adapter for locally-running Ollama models.

    Calls the Ollama /api/chat endpoint directly with no external SDK.
    JSON mode is approximated by injecting a system instruction asking
    for JSON output — Ollama does not have a native json_object mode,
    though models like mistral/llama support it via format="json".
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._base_url = (config.base_url or _DEFAULT_BASE_URL).rstrip("/")

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
        url = f"{self._base_url}/api/chat"
        effective_timeout = float(timeout or self._config.timeout)

        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        if max_tokens is not None:
            payload["options"] = {"num_predict": max_tokens}

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LLMError(
                    f"Model '{self._config.model}' is not installed in Ollama.\n"
                    f"Run: ollama pull {self._config.model}"
                ) from exc
            raise LLMError(
                f"Ollama returned HTTP {exc.code} at {self._base_url}. Error: {exc}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self._base_url}. Is it running? Error: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise LLMError(
                f"Ollama request timed out after {effective_timeout}s"
            ) from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"Ollama returned invalid JSON: {exc}") from exc

        return self._map_response(raw)

    def _map_response(self, raw: dict) -> LLMResponse:
        """Map Ollama /api/chat response to LLMResponse."""
        message = raw.get("message", {})
        content = message.get("content", "")

        # Ollama reports token counts in eval_count / prompt_eval_count
        prompt_tokens = raw.get("prompt_eval_count", 0)
        completion_tokens = raw.get("eval_count", 0)

        finish_reason = "stop"
        if raw.get("done_reason"):
            finish_reason = raw["done_reason"]

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            model=raw.get("model", self._config.model),
            finish_reason=finish_reason,
        )
