# Auth OAuth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:executing-plans to implement this plan task-by-task.

**Goal:** Add `minilegion auth login copilot` using GitHub Device Flow OAuth, with a generic provider registry and credential store so Anthropic/OpenAI can be added later without rearchitecting.

**Architecture:** A new `minilegion/auth/` package contains an abstract `AuthProvider` base class, a `CredentialStore` that writes `~/.minilegion/credentials.json` (mode 600), a `CopilotAuthProvider` implementing GitHub Device Flow, and a provider registry dict. The adapter factory gains one non-breaking fallback path. The CLI gains a new `auth` sub-app.

**Tech Stack:** Python stdlib only (`urllib`, `json`, `pathlib`, `datetime`, `abc`, `dataclasses`). Typer for CLI. Pytest + `unittest.mock` for tests. No new dependencies.

---

### Task 1: Auth exceptions

**Files:**
- Modify: `minilegion/core/exceptions.py`
- Create: `tests/auth/__init__.py`
- Create: `tests/auth/test_auth_exceptions.py`

**Step 1: Write the failing test**

```python
# tests/auth/test_auth_exceptions.py
from minilegion.core.exceptions import (
    AuthError,
    AuthExpiredError,
    AuthProviderError,
    AuthNotConfiguredError,
    MiniLegionError,
)

def test_auth_error_is_minilegion_error():
    assert issubclass(AuthError, MiniLegionError)

def test_auth_expired_is_auth_error():
    err = AuthExpiredError("copilot")
    assert isinstance(err, AuthError)
    assert "copilot" in str(err)

def test_auth_provider_error_is_auth_error():
    err = AuthProviderError("network failure")
    assert isinstance(err, AuthError)

def test_auth_not_configured_is_auth_error():
    err = AuthNotConfiguredError("copilot")
    assert isinstance(err, AuthError)
    assert "copilot" in str(err)
```

**Step 2: Run test to verify it fails**

```
pytest tests/auth/test_auth_exceptions.py -v
```
Expected: ImportError — `AuthError` not yet defined.

**Step 3: Add exceptions to `minilegion/core/exceptions.py`**

Append after the existing `FileIOError` class:

```python
class AuthError(MiniLegionError):
    """Base exception for authentication errors."""
    pass


class AuthExpiredError(AuthError):
    """Token has expired — user must re-authenticate."""
    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Authentication expired for '{provider}'. "
            f"Run: minilegion auth login {provider}"
        )
        self.provider = provider


class AuthProviderError(AuthError):
    """OAuth flow failure (network error, access denied, etc.)."""
    pass


class AuthNotConfiguredError(AuthError):
    """No credentials found for this provider."""
    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Not authenticated with '{provider}'. "
            f"Run: minilegion auth login {provider}"
        )
        self.provider = provider
```

Also create `tests/auth/__init__.py` as an empty file.

**Step 4: Run tests**

```
pytest tests/auth/test_auth_exceptions.py -v
```
Expected: 4 PASSED.

**Step 5: Commit**

```bash
git add minilegion/core/exceptions.py tests/auth/__init__.py tests/auth/test_auth_exceptions.py
git commit -m "feat(auth): add auth exception hierarchy"
```

---

### Task 2: CredentialStore

**Files:**
- Create: `minilegion/auth/__init__.py`
- Create: `minilegion/auth/store.py`
- Create: `tests/auth/test_store.py`

**Step 1: Write the failing tests**

