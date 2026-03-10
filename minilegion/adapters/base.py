"""Abstract base class and data types for LLM provider adapters.

Provides:
- LLMAdapter: ABC that all provider adapters must subclass
- LLMResponse: Frozen dataclass for structured LLM responses
- TokenUsage: Frozen dataclass for token consumption stats

A new adapter can be created by subclassing LLMAdapter and implementing
call() and call_for_json() — no other code changes required.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    """Token usage statistics from an LLM response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class LLMResponse:
    """Structured response from an LLM call."""

    content: str
    usage: TokenUsage
    model: str
    finish_reason: str


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters.

    Subclasses must implement both call() and call_for_json().
    A new adapter can be created by subclassing and implementing
    these two methods — no other code changes required.
    """

    @abstractmethod
    def call(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        """Send a prompt and receive a structured response."""
        ...

    @abstractmethod
    def call_for_json(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> LLMResponse:
        """Send a prompt requesting JSON-formatted output.

        Concrete adapters decide how to enforce JSON mode
        (e.g., OpenAI uses response_format={"type": "json_object"}).
        """
        ...
