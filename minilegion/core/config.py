"""Configuration model and loading for MiniLegion.

Config is stored in project-ai/minilegion.config.json. All fields have sensible
defaults so a missing or partial config file works out of the box.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from minilegion.core.exceptions import ConfigError


class MiniLegionConfig(BaseModel):
    """Configuration for a MiniLegion project."""

    provider: str = "openai"
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    timeout: int = 120
    max_retries: int = 2
    engines: dict[str, str] = Field(default_factory=dict)
    # Scanner limits (Phase 6) — all have defaults for backward compatibility
    scan_max_depth: int = 5
    scan_max_files: int = 200
    scan_max_file_size_kb: int = 100

    def get_engine(self, role: str) -> str:
        """Get engine for a role, falling back to default model."""
        return self.engines.get(role, self.model)


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
