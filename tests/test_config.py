"""Tests for minilegion.core.config — config model and loading."""

import json

import pytest

from minilegion.core.config import MiniLegionConfig, load_config
from minilegion.core.exceptions import ConfigError


class TestMiniLegionConfig:
    """Test the MiniLegionConfig Pydantic model."""

    def test_default_config(self):
        """MiniLegionConfig() has correct defaults."""
        config = MiniLegionConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.api_key_env == "OPENAI_API_KEY"
        assert config.timeout == 120
        assert config.max_retries == 2
        assert config.engines == {}

    def test_get_engine_override(self):
        """get_engine returns per-role engine when set."""
        config = MiniLegionConfig(engines={"researcher": "gpt-4o-mini"})
        assert config.get_engine("researcher") == "gpt-4o-mini"

    def test_get_engine_fallback(self):
        """get_engine returns default model when role not in engines."""
        config = MiniLegionConfig(engines={"researcher": "gpt-4o-mini"})
        assert config.get_engine("builder") == "gpt-4o"


class TestLoadConfig:
    """Test config loading from file."""

    def test_load_config_missing_file(self, tmp_project_dir):
        """load_config returns defaults when config file doesn't exist."""
        config = load_config(tmp_project_dir)
        assert config.provider == "openai"
        assert config.model == "gpt-4o"

    def test_load_config_valid_json(self, tmp_project_dir, sample_config_json):
        """load_config parses valid JSON correctly with custom values."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(sample_config_json)

        config = load_config(tmp_project_dir)
        assert config.model == "gpt-4o-mini"
        assert config.timeout == 60
        assert config.max_retries == 3
        assert config.engines == {"researcher": "gpt-4o"}
        assert config.get_engine("researcher") == "gpt-4o"

    def test_load_config_partial_json(self, tmp_project_dir):
        """load_config applies defaults for missing fields in partial JSON."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(json.dumps({"model": "gpt-3.5-turbo"}))

        config = load_config(tmp_project_dir)
        assert config.model == "gpt-3.5-turbo"
        assert config.provider == "openai"  # default
        assert config.timeout == 120  # default
        assert config.engines == {}  # default

    def test_load_config_invalid_json(self, tmp_project_dir):
        """load_config raises ConfigError on malformed JSON."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text("{ not valid json }")

        with pytest.raises(ConfigError):
            load_config(tmp_project_dir)