```python
# tests/auth/test_store.py
import json
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from minilegion.auth.store import CredentialStore, TokenData


@pytest.fixture
def store(tmp_path):
    return CredentialStore(credentials_dir=tmp_path)


def test_save_and_load_roundtrip(store):
    token = TokenData(
        access_token="ghu_abc123",
        token_type="bearer",
        expires_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        refresh_token=None,
        scopes=["copilot"],
    )
    store.save("copilot", token)
    loaded = store.load("copilot")
    assert loaded is not None
    assert loaded.access_token == "ghu_abc123"
    assert loaded.token_type == "bearer"
    assert loaded.scopes == ["copilot"]
    assert loaded.refresh_token is None


def test_load_returns_none_when_missing(store):
    assert store.load("copilot") is None


def test_delete_removes_entry(store):
    token = TokenData(
        access_token="ghu_abc123",
        token_type="bearer",
        expires_at=None,
        refresh_token=None,
        scopes=[],
    )
    store.save("copilot", token)
    store.delete("copilot")
    assert store.load("copilot") is None


def test_delete_nonexistent_is_noop(store):
    store.delete("copilot")  # should not raise


def test_is_expired_true_for_past_token(store):
    token = TokenData(
        access_token="x",
        token_type="bearer",
        expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        refresh_token=None,
        scopes=[],
    )
    store.save("copilot", token)
    assert store.is_expired("copilot") is True


def test_is_expired_false_for_future_token(store):
    token = TokenData(
        access_token="x",
        token_type="bearer",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        refresh_token=None,
        scopes=[],
    )
    store.save("copilot", token)
    assert store.is_expired("copilot") is False


def test_is_expired_false_when_no_expiry(store):
    token = TokenData(
        access_token="x",
        token_type="bearer",
        expires_at=None,
        refresh_token=None,
        scopes=[],
    )
    store.save("copilot", token)
    assert store.is_expired("copilot") is False


def test_is_expired_true_when_not_saved(store):
    # No credentials = treat as expired (forces re-login)
    assert store.is_expired("copilot") is True


@pytest.mark.skipif(sys.platform == "win32", reason="chmod not applicable on Windows")
def test_credentials_file_mode_is_600(store):
    token = TokenData(
        access_token="x",
        token_type="bearer",
        expires_at=None,
        refresh_token=None,
        scopes=[],
    )
    store.save("copilot", token)
    creds_file = tmp_path / "credentials.json"  # won't exist — use store._path
    path = store._path
    mode = oct(stat.S_IMODE(path.stat().st_mode))
    assert mode == "0o600"
```

**Step 2: Run tests to verify they fail**

```
pytest tests/auth/test_store.py -v
```
Expected: ImportError — `minilegion.auth.store` not yet defined.

**Step 3: Create `minilegion/auth/__init__.py`**

```python
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
```

**Step 4: Create `minilegion/auth/store.py`**

```python
"""Credential store — reads/writes ~/.minilegion/credentials.json.

Stores one entry per provider. File permissions are set to 600 on
POSIX systems. On Windows, NTFS per-user ACLs provide isolation.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TokenData:
    """OAuth token data for a single provider."""

    access_token: str
    token_type: str
    expires_at: datetime | None
    refresh_token: str | None
    scopes: list[str]


_DEFAULT_DIR = Path.home() / ".minilegion"


class CredentialStore:
    """Reads and writes credentials.json.

    Args:
        credentials_dir: Directory containing credentials.json.
            Defaults to ~/.minilegion/
    """

    def __init__(self, credentials_dir: Path | None = None) -> None:
        self._dir = credentials_dir or _DEFAULT_DIR
        self._path = self._dir / "credentials.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, provider: str, token: TokenData) -> None:
        """Persist token data for provider. Creates file with mode 600."""
        data = self._read_all()
        data[provider] = self._token_to_dict(token)
        self._write_all(data)

    def load(self, provider: str) -> TokenData | None:
        """Return token data for provider, or None if not found."""
        data = self._read_all()
        entry = data.get(provider)
        if entry is None:
            return None
        return self._dict_to_token(entry)

    def delete(self, provider: str) -> None:
        """Remove credentials for provider. No-op if not found."""
        data = self._read_all()
        if provider in data:
            del data[provider]
            self._write_all(data)

    def is_expired(self, provider: str) -> bool:
        """Return True if token is missing or past its expires_at."""
        token = self.load(provider)
        if token is None:
            return True
        if token.expires_at is None:
            return False
        now = datetime.now(tz=timezone.utc)
        return now >= token.expires_at

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_all(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        if sys.platform != "win32":
            os.chmod(self._path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

    @staticmethod
    def _token_to_dict(token: TokenData) -> dict[str, Any]:
        d: dict[str, Any] = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "refresh_token": token.refresh_token,
            "scopes": token.scopes,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        }
        return d

    @staticmethod
    def _dict_to_token(d: dict[str, Any]) -> TokenData:
        expires_at: datetime | None = None
        if d.get("expires_at"):
            expires_at = datetime.fromisoformat(d["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        return TokenData(
            access_token=d["access_token"],
            token_type=d.get("token_type", "bearer"),
            expires_at=expires_at,
            refresh_token=d.get("refresh_token"),
            scopes=d.get("scopes", []),
        )
```

