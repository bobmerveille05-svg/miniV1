"""Provider registry — maps provider name strings to AuthProvider instances."""

from __future__ import annotations

from minilegion.auth.base import AuthProvider


def _build_registry() -> dict[str, type[AuthProvider]]:
    from minilegion.auth.providers.copilot import CopilotAuthProvider

    return {
        "copilot": CopilotAuthProvider,
        # "anthropic": AnthropicAuthProvider,  # future
        # "openai": OpenAIAuthProvider,         # future
    }


# Public registry — provider name → provider class
PROVIDERS: dict[str, type[AuthProvider]] = _build_registry()


def get_provider(provider: str) -> AuthProvider:
    """Return an AuthProvider instance for the given provider name.

    Args:
        provider: Provider slug, e.g. "copilot".

    Returns:
        An AuthProvider instance.

    Raises:
        ValueError: If provider is not in the registry.
    """
    cls = PROVIDERS.get(provider.lower())
    if cls is None:
        known = ", ".join(sorted(PROVIDERS))
        raise ValueError(
            f"Unknown auth provider '{provider}'. Known providers: {known}"
        )
    return cls()
