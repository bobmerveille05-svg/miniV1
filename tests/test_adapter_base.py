"""Tests for LLM adapter base classes and dataclasses."""

import dataclasses

import pytest


class TestLLMAdapterABC:
    """Verify LLMAdapter ABC enforcement."""

    def test_cannot_instantiate_directly(self):
        from minilegion.adapters.base import LLMAdapter

        with pytest.raises(TypeError):
            LLMAdapter()

    def test_subclass_with_both_methods_instantiates(self):
        from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage

        class StubAdapter(LLMAdapter):
            def call(
                self, system_prompt, user_message, *, max_tokens=None, timeout=None
            ):
                return LLMResponse(
                    content="ok",
                    usage=TokenUsage(0, 0, 0),
                    model="test",
                    finish_reason="stop",
                )

            def call_for_json(
                self, system_prompt, user_message, *, max_tokens=None, timeout=None
            ):
                return self.call(system_prompt, user_message)

        adapter = StubAdapter()
        assert adapter is not None

    def test_subclass_missing_call_for_json_fails(self):
        from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage

        class PartialAdapter(LLMAdapter):
            def call(
                self, system_prompt, user_message, *, max_tokens=None, timeout=None
            ):
                return LLMResponse(
                    content="ok",
                    usage=TokenUsage(0, 0, 0),
                    model="test",
                    finish_reason="stop",
                )

        with pytest.raises(TypeError):
            PartialAdapter()

    def test_subclass_missing_call_fails(self):
        from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage

        class PartialAdapter(LLMAdapter):
            def call_for_json(
                self, system_prompt, user_message, *, max_tokens=None, timeout=None
            ):
                return LLMResponse(
                    content="ok",
                    usage=TokenUsage(0, 0, 0),
                    model="test",
                    finish_reason="stop",
                )

        with pytest.raises(TypeError):
            PartialAdapter()


class TestDataclasses:
    """Verify TokenUsage and LLMResponse dataclasses."""

    def test_token_usage_fields(self):
        from minilegion.adapters.base import TokenUsage

        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30

    def test_llm_response_fields(self):
        from minilegion.adapters.base import LLMResponse, TokenUsage

        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = LLMResponse(
            content="test output",
            usage=usage,
            model="gpt-4o",
            finish_reason="stop",
        )
        assert response.content == "test output"
        assert response.usage is usage
        assert response.model == "gpt-4o"
        assert response.finish_reason == "stop"

    def test_token_usage_frozen(self):
        from minilegion.adapters.base import TokenUsage

        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        with pytest.raises(dataclasses.FrozenInstanceError):
            usage.prompt_tokens = 99

    def test_llm_response_frozen(self):
        from minilegion.adapters.base import LLMResponse, TokenUsage

        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = LLMResponse(
            content="test",
            usage=usage,
            model="gpt-4o",
            finish_reason="stop",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            response.content = "modified"


class TestImports:
    """Verify package-level re-exports."""

    def test_imports_from_package(self):
        from minilegion.adapters import LLMAdapter, LLMResponse, TokenUsage

        assert LLMAdapter is not None
        assert LLMResponse is not None
        assert TokenUsage is not None