**Step 5: Run tests**

```
pytest tests/auth/test_store.py -v
```
Expected: All passing except `test_credentials_file_mode_is_600` which has a bug in the test referencing `tmp_path` — fix the test to use `store._path`:

```python
def test_credentials_file_mode_is_600(tmp_path):
    store = CredentialStore(credentials_dir=tmp_path)
    token = TokenData(
        access_token="x",
        token_type="bearer",
        expires_at=None,
        refresh_token=None,
        scopes=[],
    )
    store.save("copilot", token)
    mode = oct(stat.S_IMODE(store._path.stat().st_mode))
    assert mode == "0o600"
```

Run again:
```
pytest tests/auth/test_store.py -v
```
Expected: All PASSED (chmod test skipped on Windows).

**Step 6: Commit**

```bash
git add minilegion/auth/__init__.py minilegion/auth/store.py tests/auth/test_store.py
git commit -m "feat(auth): add CredentialStore with TokenData"
```

---

### Task 3: AuthProvider base class and registry

**Files:**
- Create: `minilegion/auth/base.py`
- Create: `minilegion/auth/providers/__init__.py`
- Create: `minilegion/auth/registry.py`
- Create: `tests/auth/test_registry.py`

**Step 1: Write the failing tests**

```python
# tests/auth/test_registry.py
import pytest
from minilegion.auth.registry import get_provider, PROVIDERS
from minilegion.auth.base import AuthProvider


def test_providers_dict_has_copilot():
    assert "copilot" in PROVIDERS


def test_get_provider_copilot_returns_auth_provider():
    provider = get_provider("copilot")
    assert isinstance(provider, AuthProvider)


def test_get_provider_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown auth provider"):
        get_provider("unknown-provider")


def test_auth_provider_is_abstract():
    # Cannot instantiate directly
    with pytest.raises(TypeError):
        AuthProvider()
```

**Step 2: Run to verify they fail**

```
pytest tests/auth/test_registry.py -v
```
Expected: ImportError.

**Step 3: Create `minilegion/auth/base.py`**

```python
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
```

**Step 4: Create `minilegion/auth/providers/__init__.py`**

Empty file — just marks the directory as a package.

**Step 5: Create `minilegion/auth/registry.py`**

```python
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
```

**Step 6: Run tests**

```
pytest tests/auth/test_registry.py -v
```
Expected: PASSED (CopilotAuthProvider will be created in the next task — if it fails with ImportError, proceed to Task 4 first and come back).

**Step 7: Commit**

```bash
git add minilegion/auth/base.py minilegion/auth/providers/__init__.py minilegion/auth/registry.py tests/auth/test_registry.py
git commit -m "feat(auth): add AuthProvider ABC and provider registry"
```

---

### Task 4: CopilotAuthProvider — GitHub Device Flow

**Files:**
- Create: `minilegion/auth/providers/copilot.py`
- Create: `tests/auth/test_copilot_provider.py`

**Step 1: Write the failing tests**

