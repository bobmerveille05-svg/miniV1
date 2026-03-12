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
