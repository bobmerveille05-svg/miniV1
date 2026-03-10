"""LLM provider adapters.

Public API:
- LLMAdapter: Abstract base class for all adapters
- LLMResponse: Structured response from an LLM call
- TokenUsage: Token usage statistics
- get_adapter: Factory — returns the right adapter from config.provider
- OpenAIAdapter: OpenAI API
- OpenAICompatibleAdapter: Any OpenAI-compatible endpoint (Groq, Together, etc.)
- OllamaAdapter: Local Ollama instance
- GeminiAdapter: Google Gemini API
- AnthropicAdapter: Anthropic Claude API
"""

from minilegion.adapters.base import LLMAdapter, LLMResponse, TokenUsage
from minilegion.adapters.factory import get_adapter
from minilegion.adapters.openai_adapter import OpenAIAdapter
from minilegion.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
from minilegion.adapters.ollama_adapter import OllamaAdapter
from minilegion.adapters.gemini_adapter import GeminiAdapter
from minilegion.adapters.anthropic_adapter import AnthropicAdapter

__all__ = [
    "LLMAdapter",
    "LLMResponse",
    "TokenUsage",
    "get_adapter",
    "OpenAIAdapter",
    "OpenAICompatibleAdapter",
    "OllamaAdapter",
    "GeminiAdapter",
    "AnthropicAdapter",
]