```python
# tests/auth/test_copilot_provider.py
"""Tests for CopilotAuthProvider — all GitHub HTTP calls are mocked."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from minilegion.auth.providers.copilot import CopilotAuthProvider
from minilegion.auth.store import CredentialStore, TokenData
from minilegion.core.exceptions import AuthExpiredError, AuthNotConfiguredError, AuthProviderError


@pytest.fixture
def store(tmp_path):
    return CredentialStore(credentials_dir=tmp_path)


@pytest.fixture
def provider(store):
    return CopilotAuthProvider(store=store)


# ---------------------------------------------------------------------------
# Device code request
# ---------------------------------------------------------------------------

def test_request_device_code_returns_expected_fields(provider):
    mock_response = MagicMock()
    mock_response.read.return_value = (
        b"device_code=abc&user_code=8F43-6FCF"
        b"&verification_uri=https%3A%2F%2Fgithub.com%2Flogin%2Fdevice"
        b"&expires_in=899&interval=5"
    )
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = provider._request_device_code()

    assert result["device_code"] == "abc"
    assert result["user_code"] == "8F43-6FCF"
    assert result["interval"] == 5
    assert result["expires_in"] == 899


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

def test_poll_returns_token_on_success(provider):
    mock_response = MagicMock()
    mock_response.read.return_value = (
        b"access_token=ghu_abc123&token_type=bearer&scope=copilot"
    )
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("time.sleep"):
            token_data = provider._poll_for_token(
                device_code="abc", interval=5, expires_in=900
            )

    assert token_data.access_token == "ghu_abc123"
    assert token_data.token_type == "bearer"
    assert "copilot" in token_data.scopes


def test_poll_retries_on_authorization_pending(provider):
    """Should keep polling when authorization_pending is returned."""
    pending_response = MagicMock()
    pending_response.read.return_value = b"error=authorization_pending"
    pending_response.__enter__ = lambda s: s
    pending_response.__exit__ = MagicMock(return_value=False)

    success_response = MagicMock()
    success_response.read.return_value = (
        b"access_token=ghu_xyz&token_type=bearer&scope=copilot"
    )
    success_response.__enter__ = lambda s: s
    success_response.__exit__ = MagicMock(return_value=False)

    responses = [pending_response, pending_response, success_response]

    with patch("urllib.request.urlopen", side_effect=responses):
        with patch("time.sleep") as mock_sleep:
            token_data = provider._poll_for_token(
                device_code="abc", interval=5, expires_in=900
            )

    assert token_data.access_token == "ghu_xyz"
    assert mock_sleep.call_count == 2


def test_poll_increases_interval_on_slow_down(provider):
    """slow_down response must increase polling interval by 5."""
    slow_response = MagicMock()
    slow_response.read.return_value = b"error=slow_down"
    slow_response.__enter__ = lambda s: s
    slow_response.__exit__ = MagicMock(return_value=False)

    success_response = MagicMock()
    success_response.read.return_value = (
        b"access_token=ghu_xyz&token_type=bearer&scope=copilot"
    )
    success_response.__enter__ = lambda s: s
    success_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", side_effect=[slow_response, success_response]):
        with patch("time.sleep") as mock_sleep:
            provider._poll_for_token(device_code="abc", interval=5, expires_in=900)

    # First sleep should be 10 (5 + 5 increase), not 5
    assert mock_sleep.call_args_list[0] == call(10)


def test_poll_raises_on_expired_token(provider):
    mock_response = MagicMock()
    mock_response.read.return_value = b"error=expired_token"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("time.sleep"):
            with pytest.raises(AuthProviderError, match="expired"):
                provider._poll_for_token(
                    device_code="abc", interval=5, expires_in=900
                )


def test_poll_raises_on_access_denied(provider):
    mock_response = MagicMock()
    mock_response.read.return_value = b"error=access_denied"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("time.sleep"):
            with pytest.raises(AuthProviderError, match="Copilot subscription"):
                provider._poll_for_token(
                    device_code="abc", interval=5, expires_in=900
                )


# ---------------------------------------------------------------------------
# is_authenticated / get_token
# ---------------------------------------------------------------------------

def test_is_authenticated_false_when_no_credentials(provider):
    assert provider.is_authenticated() is False


def test_is_authenticated_true_when_valid_token(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghu_x",
            token_type="bearer",
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            refresh_token=None,
            scopes=["copilot"],
        ),
    )
    assert provider.is_authenticated() is True


def test_get_token_returns_token_when_valid(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghu_valid",
            token_type="bearer",
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            refresh_token=None,
            scopes=["copilot"],
        ),
    )
    assert provider.get_token() == "ghu_valid"


def test_get_token_raises_not_configured_when_missing(provider):
    with pytest.raises(AuthNotConfiguredError):
        provider.get_token()


def test_get_token_raises_expired_error_in_noninteractive(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghu_old",
            token_type="bearer",
            expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            refresh_token=None,
            scopes=["copilot"],
        ),
    )
    with pytest.raises(AuthExpiredError):
        provider.get_token(interactive=False)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

def test_logout_removes_credentials(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghu_x",
            token_type="bearer",
            expires_at=None,
            refresh_token=None,
            scopes=[],
        ),
    )
    provider.logout()
    assert store.load("copilot") is None
```

**Step 2: Run to verify they fail**

```
pytest tests/auth/test_copilot_provider.py -v
```
Expected: ImportError — `CopilotAuthProvider` not yet defined.

**Step 3: Create `minilegion/auth/providers/copilot.py`**

