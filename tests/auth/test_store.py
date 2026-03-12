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
