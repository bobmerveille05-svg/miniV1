"""Tests for CopilotAuthProvider — all GitHub HTTP calls are mocked."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from minilegion.auth.providers.copilot import CopilotAuthProvider
from minilegion.auth.store import CredentialStore, TokenData
from minilegion.core.exceptions import (
    AuthExpiredError,
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
                provider._poll_for_token(device_code="abc", interval=5, expires_in=900)


def test_poll_raises_on_access_denied(provider):
    mock_response = MagicMock()
    mock_response.read.return_value = b"error=access_denied"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        with patch("time.sleep"):
            with pytest.raises(AuthProviderError, match="Copilot subscription"):
                provider._poll_for_token(device_code="abc", interval=5, expires_in=900)


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