```python
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
        return (
            self._store.load("copilot") is not None
            and not self._store.is_expired("copilot")
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
            time.sleep(current_interval)

            data = urllib.parse.urlencode(
                {
                    "client_id": _COPILOT_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": (
                        "urn:ietf:params:oauth:grant-type:device_code"
                    ),
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
                continue
            elif error == "slow_down":
                current_interval += 5
                continue
            elif error == "expired_token":
                raise AuthProviderError(
                    "Device code expired. "
                    "Run `minilegion auth login copilot` again."
                )
            elif error == "access_denied":
                raise AuthProviderError(
                    "Your GitHub account does not have an active "
                    "Copilot subscription."
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
```

**Step 4: Run tests**

```
pytest tests/auth/test_copilot_provider.py -v
```
Expected: All PASSED.

Also run registry tests now that the provider exists:

```
pytest tests/auth/test_registry.py -v
```
Expected: All PASSED.

**Step 5: Commit**

```bash
git add minilegion/auth/providers/copilot.py tests/auth/test_copilot_provider.py
git commit -m "feat(auth): add CopilotAuthProvider with GitHub Device Flow"
```

---

### Task 5: Copilot LLM adapter

**Files:**
- Create: `minilegion/adapters/copilot_adapter.py`
- Create: `tests/test_copilot_adapter.py`

**Step 1: Write the failing tests**

```python
# tests/test_copilot_adapter.py
"""Tests for CopilotAdapter — GitHub Copilot LLM via OpenAI-compatible API."""

from unittest.mock import MagicMock, patch

import pytest

from minilegion.adapters.copilot_adapter import CopilotAdapter
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import AuthNotConfiguredError, LLMError


@pytest.fixture
def config():
    return MiniLegionConfig(
        provider="copilot",
        model="gpt-4o",
        api_key_env="",  # empty — adapter should use credential store
    )


def test_get_client_fetches_token_from_store(config):
    with patch("minilegion.adapters.copilot_adapter.get_token", return_value="ghu_tok"):
        with patch("minilegion.adapters.copilot_adapter.OpenAI") as mock_openai:
            adapter = CopilotAdapter(config)
            adapter._get_client()
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args.kwargs
            assert call_kwargs["api_key"] == "ghu_tok"
            assert "githubcopilot.com" in call_kwargs["base_url"]


def test_get_client_raises_llm_error_when_not_authenticated(config):
    with patch(
        "minilegion.adapters.copilot_adapter.get_token",
        side_effect=AuthNotConfiguredError("copilot"),
    ):
        adapter = CopilotAdapter(config)
        with pytest.raises(LLMError, match="minilegion auth login copilot"):
            adapter._get_client()


def test_adapter_is_registered_in_factory():
    from minilegion.adapters.factory import _PROVIDER_MAP
    assert "copilot" in _PROVIDER_MAP
```

**Step 2: Run to verify they fail**

```
pytest tests/test_copilot_adapter.py -v
```
Expected: ImportError.

**Step 3: Create `minilegion/adapters/copilot_adapter.py`**

```python
"""GitHub Copilot LLM adapter.

Uses the OpenAI-compatible GitHub Copilot API endpoint with a token
retrieved from the credential store (set via `minilegion auth login copilot`).

API endpoint: https://api.githubcopilot.com
"""

from __future__ import annotations

import openai
from openai import OpenAI

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.auth import get_token
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import AuthError, LLMError

_COPILOT_BASE_URL = "https://api.githubcopilot.com"


class CopilotAdapter(LLMAdapter):
    """LLM adapter for GitHub Copilot via the OpenAI-compatible API.

    Retrieves the access token from the credential store. The token is
    fetched lazily on first call so construction never triggers I/O.
    """

    def __init__(self, config: MiniLegionConfig) -> None:
        self._config = config
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        try:
            token = get_token("copilot")
        except AuthError as exc:
            raise LLMError(
                f"GitHub Copilot authentication required. "
                f"Run: minilegion auth login copilot\n({exc})"
            ) from exc

        self._client = OpenAI(
            api_key=token,
            base_url=_COPILOT_BASE_URL,
            timeout=float(self._config.timeout),
            max_retries=0,
        )
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
            response_format=None,
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
            response_format={"type": "json_object"},
        )

    def _do_call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None,
        timeout: int | None,
        response_format: dict | None,
    ) -> LLMResponse:
        client = self._get_client()
        kwargs: dict = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        if max_tokens is not None:
            kwargs["max_completion_tokens"] = max_tokens
        if timeout is not None:
            kwargs["timeout"] = float(timeout)
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise LLMError(
                f"GitHub Copilot authentication failed. "
                f"Run: minilegion auth login copilot\n({exc})"
            ) from exc
        except openai.APITimeoutError as exc:
            effective_timeout = timeout or self._config.timeout
            raise LLMError(f"Request timed out after {effective_timeout}s: {exc}") from exc
        except openai.APIError as exc:
            raise LLMError(f"Copilot API error: {exc}") from exc

        return self._map_response(response)

    def _map_response(self, response) -> LLMResponse:
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            model=response.model,
            finish_reason=choice.finish_reason,
        )
```

