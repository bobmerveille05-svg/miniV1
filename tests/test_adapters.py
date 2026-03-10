"""Tests for all LLM adapters and the get_adapter factory.

All network calls are mocked — no real API keys required.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from minilegion.adapters import (
    AnthropicAdapter,
    GeminiAdapter,
    OllamaAdapter,
    OpenAICompatibleAdapter,
    get_adapter,
)
from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ConfigError, LLMError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(**kwargs) -> MiniLegionConfig:
    defaults = dict(provider="openai", model="gpt-4o", api_key_env="OPENAI_API_KEY")
    defaults.update(kwargs)
    return MiniLegionConfig(**defaults)


def _fake_openai_response(content="hello", model="gpt-4o"):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.choices[0].finish_reason = "stop"
    resp.model = model
    resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return resp


# ---------------------------------------------------------------------------
# get_adapter factory
# ---------------------------------------------------------------------------


class TestGetAdapter:
    def test_returns_openai_adapter_for_openai_provider(self):
        from minilegion.adapters import OpenAIAdapter

        cfg = _config(provider="openai")
        adapter = get_adapter(cfg)
        assert isinstance(adapter, OpenAIAdapter)

    def test_returns_openai_compatible_adapter(self):
        cfg = _config(provider="openai-compatible", base_url="http://localhost:1234/v1")
        adapter = get_adapter(cfg)
        assert isinstance(adapter, OpenAICompatibleAdapter)

    def test_returns_ollama_adapter(self):
        cfg = _config(provider="ollama", model="llama3.2")
        adapter = get_adapter(cfg)
        assert isinstance(adapter, OllamaAdapter)

    def test_returns_gemini_adapter(self):
        cfg = _config(
            provider="gemini", model="gemini-1.5-flash", api_key_env="GEMINI_API_KEY"
        )
        adapter = get_adapter(cfg)
        assert isinstance(adapter, GeminiAdapter)

    def test_returns_anthropic_adapter(self):
        cfg = _config(
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            api_key_env="ANTHROPIC_API_KEY",
        )
        adapter = get_adapter(cfg)
        assert isinstance(adapter, AnthropicAdapter)

    def test_provider_case_insensitive(self):
        cfg = _config(provider="OLLAMA", model="llama3.2")
        adapter = get_adapter(cfg)
        assert isinstance(adapter, OllamaAdapter)

    def test_unknown_provider_raises_config_error(self):
        cfg = _config(provider="unknown-llm")
        with pytest.raises(ConfigError, match="Unknown provider"):
            get_adapter(cfg)


# ---------------------------------------------------------------------------
# OpenAICompatibleAdapter
# ---------------------------------------------------------------------------


class TestOpenAICompatibleAdapter:
    _PATCH = "minilegion.adapters.openai_compatible_adapter.OpenAI"

    def _make(
        self, base_url="https://api.groq.com/openai/v1", api_key_env="GROQ_API_KEY"
    ):
        cfg = _config(
            provider="openai-compatible",
            model="llama-3.3-70b",
            api_key_env=api_key_env,
            base_url=base_url,
        )
        return OpenAICompatibleAdapter(cfg)

    def test_call_returns_llm_response(self):
        adapter = self._make()
        fake = _fake_openai_response("world", "llama-3.3-70b")
        with patch.dict("os.environ", {"GROQ_API_KEY": "sk-test"}):
            with patch(self._PATCH) as mock_cls:
                mock_cls.return_value.chat.completions.create.return_value = fake
                result = adapter.call("sys", "hi")
        assert result.content == "world"
        assert result.model == "llama-3.3-70b"
        assert result.usage.total_tokens == 15

    def test_call_for_json_passes_response_format(self):
        adapter = self._make()
        fake = _fake_openai_response('{"key": "val"}')
        with patch.dict("os.environ", {"GROQ_API_KEY": "sk-test"}):
            with patch(self._PATCH) as mock_cls:
                mock_client = mock_cls.return_value
                mock_client.chat.completions.create.return_value = fake
                adapter.call_for_json("sys", "give json")
                call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs.get("response_format") == {"type": "json_object"}

    def test_missing_api_key_raises_llm_error(self):
        # No base_url + no env var → should raise before constructing client
        cfg = _config(
            provider="openai-compatible",
            model="llama-3.3-70b",
            api_key_env="GROQ_API_KEY",
            base_url=None,
        )
        adapter = OpenAICompatibleAdapter(cfg)
        with patch.dict("os.environ", {}, clear=True):
            with patch(self._PATCH):
                with pytest.raises(LLMError, match="API key not found"):
                    adapter.call("sys", "hi")

    def test_local_endpoint_no_key_required(self):
        """base_url without api_key should still construct the client."""
        adapter = self._make(
            base_url="http://localhost:1234/v1", api_key_env="NONEXISTENT_KEY"
        )
        fake = _fake_openai_response("ok")
        with patch.dict("os.environ", {}, clear=True):
            with patch(self._PATCH) as mock_cls:
                mock_cls.return_value.chat.completions.create.return_value = fake
                result = adapter.call("sys", "hi")
        assert result.content == "ok"


# ---------------------------------------------------------------------------
# OllamaAdapter
# ---------------------------------------------------------------------------


class TestOllamaAdapter:
    def _make(self, base_url="http://localhost:11434"):
        cfg = _config(provider="ollama", model="llama3.2", base_url=base_url)
        return OllamaAdapter(cfg)

    def _fake_ollama_response(self, content="hi from ollama"):
        return json.dumps(
            {
                "model": "llama3.2",
                "message": {"role": "assistant", "content": content},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 20,
                "eval_count": 8,
            }
        ).encode("utf-8")

    def test_call_returns_llm_response(self):
        adapter = self._make()
        raw = self._fake_ollama_response("pong")
        mock_resp = MagicMock()
        mock_resp.read.return_value = raw
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = adapter.call("sys", "ping")

        assert result.content == "pong"
        assert result.model == "llama3.2"
        assert result.usage.prompt_tokens == 20
        assert result.usage.completion_tokens == 8
        assert result.usage.total_tokens == 28

    def test_call_for_json_sets_format(self):
        adapter = self._make()
        raw = self._fake_ollama_response('{"a": 1}')
        mock_resp = MagicMock()
        mock_resp.read.return_value = raw
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            adapter.call_for_json("sys", "give json")

        assert captured["body"].get("format") == "json"

    def test_unreachable_host_raises_llm_error(self):
        import urllib.error

        adapter = self._make()
        with patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("refused")
        ):
            with pytest.raises(LLMError, match="Cannot reach Ollama"):
                adapter.call("sys", "hi")

    def test_custom_base_url(self):
        adapter = self._make(base_url="http://192.168.1.100:11434")
        assert adapter._base_url == "http://192.168.1.100:11434"


# ---------------------------------------------------------------------------
# GeminiAdapter
# ---------------------------------------------------------------------------


class TestGeminiAdapter:
    def _make(self):
        cfg = _config(
            provider="gemini",
            model="gemini-1.5-flash",
            api_key_env="GEMINI_API_KEY",
        )
        return GeminiAdapter(cfg)

    def _fake_gemini_response(self, text="gemini reply"):
        part = MagicMock()
        part.text = text
        candidate = MagicMock()
        candidate.content.parts = [part]
        candidate.finish_reason = "STOP"
        resp = MagicMock()
        resp.candidates = [candidate]
        resp.usage_metadata.prompt_token_count = 12
        resp.usage_metadata.candidates_token_count = 6
        return resp

    def test_call_returns_llm_response(self):
        adapter = self._make()
        fake = self._fake_gemini_response("hello gemini")

        mock_genai = MagicMock()
        mock_genai.Client.return_value.models.generate_content.return_value = fake
        mock_types = MagicMock()

        with patch.dict("os.environ", {"GEMINI_API_KEY": "key123"}):
            with patch.dict(
                "sys.modules",
                {
                    "google": MagicMock(genai=mock_genai),
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                result = adapter.call("sys", "hi")

        assert result.content == "hello gemini"
        assert result.model == "gemini-1.5-flash"

    def test_missing_api_key_raises_llm_error(self):
        adapter = self._make()
        mock_genai = MagicMock()
        mock_types = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            with patch.dict(
                "sys.modules",
                {
                    "google": MagicMock(genai=mock_genai),
                    "google.genai": mock_genai,
                    "google.genai.types": mock_types,
                },
            ):
                with pytest.raises(LLMError, match="API key not found"):
                    adapter.call("sys", "hi")

    def test_missing_sdk_raises_llm_error(self):
        adapter = self._make()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "key"}):
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                with pytest.raises((LLMError, ImportError)):
                    adapter.call("sys", "hi")


# ---------------------------------------------------------------------------
# AnthropicAdapter
# ---------------------------------------------------------------------------


class TestAnthropicAdapter:
    def _make(self):
        cfg = _config(
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            api_key_env="ANTHROPIC_API_KEY",
        )
        return AnthropicAdapter(cfg)

    def _fake_anthropic_response(self, text="claude reply"):
        block = MagicMock()
        block.text = text
        resp = MagicMock()
        resp.content = [block]
        resp.model = "claude-3-5-haiku-20241022"
        resp.stop_reason = "end_turn"
        resp.usage.input_tokens = 15
        resp.usage.output_tokens = 7
        return resp

    def test_call_returns_llm_response(self):
        adapter = self._make()
        fake = self._fake_anthropic_response("hello claude")

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value.messages.create.return_value = fake

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                result = adapter.call("sys", "hi")

        assert result.content == "hello claude"
        assert result.model == "claude-3-5-haiku-20241022"
        assert result.usage.prompt_tokens == 15
        assert result.usage.completion_tokens == 7
        assert result.usage.total_tokens == 22

    def test_call_for_json_prepends_brace(self):
        """Assistant prefill: response without leading { gets one prepended."""
        adapter = self._make()
        fake = self._fake_anthropic_response('"key": "val"}')  # missing leading {

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value.messages.create.return_value = fake
        mock_anthropic.AuthenticationError = Exception
        mock_anthropic.APITimeoutError = Exception
        mock_anthropic.APIError = Exception

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                result = adapter.call_for_json("sys", "give json")

        assert result.content.startswith("{")

    def test_missing_api_key_raises_llm_error(self):
        adapter = self._make()
        mock_anthropic = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                with pytest.raises(LLMError, match="API key not found"):
                    adapter.call("sys", "hi")

    def test_missing_sdk_raises_llm_error(self):
        adapter = self._make()
        import sys

        saved = sys.modules.pop("anthropic", None)
        try:
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "key"}):
                with patch.dict("sys.modules", {"anthropic": None}):
                    with pytest.raises((LLMError, ImportError)):
                        adapter.call("sys", "hi")
        finally:
            if saved is not None:
                sys.modules["anthropic"] = saved


# ---------------------------------------------------------------------------
# MiniLegionConfig.base_url field
# ---------------------------------------------------------------------------


class TestConfigBaseUrl:
    def test_base_url_defaults_to_none(self):
        cfg = MiniLegionConfig()
        assert cfg.base_url is None

    def test_base_url_can_be_set(self):
        cfg = MiniLegionConfig(base_url="http://localhost:11434")
        assert cfg.base_url == "http://localhost:11434"

    def test_base_url_roundtrips_json(self):
        cfg = MiniLegionConfig(provider="ollama", base_url="http://host:11434")
        reloaded = MiniLegionConfig.model_validate_json(cfg.model_dump_json())
        assert reloaded.base_url == "http://host:11434"
