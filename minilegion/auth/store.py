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