**Step 4: Register the adapter in `minilegion/adapters/factory.py`**

Add `"copilot"` to `_PROVIDER_MAP`:

```python
_PROVIDER_MAP: dict[str, str] = {
    "openai": "minilegion.adapters.openai_adapter.OpenAIAdapter",
    "openai-compatible": "minilegion.adapters.openai_compatible_adapter.OpenAICompatibleAdapter",
    "ollama": "minilegion.adapters.ollama_adapter.OllamaAdapter",
    "gemini": "minilegion.adapters.gemini_adapter.GeminiAdapter",
    "anthropic": "minilegion.adapters.anthropic_adapter.AnthropicAdapter",
    "copilot": "minilegion.adapters.copilot_adapter.CopilotAdapter",
}
```

**Step 5: Run tests**

```
pytest tests/test_copilot_adapter.py -v
```
Expected: All PASSED.

**Step 6: Commit**

```bash
git add minilegion/adapters/copilot_adapter.py minilegion/adapters/factory.py tests/test_copilot_adapter.py
git commit -m "feat(auth): add CopilotAdapter and register in factory"
```

---

### Task 6: CLI auth commands

**Files:**
- Create: `minilegion/cli/auth_commands.py`
- Modify: `minilegion/cli/__init__.py`
- Create: `tests/test_cli_auth.py`

**Step 1: Write the failing tests**

```python
# tests/test_cli_auth.py
"""Tests for minilegion auth CLI commands."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# auth login
# ---------------------------------------------------------------------------

def test_auth_login_copilot_calls_login(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("minilegion.cli.auth_commands.auth_login_provider") as mock_login:
        result = runner.invoke(app, ["auth", "login", "copilot"])
    assert result.exit_code == 0
    mock_login.assert_called_once_with("copilot")


def test_auth_login_unknown_provider_exits_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "minilegion.cli.auth_commands.auth_login_provider",
        side_effect=ValueError("Unknown auth provider 'fakebot'"),
    ):
        result = runner.invoke(app, ["auth", "login", "fakebot"])
    assert result.exit_code == 1
    assert "Unknown" in result.output


def test_auth_login_provider_error_exits_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from minilegion.core.exceptions import AuthProviderError

    with patch(
        "minilegion.cli.auth_commands.auth_login_provider",
        side_effect=AuthProviderError("network failure"),
    ):
        result = runner.invoke(app, ["auth", "login", "copilot"])
    assert result.exit_code == 1
    assert "network failure" in result.output


# ---------------------------------------------------------------------------
# auth logout
# ---------------------------------------------------------------------------

def test_auth_logout_copilot_calls_logout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("minilegion.cli.auth_commands.auth_logout_provider") as mock_logout:
        result = runner.invoke(app, ["auth", "logout", "copilot"])
    assert result.exit_code == 0
    mock_logout.assert_called_once_with("copilot")


# ---------------------------------------------------------------------------
# auth status
# ---------------------------------------------------------------------------

def test_auth_status_shows_all_providers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "minilegion.cli.auth_commands.get_auth_status",
        return_value={"copilot": False, "anthropic": False, "openai": False},
    ):
        result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "copilot" in result.output


def test_auth_status_shows_authenticated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "minilegion.cli.auth_commands.get_auth_status",
        return_value={"copilot": True, "anthropic": False, "openai": False},
    ):
        result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "authenticated" in result.output.lower()
```

**Step 2: Run to verify they fail**

```
pytest tests/test_cli_auth.py -v
```
Expected: ImportError or "No such command 'auth'".

