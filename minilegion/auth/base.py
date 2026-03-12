"""Abstract base class for OAuth authentication providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """Abstract base class all auth providers must implement."""

    @abstractmethod
    def login(self) -> None:
        """Run the full OAuth flow and persist credentials."""
        ...

    @abstractmethod
    def logout(self) -> None:
        """Remove persisted credentials for this provider."""
        ...

    @abstractmethod
    def get_token(self) -> str:
        """Return a valid access token, refreshing/re-authing if needed.

        Raises:
            AuthExpiredError: If token is expired and environment is non-interactive.
            AuthNotConfiguredError: If no credentials exist at all.
        """
        ...

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Return True if credentials exist and are not expired."""
        ...
