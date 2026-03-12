"""Configuration model and loading for MiniLegion.

Config is stored in project-ai/minilegion.config.json. All fields have sensible
defaults so a missing or partial config file works out of the box.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from minilegion.core.exceptions import ConfigError


class ModelCatalogEntry(BaseModel):
    """Serializable provider model entry used by the config CLI."""

    id: str
    description: str


def _default_recommended_models() -> dict[str, list[ModelCatalogEntry]]:
    return {
        "openai": [
            ModelCatalogEntry(
                id="gpt-4o", description="GPT-4o - fast, multimodal flagship"
            ),
            ModelCatalogEntry(
                id="gpt-4o-mini", description="GPT-4o mini - cheap, fast"
            ),
            ModelCatalogEntry(id="o3-mini", description="o3-mini - reasoning model"),
        ],
        "anthropic": [
            ModelCatalogEntry(
                id="claude-3-7-sonnet-20250219",
                description="Claude 3.7 Sonnet - best balance",
            ),
            ModelCatalogEntry(
                id="claude-3-5-haiku-20241022",
                description="Claude 3.5 Haiku - fast, cheap",
            ),
            ModelCatalogEntry(
                id="claude-3-opus-20240229",
                description="Claude 3 Opus - most powerful",
            ),
        ],
        "gemini": [
            ModelCatalogEntry(
                id="gemini-2.0-flash", description="Gemini 2.0 Flash - fast, cheap"
            ),
            ModelCatalogEntry(
                id="gemini-2.0-pro", description="Gemini 2.0 Pro - most capable"
            ),
            ModelCatalogEntry(
                id="gemini-1.5-flash", description="Gemini 1.5 Flash - stable"
            ),
        ],
        "ollama": [
            ModelCatalogEntry(
                id="llama3.2", description="Llama 3.2 - default local model"
            ),
            ModelCatalogEntry(
                id="mistral", description="Mistral 7B - fast local model"
            ),
            ModelCatalogEntry(id="deepseek-r1", description="DeepSeek R1 - reasoning"),
            ModelCatalogEntry(
                id="qwen2.5-coder", description="Qwen 2.5 Coder - coding specialist"
            ),
        ],
        "openai-compatible": [
            ModelCatalogEntry(
                id="openrouter/auto",
                description="OpenRouter auto - cheapest available",
            ),
            ModelCatalogEntry(
                id="anthropic/claude-3.7-sonnet",
                description="Claude 3.7 Sonnet via OpenRouter",
            ),
            ModelCatalogEntry(
                id="openai/gpt-4o-mini",
                description="GPT-4o mini via OpenRouter",
            ),
            ModelCatalogEntry(
                id="google/gemini-2.0-flash",
                description="Gemini 2.0 Flash via OpenRouter",
            ),
            ModelCatalogEntry(
                id="meta-llama/llama-3.3-70b-instruct",
                description="Llama 3.3 70B via OpenRouter",
            ),
        ],
        "copilot": [
            ModelCatalogEntry(id="gpt-4o", description="GPT-4o via GitHub Copilot"),
            ModelCatalogEntry(
                id="claude-3.5-sonnet",
                description="Claude 3.5 Sonnet via GitHub Copilot",
            ),
            ModelCatalogEntry(id="o3-mini", description="o3-mini via GitHub Copilot"),
        ],
    }


def _default_all_models() -> dict[str, list[ModelCatalogEntry]]:
    return {
        "openai": [
            ModelCatalogEntry(
                id="gpt-4o", description="GPT-4o - fast, multimodal flagship"
            ),
            ModelCatalogEntry(
                id="gpt-4o-mini", description="GPT-4o mini - cheap, fast"
            ),
            ModelCatalogEntry(id="o3-mini", description="o3-mini - reasoning model"),
            ModelCatalogEntry(
                id="gpt-4.1", description="GPT-4.1 - newer general flagship"
            ),
            ModelCatalogEntry(id="o1", description="o1 - high reasoning model"),
        ],
        "anthropic": [
            ModelCatalogEntry(
                id="claude-3-7-sonnet-20250219",
                description="Claude 3.7 Sonnet - best balance",
            ),
            ModelCatalogEntry(
                id="claude-3-5-haiku-20241022",
                description="Claude 3.5 Haiku - fast, cheap",
            ),
            ModelCatalogEntry(
                id="claude-3-opus-20240229",
                description="Claude 3 Opus - most powerful",
            ),
            ModelCatalogEntry(
                id="claude-3-5-sonnet-20241022",
                description="Claude 3.5 Sonnet - stable general model",
            ),
        ],
        "gemini": [
            ModelCatalogEntry(
                id="gemini-2.0-flash", description="Gemini 2.0 Flash - fast, cheap"
            ),
            ModelCatalogEntry(
                id="gemini-2.0-pro", description="Gemini 2.0 Pro - most capable"
            ),
            ModelCatalogEntry(
                id="gemini-1.5-flash", description="Gemini 1.5 Flash - stable"
            ),
            ModelCatalogEntry(
                id="gemini-1.5-pro", description="Gemini 1.5 Pro - long context"
            ),
        ],
        "ollama": [
            ModelCatalogEntry(
                id="llama3.2", description="Llama 3.2 - default local model"
            ),
            ModelCatalogEntry(
                id="mistral", description="Mistral 7B - fast local model"
            ),
            ModelCatalogEntry(id="deepseek-r1", description="DeepSeek R1 - reasoning"),
            ModelCatalogEntry(
                id="qwen2.5-coder", description="Qwen 2.5 Coder - coding specialist"
            ),
            ModelCatalogEntry(id="phi4", description="Phi-4 - compact local model"),
        ],
        "openai-compatible": [
            ModelCatalogEntry(
                id="openrouter/auto",
                description="OpenRouter auto - cheapest available",
            ),
            ModelCatalogEntry(
                id="anthropic/claude-3.7-sonnet",
                description="Claude 3.7 Sonnet via OpenRouter",
            ),
            ModelCatalogEntry(
                id="openai/gpt-4o-mini",
                description="GPT-4o mini via OpenRouter",
            ),
            ModelCatalogEntry(
                id="google/gemini-2.0-flash",
                description="Gemini 2.0 Flash via OpenRouter",
            ),
            ModelCatalogEntry(
                id="meta-llama/llama-3.3-70b-instruct",
                description="Llama 3.3 70B via OpenRouter",
            ),
            ModelCatalogEntry(
                id="deepseek/deepseek-r1",
                description="DeepSeek R1 via OpenRouter",
            ),
        ],
        "copilot": [
            ModelCatalogEntry(id="gpt-4o", description="GPT-4o via GitHub Copilot"),
            ModelCatalogEntry(
                id="claude-3.5-sonnet",
                description="Claude 3.5 Sonnet via GitHub Copilot",
            ),
            ModelCatalogEntry(id="o3-mini", description="o3-mini via GitHub Copilot"),
        ],
    }


def _default_model_aliases() -> dict[str, dict[str, str]]:
    return {
        "openai": {
            "default": "gpt-4o",
            "fast": "gpt-4o-mini",
            "mini": "gpt-4o-mini",
            "reasoning": "o3-mini",
        },
        "anthropic": {
            "default": "claude-3-7-sonnet-20250219",
            "fast": "claude-3-5-haiku-20241022",
            "haiku": "claude-3-5-haiku-20241022",
            "opus": "claude-3-opus-20240229",
        },
        "gemini": {
            "default": "gemini-2.0-flash",
            "fast": "gemini-2.0-flash",
            "pro": "gemini-2.0-pro",
        },
        "ollama": {
            "default": "llama3.2",
            "fast": "mistral",
            "reasoning": "deepseek-r1",
            "coder": "qwen2.5-coder",
        },
        "openai-compatible": {
            "default": "openrouter/auto",
            "fast": "openai/gpt-4o-mini",
            "claude": "anthropic/claude-3.7-sonnet",
            "gemini": "google/gemini-2.0-flash",
        },
        "copilot": {
            "default": "gpt-4o",
            "fast": "gpt-4o",
            "claude": "claude-3.5-sonnet",
            "reasoning": "o3-mini",
        },
    }


class ContextConfig(BaseModel):
    """Config for context assembly (CTX-01, CFG-08).

    All fields have defaults so omitting 'context' from minilegion.config.json
    produces identical behavior (CFG-09).
    """

    max_injection_tokens: int = 3000
    lookahead_tasks: int = 2
    warn_threshold: float = 0.7


class WorkflowConfig(BaseModel):
    """Config for explicit validate/advance workflow gating."""

    strict_mode: bool = True
    require_validation: bool = True


class ResearchConfig(BaseModel):
    """Config for research stage modes and options (RSM-01 through RSM-04).

    All fields have defaults so omitting 'research' from minilegion.config.json
    produces identical behavior (non-breaking).
    """

    default_mode: Literal["fact", "brainstorm"] = "fact"
    default_options: int = 3
    min_options: int = 1
    max_options: int = 5
    require_recommendation: bool = True

    @model_validator(mode="after")
    def _normalize_default_options(self) -> "ResearchConfig":
        """Normalize default_options to be within min/max bounds."""
        if self.default_options < self.min_options:
            self.default_options = self.min_options
        elif self.default_options > self.max_options:
            self.default_options = self.max_options
        return self


class MiniLegionConfig(BaseModel):
    """Configuration for a MiniLegion project."""

    provider: str = "openai"
    model: str = "gpt-4o"
    small_model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None  # For openai-compatible and ollama providers
    timeout: int = 300
    max_retries: int = 2
    tool_permissions: Literal["confirm", "allow", "deny"] = "confirm"
    recommended_models: dict[str, list[ModelCatalogEntry]] = Field(
        default_factory=_default_recommended_models
    )
    all_models: dict[str, list[ModelCatalogEntry]] = Field(
        default_factory=_default_all_models
    )
    model_aliases: dict[str, dict[str, str]] = Field(
        default_factory=_default_model_aliases
    )
    context_auto_compact: bool = True
    provider_healthcheck: bool = True
    engines: dict[str, str] = Field(default_factory=dict)
    # Scanner limits (Phase 6) — all have defaults for backward compatibility
    scan_max_depth: int = 5
    scan_max_files: int = 200
    scan_max_file_size_kb: int = 100
    # Context assembly config (Phase 2, CTX-01, CFG-08) — optional, backward compatible
    context: ContextConfig = Field(default_factory=ContextConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    # Research stage config (Phase 6, RSM-01 through RSM-04) — optional, backward compatible
    research: ResearchConfig = Field(default_factory=ResearchConfig)

    @model_validator(mode="after")
    def _normalize_small_model(self) -> "MiniLegionConfig":
        if not self.small_model.strip():
            self.small_model = self.model
        return self

    def get_engine(self, role: str) -> str:
        """Get engine for a role, falling back to default model."""
        return self.engines.get(role, self.model)

    def get_small_model(self) -> str:
        """Get the configured small model with a safe fallback."""
        return self.small_model or self.model


def load_config(project_dir: Path) -> MiniLegionConfig:
    """Load config from project-ai/minilegion.config.json.

    Args:
        project_dir: Root directory of the project.

    Returns:
        MiniLegionConfig with values from file or defaults.

    Raises:
        ConfigError: If the config file contains invalid JSON.
    """
    config_path = project_dir / "project-ai" / "minilegion.config.json"
    if not config_path.exists():
        return MiniLegionConfig()  # All defaults

    raw = config_path.read_text(encoding="utf-8")
    try:
        return MiniLegionConfig.model_validate_json(raw)
    except Exception as exc:
        raise ConfigError(f"Invalid config file {config_path}: {exc}") from exc