**Step 3: Create `minilegion/cli/auth_commands.py`**

```python
"""MiniLegion auth sub-commands.

Commands:
    minilegion auth login <provider>   — run OAuth flow, store credentials
    minilegion auth logout <provider>  — clear stored credentials
    minilegion auth status             — show auth state for all providers
"""

from __future__ import annotations

import typer

from minilegion.auth.registry import PROVIDERS
from minilegion.auth.store import CredentialStore
from minilegion.core.exceptions import AuthError, AuthProviderError

auth_app = typer.Typer(
    name="auth",
    help="Authenticate with LLM providers.",
    no_args_is_help=True,
)

# Known providers to display in status (registry + future ones)
_STATUS_PROVIDERS = ["copilot", "anthropic", "openai"]


# ---------------------------------------------------------------------------
# Helpers (thin wrappers — easy to mock in tests)
# ---------------------------------------------------------------------------


def auth_login_provider(provider: str) -> None:
    """Run login for the given provider. Raises ValueError or AuthError."""
    from minilegion.auth.registry import get_provider
    get_provider(provider).login()


def auth_logout_provider(provider: str) -> None:
    """Run logout for the given provider."""
    from minilegion.auth.registry import get_provider
    get_provider(provider).logout()


def get_auth_status(store: CredentialStore | None = None) -> dict[str, bool]:
    """Return {provider: is_authenticated} for all known providers."""
    _store = store or CredentialStore()
    result: dict[str, bool] = {}
    for p in _STATUS_PROVIDERS:
        token = _store.load(p)
        result[p] = token is not None and not _store.is_expired(p)
    return result


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@auth_app.command("login")
def auth_login(
    provider: str = typer.Argument(..., help="Provider to authenticate with (e.g. copilot)"),
) -> None:
    """Authenticate with an LLM provider using OAuth."""
    try:
        auth_login_provider(provider)
    except ValueError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)
    except AuthError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@auth_app.command("logout")
def auth_logout(
    provider: str = typer.Argument(..., help="Provider to log out from (e.g. copilot)"),
) -> None:
    """Remove stored credentials for a provider."""
    try:
        auth_logout_provider(provider)
        typer.echo(typer.style(f"Logged out from {provider}.", fg=typer.colors.GREEN))
    except ValueError as exc:
        typer.echo(typer.style(str(exc), fg=typer.colors.RED))
        raise typer.Exit(code=1)


@auth_app.command("status")
def auth_status() -> None:
    """Show authentication status for all known providers."""
    status = get_auth_status()
    typer.echo("")
    for provider, authenticated in status.items():
        if authenticated:
            mark = typer.style("✓ authenticated", fg=typer.colors.GREEN)
        else:
            mark = typer.style("✗ not logged in", fg=typer.colors.RED)
        typer.echo(f"  {provider:<12} {mark}")
    typer.echo("")
```

**Step 4: Wire into `minilegion/cli/__init__.py`**

Add after the existing `app.add_typer(config_app, name="config")` line:

```python
from minilegion.cli.auth_commands import auth_app  # noqa: E402

app.add_typer(auth_app, name="auth")
```

**Step 5: Run tests**

```
pytest tests/test_cli_auth.py -v
```
Expected: All PASSED.

**Step 6: Commit**

```bash
git add minilegion/cli/auth_commands.py minilegion/cli/__init__.py tests/test_cli_auth.py
git commit -m "feat(auth): add auth CLI commands (login/logout/status)"
```

---

### Task 7: config init — skip API key prompt for copilot

**Files:**
- Modify: `minilegion/cli/config_commands.py`
- Modify: `tests/test_config_commands.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_config_commands.py — inside class TestConfigInit:

def test_copilot_skips_api_key_prompt(self, tmp_path, monkeypatch):
    """Selecting copilot as provider should skip the API key env var prompt."""
    _make_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    # provider=6 (copilot), model source=1 (recommended), model=1
    result = runner.invoke(app, ["config", "init"], input="6\n1\n1\n")
    assert result.exit_code == 0
    assert "minilegion auth login copilot" in result.output

    config = _read_config(tmp_path / "project-ai")
    assert config.provider == "copilot"
    assert config.api_key_env == ""
```

**Step 2: Run to verify it fails**

