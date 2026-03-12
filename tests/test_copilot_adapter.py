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
