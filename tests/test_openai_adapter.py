"""Tests for OpenAI adapter implementation."""

from unittest.mock import MagicMock, patch

import openai
import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import LLMError


def make_mock_completion(content="test", model="gpt-4o"):
    """Create a realistic ChatCompletion object for testing."""
    return ChatCompletion(
        id="chatcmpl-test",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(content=content, role="assistant"),
            )
        ],
        created=1234567890,
        model=model,
        object="chat.completion",
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        ),
    )


def make_adapter_with_mock_client(config=None):
    """Create an OpenAIAdapter with a mock client injected."""
    from minilegion.adapters.openai_adapter import OpenAIAdapter

    config = config or MiniLegionConfig()
    adapter = OpenAIAdapter(config)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_completion()
    adapter._client = mock_client
    return adapter, mock_client


class TestLazyInit:
    """Verify lazy client initialization."""

    def test_client_is_none_after_construction(self):
        from minilegion.adapters.openai_adapter import OpenAIAdapter

        adapter = OpenAIAdapter(MiniLegionConfig())
        assert adapter._client is None

    def test_client_created_on_first_call(self, monkeypatch):
        from minilegion.adapters.openai_adapter import OpenAIAdapter

        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        adapter = OpenAIAdapter(MiniLegionConfig())

        with patch("minilegion.adapters.openai_adapter.OpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = make_mock_completion()
            mock_cls.return_value = mock_instance

            adapter.call("system", "user")
            assert adapter._client is not None

    def test_client_reused_on_second_call(self, monkeypatch):
        from minilegion.adapters.openai_adapter import OpenAIAdapter

        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        adapter = OpenAIAdapter(MiniLegionConfig())

        with patch("minilegion.adapters.openai_adapter.OpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = make_mock_completion()
            mock_cls.return_value = mock_instance

            adapter.call("system", "user1")
            first_client = adapter._client
            adapter.call("system", "user2")
            assert adapter._client is first_client
            # OpenAI constructor called only once
            assert mock_cls.call_count == 1


class TestAPIKeyValidation:
    """Verify API key validation before API calls."""

    def test_missing_api_key_raises_llm_error(self, monkeypatch):
        from minilegion.adapters.openai_adapter import OpenAIAdapter

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        adapter = OpenAIAdapter(MiniLegionConfig())

        with pytest.raises(LLMError, match="OPENAI_API_KEY"):
            adapter.call("system", "user")

    def test_custom_env_var_name_in_error(self, monkeypatch):
        from minilegion.adapters.openai_adapter import OpenAIAdapter

        monkeypatch.delenv("MY_KEY", raising=False)
        config = MiniLegionConfig(api_key_env="MY_KEY")
        adapter = OpenAIAdapter(config)

        with pytest.raises(LLMError, match="MY_KEY"):
            adapter.call("system", "user")


class TestAPIKeyFromConfig:
    """Verify API key is read from the configured env var."""

    def test_reads_from_configured_env_var(self, monkeypatch):
        from minilegion.adapters.openai_adapter import OpenAIAdapter

        monkeypatch.setenv("CUSTOM_API_KEY", "my-secret-key")
        config = MiniLegionConfig(api_key_env="CUSTOM_API_KEY")
        adapter = OpenAIAdapter(config)

        with patch("minilegion.adapters.openai_adapter.OpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.chat.completions.create.return_value = make_mock_completion()
            mock_cls.return_value = mock_instance

            adapter.call("system", "user")
            mock_cls.assert_called_once_with(
                api_key="my-secret-key",
                timeout=300.0,
                max_retries=0,
            )


class TestCall:
    """Verify call() behavior."""

    def test_call_returns_llm_response(self):
        from minilegion.adapters.base import LLMResponse

        adapter, mock_client = make_adapter_with_mock_client()
        result = adapter.call("system prompt", "user message")

        assert isinstance(result, LLMResponse)
        assert result.content == "test"
        assert result.model == "gpt-4o"
        assert result.finish_reason == "stop"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 20
        assert result.usage.total_tokens == 30

    def test_call_does_not_pass_response_format(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call("system", "user")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert "response_format" not in call_kwargs.kwargs


class TestCallForJson:
    """Verify call_for_json() behavior."""

    def test_call_for_json_passes_response_format(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call_for_json("system", "user")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}


class TestCallParameters:
    """Verify SDK call parameter mapping."""

    def test_system_and_user_messages_sent(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call("You are helpful", "Hello world")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "You are helpful"}
        assert messages[1] == {"role": "user", "content": "Hello world"}

    def test_max_tokens_mapped_to_max_completion_tokens(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call("system", "user", max_tokens=500)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_completion_tokens"] == 500

    def test_timeout_cast_to_float(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call("system", "user", timeout=30)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["timeout"] == 30.0
        assert isinstance(call_kwargs["timeout"], float)

    def test_max_tokens_none_omitted(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call("system", "user", max_tokens=None)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "max_completion_tokens" not in call_kwargs

    def test_timeout_none_omitted(self):
        adapter, mock_client = make_adapter_with_mock_client()
        adapter.call("system", "user", timeout=None)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "timeout" not in call_kwargs


class TestTokenUsageMapping:
    """Verify token usage extraction from SDK response."""

    def test_token_usage_mapped(self):
        adapter, mock_client = make_adapter_with_mock_client()
        result = adapter.call("system", "user")

        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 20
        assert result.usage.total_tokens == 30

    def test_none_usage_defaults_to_zero(self):
        adapter, mock_client = make_adapter_with_mock_client()
        # Create a completion with usage=None
        completion = ChatCompletion(
            id="chatcmpl-test",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(content="test", role="assistant"),
                )
            ],
            created=1234567890,
            model="gpt-4o",
            object="chat.completion",
            usage=None,
        )
        mock_client.chat.completions.create.return_value = completion

        result = adapter.call("system", "user")
        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 0


class TestErrorWrapping:
    """Verify SDK errors are wrapped in LLMError with chaining."""

    def test_authentication_error_wrapped(self):
        adapter, mock_client = make_adapter_with_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {}
        exc = openai.AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body=None,
        )
        mock_client.chat.completions.create.side_effect = exc

        with pytest.raises(LLMError, match="check your API key") as exc_info:
            adapter.call("system", "user")
        assert exc_info.value.__cause__ is exc

    def test_timeout_error_wrapped(self):
        adapter, mock_client = make_adapter_with_mock_client()
        exc = openai.APITimeoutError(request=MagicMock())
        mock_client.chat.completions.create.side_effect = exc

        with pytest.raises(LLMError, match="timed out") as exc_info:
            adapter.call("system", "user")
        assert exc_info.value.__cause__ is exc

    def test_api_error_wrapped(self):
        adapter, mock_client = make_adapter_with_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        exc = openai.APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )
        mock_client.chat.completions.create.side_effect = exc

        with pytest.raises(LLMError, match="OpenAI API error") as exc_info:
            adapter.call("system", "user")
        assert exc_info.value.__cause__ is exc

    def test_non_api_errors_propagate(self):
        adapter, mock_client = make_adapter_with_mock_client()
        mock_client.chat.completions.create.side_effect = ValueError("unexpected")

        with pytest.raises(ValueError, match="unexpected"):
            adapter.call("system", "user")


class TestPackageImport:
    """Verify package-level import of OpenAIAdapter."""

    def test_import_from_adapters_package(self):
        from minilegion.adapters import OpenAIAdapter

        assert OpenAIAdapter is not None
