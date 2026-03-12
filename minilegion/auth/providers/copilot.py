"""GitHub Copilot authentication provider using GitHub Device Flow.

OAuth flow (pure Python stdlib — no new dependencies):
1. POST /login/device/code  → device_code, user_code, verification_uri
2. Display URL + code to user
3. Poll /login/oauth/access_token until approved or expired
4. Store token in CredentialStore
"""

from __future__ import annotations

import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from minilegion.auth.base import AuthProvider
from minilegion.auth.store import CredentialStore, TokenData
from minilegion.core.exceptions import (
    AuthExpiredError,
    AuthNotConfiguredError,
    AuthProviderError,
)

# GitHub OAuth client ID for Copilot — same as used by Zed, OpenCode, etc.
_COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"

_DEVICE_CODE_URL = "https://github.com/login/device/code"
_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
_COPILOT_SCOPE = "copilot"

# Copilot tokens live ~8 hours; we track expiry from issue time
_TOKEN_LIFETIME_SECONDS = 8 * 3600


class CopilotAuthProvider(AuthProvider):
    """GitHub Copilot auth via GitHub Device Flow."""

    def __init__(self, store: CredentialStore | None = None) -> None:
        self._store = store or CredentialStore()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Run Device Flow and persist token."""
        try:
            code_data = self._request_device_code()
        except Exception as exc:
            raise AuthProviderError(f"Could not reach GitHub: {exc}") from exc

        print(f"\n! Open this URL in your browser:")
        print(f"  {code_data['verification_uri']}\n")
        print(f"! Enter this code when prompted:")
        print(f"  {code_data['user_code']}\n")

        token = self._poll_for_token(
            device_code=code_data["device_code"],
            interval=code_data["interval"],
            expires_in=code_data["expires_in"],
        )
        self._store.save("copilot", token)
        print(f"\n✓ Authenticated with GitHub Copilot.\n")

    def logout(self) -> None:
        """Remove stored Copilot credentials."""
        self._store.delete("copilot")

    def get_token(self, *, interactive: bool = True) -> str:
        """Return a valid access token.

        If token is expired and interactive=True, re-runs Device Flow.
        If token is expired and interactive=False, raises AuthExpiredError.
        If no token exists at all, raises AuthNotConfiguredError.

        Args:
            interactive: Whether to re-authenticate if expired (default True).
        """
        token = self._store.load("copilot")
        if token is None:
            raise AuthNotConfiguredError("copilot")

        if self._store.is_expired("copilot"):
            if not interactive:
                raise AuthExpiredError("copilot")
            # Re-run login silently
            self.login()
            token = self._store.load("copilot")
            if token is None:
                raise AuthNotConfiguredError("copilot")

        return token.access_token

    def is_authenticated(self) -> bool:
        """Return True if valid, non-expired credentials exist."""
        return self._store.load("copilot") is not None and not self._store.is_expired(
            "copilot"
        )

    # ------------------------------------------------------------------
    # Private — Device Flow steps
    # ------------------------------------------------------------------

    def _request_device_code(self) -> dict[str, Any]:
        """POST to GitHub device code endpoint. Returns parsed response dict."""
        data = urllib.parse.urlencode(
            {"client_id": _COPILOT_CLIENT_ID, "scope": _COPILOT_SCOPE}
        ).encode()
        req = urllib.request.Request(
            _DEVICE_CODE_URL,
            data=data,
            headers={"Accept": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()

        parsed = dict(urllib.parse.parse_qsl(raw))
        return {
            "device_code": parsed["device_code"],
            "user_code": parsed["user_code"],
            "verification_uri": parsed.get(
                "verification_uri", "https://github.com/login/device"
            ),
            "expires_in": int(parsed.get("expires_in", 899)),
            "interval": int(parsed.get("interval", 5)),
        }

    def _poll_for_token(
        self, *, device_code: str, interval: int, expires_in: int
    ) -> TokenData:
        """Poll GitHub until the user completes auth or the code expires."""
        deadline = time.monotonic() + expires_in
        current_interval = interval

        while time.monotonic() < deadline:
            data = urllib.parse.urlencode(
                {
                    "client_id": _COPILOT_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": ("urn:ietf:params:oauth:grant-type:device_code"),
                }
            ).encode()
            req = urllib.request.Request(
                _ACCESS_TOKEN_URL,
                data=data,
                headers={"Accept": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode()

            parsed = dict(urllib.parse.parse_qsl(raw))
            error = parsed.get("error")

            if error == "authorization_pending":
                time.sleep(current_interval)
                continue
            elif error == "slow_down":
                current_interval += 5
                time.sleep(current_interval)
                continue
            elif error == "expired_token":
                raise AuthProviderError(
                    "Device code expired. Run `minilegion auth login copilot` again."
                )
            elif error == "access_denied":
                raise AuthProviderError(
                    "Your GitHub account does not have an active Copilot subscription."
                )
            elif error:
                raise AuthProviderError(f"GitHub OAuth error: {error}")
            elif "access_token" in parsed:
                expires_at = datetime.now(tz=timezone.utc) + timedelta(
                    seconds=_TOKEN_LIFETIME_SECONDS
                )
                scopes = [
                    s.strip()
                    for s in parsed.get("scope", _COPILOT_SCOPE).split(",")
                    if s.strip()
                ]
                return TokenData(
                    access_token=parsed["access_token"],
                    token_type=parsed.get("token_type", "bearer"),
                    expires_at=expires_at,
                    refresh_token=None,
                    scopes=scopes,
                )

        raise AuthProviderError(
            "Timed out waiting for authorization. "
            "Run `minilegion auth login copilot` again."
        )
