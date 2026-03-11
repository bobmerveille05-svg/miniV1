"""Deterministic provider readiness checks for research orchestration."""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request

from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ConfigError, LLMError

_SUPPORTED_PROVIDERS = {
    "openai",
    "openai-compatible",
    "ollama",
    "gemini",
    "anthropic",
}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_DEFAULT_OLLAMA_URL = "http://localhost:11434"


def provider_healthcheck_enabled(config: MiniLegionConfig) -> bool:
    """Return whether provider readiness checks should run."""
    return bool(config.provider_healthcheck)


def run_provider_healthcheck(config: MiniLegionConfig) -> None:
    """Fail fast when configured provider is not ready for research."""
    if not provider_healthcheck_enabled(config):
        return

    provider = config.provider.lower()
    if provider not in _SUPPORTED_PROVIDERS:
        known = ", ".join(sorted(_SUPPORTED_PROVIDERS))
        raise ConfigError(
            f"Unknown provider '{config.provider}'. Supported providers: {known}"
        )

    if provider == "ollama":
        _check_ollama(config)
        return

    if provider == "openai-compatible":
        _check_openai_compatible(config)
        return

    _require_env_var(config.api_key_env, provider)


def _check_openai_compatible(config: MiniLegionConfig) -> None:
    if not config.base_url:
        raise ConfigError(
            "Provider 'openai-compatible' requires base_url in minilegion.config.json "
            "so MiniLegion knows which endpoint to use."
        )

    if _is_local_url(config.base_url):
        return

    _require_env_var(config.api_key_env, "openai-compatible")


def _check_ollama(config: MiniLegionConfig) -> None:
    base_url = (config.base_url or _DEFAULT_OLLAMA_URL).rstrip("/")
    url = f"{base_url}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=config.timeout):
            return
    except urllib.error.URLError as exc:
        raise LLMError(
            f"Ollama is not ready at {base_url}. Start Ollama or update base_url. Error: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise LLMError(
            f"Ollama healthcheck timed out after {config.timeout}s at {base_url}."
        ) from exc


def _require_env_var(env_name: str, provider: str) -> None:
    if os.environ.get(env_name):
        return
    raise ConfigError(
        f"Provider '{provider}' is not ready. Set the {env_name} environment variable "
        "before running research."
    )


def _is_local_url(base_url: str) -> bool:
    parsed = urllib.parse.urlparse(base_url)
    return (parsed.hostname or "").lower() in _LOCAL_HOSTS
