"""GitHub Models authentication provider using a GitHub Personal Access Token.

The GitHub Models inference API (models.inference.ai.azure.com) requires a
GitHub PAT — either a classic token or a fine-grained token with the
``models:read`` permission (no extra scopes needed for classic tokens).

Login flow:
1. Prompt user to open https://github.com/settings/tokens/new
2. User pastes their PAT
3. Token is stored in CredentialStore under key "copilot"
"""

from __future__ import annotations

import sys

from minilegion.auth.base import AuthProvider
from minilegion.auth.store import CredentialStore, TokenData
from minilegion.core.exceptions import (
    AuthNotConfiguredError,
    AuthProviderError,
)

_PAT_HELP_URL = "https://github.com/settings/tokens/new"
# GitHub PATs do not expire by default; we store with no expiry.
_NO_EXPIRY = None


class CopilotAuthProvider(AuthProvider):
    """GitHub Models auth via a GitHub Personal Access Token (PAT)."""

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store or CredentialStore()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Prompt the user for a GitHub PAT and persist it."""
        print("\n! GitHub Models requires a GitHub Personal Access Token (PAT).")
        print(f"  Create one at: {_PAT_HELP_URL}")
        print("  Classic tokens work with no extra scopes.")
        print("  Fine-grained tokens need the 'models:read' permission.\n")

        try:
            token_str = _prompt_for_token()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            raise AuthProviderError("Login cancelled.")

        token_str = token_str.strip()
        if not token_str:
            raise AuthProviderError("No token entered. Login cancelled.")

        if not (token_str.startswith("ghp_") or token_str.startswith("github_pat_")):
            # Warn but don't block — tokens formats can change
            print(
                "  Warning: token doesn't look like a classic PAT (ghp_...) "
                "or fine-grained PAT (github_pat_...). Storing anyway.\n"
            )

        token_data = TokenData(
            access_token=token_str,
            token_type="bearer",
            expires_at=_NO_EXPIRY,
            refresh_token=None,
            scopes=[],
        )
        self._store.save("copilot", token_data)
        print("✓ GitHub PAT saved. You can now use GitHub Models.\n")

    def logout(self) -> None:
        """Remove stored PAT credentials."""
        self._store.delete("copilot")

    def get_token(self, *, interactive: bool = True) -> str:
        """Return the stored PAT.

        Args:
            interactive: If True and no token exists, runs login flow.
                         If False and no token exists, raises AuthNotConfiguredError.
        """
        token = self._store.load("copilot")
        if token is None:
            if interactive:
                self.login()
                token = self._store.load("copilot")
                if token is None:
                    raise AuthNotConfiguredError("copilot")
            else:
                raise AuthNotConfiguredError("copilot")

        return token.access_token

    def is_authenticated(self) -> bool:
        """Return True if a PAT is stored (PATs don't expire unless revoked)."""
        return self._store.load("copilot") is not None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _prompt_for_token() -> str:
    """Read a token from stdin, hiding input if possible."""
    try:
        import getpass

        return getpass.getpass("  Paste your GitHub PAT (input hidden): ")
    except Exception:
        # Fallback to visible input (e.g. in non-TTY environments)
        sys.stdout.write("  Paste your GitHub PAT: ")
        sys.stdout.flush()
        return sys.stdin.readline()
