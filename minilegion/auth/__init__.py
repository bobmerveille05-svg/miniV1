"""MiniLegion auth package.

Public API:
    login(provider)           — run OAuth flow and store credentials
    logout(provider)          — clear stored credentials
    get_token(provider)       -> str  — return usable token (refreshes if needed)
    is_authenticated(provider) -> bool
"""

from minilegion.auth.registry import get_provider


def login(provider: str) -> None:
    """Run the OAuth flow for the given provider and store credentials."""
    get_provider(provider).login()


def logout(provider: str) -> None:
    """Clear stored credentials for the given provider."""
    get_provider(provider).logout()


def get_token(provider: str) -> str:
    """Return a valid token for the given provider, refreshing if needed."""
    return get_provider(provider).get_token()


def is_authenticated(provider: str) -> bool:
    """Return True if the provider has valid, non-expired credentials."""
    return get_provider(provider).is_authenticated()