```
pytest tests/test_config_commands.py::TestConfigInit::test_copilot_skips_api_key_prompt -v
```
Expected: FAIL — copilot not yet in PROVIDERS, and API key prompt is not skipped.

**Step 3: Update `minilegion/cli/config_commands.py`**

Add `"copilot"` to the provider catalogues:

```python
PROVIDERS: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "ollama": "Ollama",
    "openai-compatible": "OpenRouter / OpenAI-compatible",
    "copilot": "GitHub Copilot",
}

DEFAULT_BASE_URL: dict[str, str | None] = {
    "openai": None,
    "anthropic": None,
    "gemini": None,
    "ollama": "http://localhost:11434",
    "openai-compatible": "https://openrouter.ai/api/v1",
    "copilot": None,
}

DEFAULT_ENV_VAR: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": "",
    "openai-compatible": "OPENROUTER_API_KEY",
    "copilot": "",  # uses credential store, not env var
}
```

In the `config_init` function, extend the "Step 2: API key" block to also skip for copilot:

```python
    # --- Step 2: API key env var ---
    default_env = DEFAULT_ENV_VAR[provider]
    if provider in ("ollama", "copilot"):
        api_key_env = ""
        if provider == "ollama":
            typer.echo(
                typer.style(
                    "\nOllama is local — no API key required.", fg=typer.colors.CYAN
                )
            )
        else:
            typer.echo(
                typer.style(
                    "\nGitHub Copilot uses OAuth — no API key needed.",
                    fg=typer.colors.CYAN,
                )
            )
            typer.echo(
                typer.style(
                    "  Run: minilegion auth login copilot",
                    fg=typer.colors.CYAN,
                )
            )
    else:
        # existing API key prompt block (unchanged)
        ...
```

Also add `"copilot"` recommended models to `config.py`'s `_default_recommended_models` and `_default_all_models`:

```python
"copilot": [
    ModelCatalogEntry(id="gpt-4o", description="GPT-4o via GitHub Copilot"),
    ModelCatalogEntry(id="claude-3.5-sonnet", description="Claude 3.5 Sonnet via GitHub Copilot"),
    ModelCatalogEntry(id="o3-mini", description="o3-mini via GitHub Copilot"),
],
```

And to `_default_model_aliases`:

```python
"copilot": {
    "default": "gpt-4o",
    "fast": "gpt-4o",
    "sonnet": "claude-3.5-sonnet",
},
```

**Step 4: Run tests**

```
pytest tests/test_config_commands.py -v
pytest tests/auth/ -v
```
Expected: All PASSED.

**Step 5: Commit**

```bash
git add minilegion/cli/config_commands.py minilegion/core/config.py tests/test_config_commands.py
git commit -m "feat(auth): add copilot to config init — skips API key prompt"
```

---

### Task 8: Full test suite green

**Step 1: Run the full test suite**

```
pytest --tb=short -q
```

Fix any failures before proceeding. Common issues to look for:
- `test_all_providers_have_default_env_var` — needs `copilot` in `DEFAULT_ENV_VAR` ✓ (done in Task 7)
- `test_default_config_exposes_recommended_and_full_catalogs` — needs `copilot` in model catalogs ✓ (done in Task 7)
- Any import cycle from `minilegion/auth/__init__.py` → `registry.py` → `providers/copilot.py`

**Step 2: Commit any fixes**

```bash
git add -A
git commit -m "fix(auth): resolve any test failures from full suite run"
```

---

### Task 9: Final integration check

**Step 1: Verify CLI help text**

```
python -m minilegion.cli auth --help
python -m minilegion.cli auth login --help
python -m minilegion.cli auth logout --help
python -m minilegion.cli auth status --help
```

Expected: All commands listed with correct help text.

**Step 2: Verify factory recognizes copilot**

```python
python -c "
from minilegion.adapters.factory import _PROVIDER_MAP
assert 'copilot' in _PROVIDER_MAP
print('factory: OK')

from minilegion.auth.registry import PROVIDERS
assert 'copilot' in PROVIDERS
print('auth registry: OK')

from minilegion.core.exceptions import AuthError, AuthExpiredError, AuthNotConfiguredError, AuthProviderError
print('exceptions: OK')
"
```

**Step 3: Run full suite one final time**

```
pytest --tb=short
```

Expected: All tests pass.

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(auth): minilegion auth login copilot — GitHub Device Flow OAuth complete"
```
