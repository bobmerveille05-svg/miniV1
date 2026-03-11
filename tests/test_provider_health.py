"""Tests for provider readiness checks."""

from __future__ import annotations

import urllib.error

import pytest

from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ConfigError, LLMError
from minilegion.core.provider_health import (
    fetch_ollama_models,
    run_provider_healthcheck,
)


def test_healthcheck_disabled_skips_provider_checks(monkeypatch):
    """Disabled healthcheck returns without probing provider readiness."""
    config = MiniLegionConfig(provider="openai", provider_healthcheck=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    run_provider_healthcheck(config)


def test_openai_healthcheck_passes_with_required_env(monkeypatch):
    """Configured remote providers pass when local prerequisites exist."""
    config = MiniLegionConfig(provider="openai", provider_healthcheck=True)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    run_provider_healthcheck(config)


def test_openai_healthcheck_fails_with_missing_api_key(monkeypatch):
    """Missing API key fails with actionable remediation text."""
    config = MiniLegionConfig(provider="openai", provider_healthcheck=True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        run_provider_healthcheck(config)


def test_openai_compatible_healthcheck_requires_base_url(monkeypatch):
    """OpenAI-compatible providers need a configured base_url."""
    config = MiniLegionConfig(
        provider="openai-compatible",
        provider_healthcheck=True,
        api_key_env="GROQ_API_KEY",
        base_url=None,
    )
    monkeypatch.setenv("GROQ_API_KEY", "sk-test")

    with pytest.raises(ConfigError, match="base_url"):
        run_provider_healthcheck(config)


def _make_response(body: bytes):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return body

    return _Response()


def test_ollama_healthcheck_passes_with_exact_model_name(monkeypatch):
    """Healthcheck passes when configured model exactly matches installed name."""
    config = MiniLegionConfig(
        provider="ollama", provider_healthcheck=True, model="deepseek-r1:1.5b"
    )
    calls = []

    def fake_urlopen(url, timeout=0):
        calls.append((url, timeout))
        return _make_response(
            b'{"models": [{"name": "deepseek-r1:1.5b"}, {"name": "gemma3:4b"}]}'
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    run_provider_healthcheck(config)

    assert calls == [("http://localhost:11434/api/tags", config.timeout)]


def test_ollama_healthcheck_fails_model_not_installed(monkeypatch):
    """Completely absent model raises LLMError with ollama pull hint."""
    config = MiniLegionConfig(
        provider="ollama", provider_healthcheck=True, model="qwen2.5-coder"
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=0: _make_response(
            b'{"models": [{"name": "deepseek-r1:1.5b"}, {"name": "gemma3:4b"}]}'
        ),
    )

    with pytest.raises(LLMError, match="ollama pull qwen2.5-coder"):
        run_provider_healthcheck(config)


def test_ollama_healthcheck_suggests_exact_name_for_base_match(monkeypatch):
    """Base-name-only match surfaces the exact installed name with a hint."""
    config = MiniLegionConfig(
        provider="ollama", provider_healthcheck=True, model="deepseek-r1"
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=0: _make_response(
            b'{"models": [{"name": "deepseek-r1:1.5b"}, {"name": "gemma3:4b"}]}'
        ),
    )

    with pytest.raises(LLMError, match="deepseek-r1:1.5b"):
        run_provider_healthcheck(config)


def test_ollama_healthcheck_fails_when_endpoint_unavailable(monkeypatch):
    """Unreachable Ollama endpoint raises a clear readiness error."""
    config = MiniLegionConfig(provider="ollama", provider_healthcheck=True)

    def fake_urlopen(url, timeout=0):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(LLMError, match="Ollama"):
        run_provider_healthcheck(config)


def test_fetch_ollama_models_returns_names(monkeypatch):
    """fetch_ollama_models returns sorted name list from /api/tags."""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=0: _make_response(
            b'{"models": [{"name": "gemma3:4b"}, {"name": "deepseek-r1:1.5b"}]}'
        ),
    )

    result = fetch_ollama_models()

    assert result == ["gemma3:4b", "deepseek-r1:1.5b"]


def test_fetch_ollama_models_returns_empty_on_error(monkeypatch):
    """fetch_ollama_models returns [] when Ollama is unreachable."""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=0: (_ for _ in ()).throw(urllib.error.URLError("refused")),
    )

    result = fetch_ollama_models()

    assert result == []
