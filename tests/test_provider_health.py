"""Tests for provider readiness checks."""

from __future__ import annotations

import urllib.error

import pytest

from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ConfigError, LLMError
from minilegion.core.provider_health import run_provider_healthcheck


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


def test_ollama_healthcheck_probes_local_endpoint(monkeypatch):
    """Ollama performs a local readiness probe and validates model is installed."""
    config = MiniLegionConfig(
        provider="ollama", provider_healthcheck=True, model="llama3.2"
    )
    calls = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                b'{"models": [{"name": "llama3.2:latest"}, {"name": "mistral:latest"}]}'
            )

    def fake_urlopen(url, timeout=0):
        calls.append((url, timeout))
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    run_provider_healthcheck(config)

    assert calls == [("http://localhost:11434/api/tags", config.timeout)]


def test_ollama_healthcheck_fails_when_model_not_installed(monkeypatch):
    """Missing Ollama model raises a clear error with ollama pull hint."""
    config = MiniLegionConfig(
        provider="ollama", provider_healthcheck=True, model="qwen2.5-coder"
    )

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"models": [{"name": "deepseek-r1:1.5b"}, {"name": "gemma3:4b"}]}'

    monkeypatch.setattr("urllib.request.urlopen", lambda url, timeout=0: _Response())

    with pytest.raises(LLMError, match="ollama pull qwen2.5-coder"):
        run_provider_healthcheck(config)


def test_ollama_healthcheck_fails_when_endpoint_unavailable(monkeypatch):
    """Unreachable Ollama endpoint raises a clear readiness error."""
    config = MiniLegionConfig(provider="ollama", provider_healthcheck=True)

    def fake_urlopen(url, timeout=0):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(LLMError, match="Ollama"):
        run_provider_healthcheck(config)
