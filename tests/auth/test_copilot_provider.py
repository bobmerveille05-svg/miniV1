"""Tests for CopilotAuthProvider — PAT-based GitHub Models authentication."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from minilegion.auth.providers.copilot import CopilotAuthProvider
from minilegion.auth.store import CredentialStore, TokenData
from minilegion.core.exceptions import (
    AuthNotConfiguredError,
    AuthProviderError,
)


@pytest.fixture
def store(tmp_path):
    return CredentialStore(credentials_dir=tmp_path)


@pytest.fixture
def provider(store):
    return CopilotAuthProvider(store=store)


# ---------------------------------------------------------------------------
# login — PAT prompt and storage
# ---------------------------------------------------------------------------


def test_login_stores_pat(provider, store):
    """login() should store the token entered by the user."""
    with patch(
        "minilegion.auth.providers.copilot._prompt_for_token",
        return_value="ghp_testtoken123",
    ):
        provider.login()

    saved = store.load("copilot")
    assert saved is not None
    assert saved.access_token == "ghp_testtoken123"


def test_login_raises_on_empty_token(provider):
    """login() should raise AuthProviderError if user enters nothing."""
    with patch(
        "minilegion.auth.providers.copilot._prompt_for_token",
        return_value="   ",
    ):
        with pytest.raises(AuthProviderError, match="No token entered"):
            provider.login()


def test_login_raises_on_cancelled(provider):
    """login() should raise AuthProviderError on KeyboardInterrupt."""
    with patch(
        "minilegion.auth.providers.copilot._prompt_for_token",
        side_effect=KeyboardInterrupt,
    ):
        with pytest.raises(AuthProviderError, match="cancelled"):
            provider.login()


def test_login_warns_on_unrecognised_token_format(provider, store, capsys):
    """login() should warn (but not fail) if the token format is unrecognised."""
    with patch(
        "minilegion.auth.providers.copilot._prompt_for_token",
        return_value="some_unexpected_token",
    ):
        provider.login()

    captured = capsys.readouterr()
    assert "Warning" in captured.out
    # Token should still be saved
    assert store.load("copilot") is not None


# ---------------------------------------------------------------------------
# is_authenticated
# ---------------------------------------------------------------------------


def test_is_authenticated_false_when_no_credentials(provider):
    assert provider.is_authenticated() is False


def test_is_authenticated_true_when_token_stored(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghp_x",
            token_type="bearer",
            expires_at=None,
            refresh_token=None,
            scopes=[],
        ),
    )
    assert provider.is_authenticated() is True


# ---------------------------------------------------------------------------
# get_token
# ---------------------------------------------------------------------------


def test_get_token_returns_stored_pat(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghp_valid",
            token_type="bearer",
            expires_at=None,
            refresh_token=None,
            scopes=[],
        ),
    )
    assert provider.get_token() == "ghp_valid"


def test_get_token_raises_not_configured_when_missing_noninteractive(provider):
    with pytest.raises(AuthNotConfiguredError):
        provider.get_token(interactive=False)


def test_get_token_runs_login_when_missing_interactive(provider, store):
    """When interactive=True and no token exists, get_token should call login."""
    with patch(
        "minilegion.auth.providers.copilot._prompt_for_token",
        return_value="ghp_from_login",
    ):
        token = provider.get_token(interactive=True)

    assert token == "ghp_from_login"


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


def test_logout_removes_credentials(provider, store):
    store.save(
        "copilot",
        TokenData(
            access_token="ghp_x",
            token_type="bearer",
            expires_at=None,
            refresh_token=None,
            scopes=[],
        ),
    )
    provider.logout()
    assert store.load("copilot") is None
