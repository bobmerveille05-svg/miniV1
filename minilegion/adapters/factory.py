"""Factory function to instantiate the correct LLM adapter from config.

Usage:
    from minilegion.adapters import get_adapter
    adapter = get_adapter(config)
    response = adapter.call(system_prompt, user_message)

Supported providers (config.provider):
    "openai"            — OpenAI API (default)
    "openai-compatible" — Any OpenAI-compatible endpoint (Groq, Together, etc.)
    "ollama"            — Local Ollama instance
    "gemini"            — Google Gemini API
    "anthropic"         — Anthropic Claude API
"""

from minilegion.adapters.base import LLMAdapter
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ConfigError

_PROVIDER_MAP: dict[str, str] = {
    "openai": "minilegion.adapters.openai_adapter.OpenAIAdapter",
    "openai-compatible": "minilegion.adapters.openai_compatible_adapter.OpenAICompatibleAdapter",
    "ollama": "minilegion.adapters.ollama_adapter.OllamaAdapter",
    "gemini": "minilegion.adapters.gemini_adapter.GeminiAdapter",
    "anthropic": "minilegion.adapters.anthropic_adapter.AnthropicAdapter",
}


def get_adapter(config: MiniLegionConfig) -> LLMAdapter:
    """Return the appropriate LLMAdapter instance for the given config.

    Args:
        config: Loaded MiniLegionConfig (provider field drives selection).

    Returns:
        An LLMAdapter instance ready to use.

    Raises:
        ConfigError: If config.provider is not a known provider.
    """
    provider = config.provider.lower()
    dotted = _PROVIDER_MAP.get(provider)

    if dotted is None:
        known = ", ".join(sorted(_PROVIDER_MAP))
        raise ConfigError(
            f"Unknown provider '{config.provider}'. Supported providers: {known}"
        )

    # Lazy import — only load the module for the selected provider.
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(config)
