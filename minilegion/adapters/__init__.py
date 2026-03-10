"""LLM provider adapters.

Public API:
- LLMAdapter: Abstract base class for all adapters
- LLMResponse: Structured response from an LLM call
- TokenUsage: Token usage statistics
- OpenAIAdapter: Concrete adapter using OpenAI SDK
"""

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.adapters.openai_adapter import OpenAIAdapter

__all__ = ["LLMAdapter", "LLMResponse", "TokenUsage", "OpenAIAdapter"]
