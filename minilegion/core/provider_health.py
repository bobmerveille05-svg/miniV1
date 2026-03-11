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


def fetch_ollama_models(base_url: str | None = None, timeout: int = 10) -> list[str]:
    """Return list of model names installed in a running Ollama instance.

    Returns an empty list if Ollama is unreachable (no exception raised).
    """
    import json as _json

    url = f"{(base_url or _DEFAULT_OLLAMA_URL).rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:  # noqa: BLE001
        return []


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
    import json as _json

    base_url = (config.base_url or _DEFAULT_OLLAMA_URL).rstrip("/")
    url = f"{base_url}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=config.timeout) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise LLMError(
            f"Cannot reach Ollama at {base_url}. Is Ollama running? Error: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise LLMError(
            f"Ollama healthcheck timed out after {config.timeout}s at {base_url}."
        ) from exc

    # Check that the configured model is actually installed.
    # Match by exact name OR by base name (strip tag suffix after ':').
    # Prefer exact match; if only base matches, suggest the exact installed name.
    model = config.model
    model_base = model.split(":")[0]
    installed_names = [m.get("name", "") for m in data.get("models", [])]

    exact_match = model in installed_names
    base_matches = [n for n in installed_names if n.split(":")[0] == model_base]

    if not exact_match and not base_matches:
        available = ", ".join(sorted(installed_names)) or "none"
        raise LLMError(
            f"Model '{model}' is not installed in Ollama.\n"
            f"Run: ollama pull {model}\n"
            f"Installed models: {available}"
        )

    if not exact_match and base_matches:
        # The user typed 'deepseek-r1' but installed name is 'deepseek-r1:1.5b' —
        # surface this so they know the exact name to use.
        suggestion = base_matches[0]
        raise LLMError(
            f"Model '{model}' not found. Did you mean '{suggestion}'?\n"
            f"Update your config: minilegion config model\n"
            f"Or use the exact name in config: {suggestion}"
        )

    # Warn (but don't block) if a cloud-routed model is selected
    if model.endswith("-cloud") or ":cloud" in model:
        import warnings

        warnings.warn(
            f"Model '{model}' is routed via ollama.com (cloud). "
            "It requires internet access and may be slow. "
            "Consider a local model like deepseek-r1:1.5b or gemma3:4b.",
            stacklevel=3,
        )


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
