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
        dumped = config.model_dump()

        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.small_model == "gpt-4o-mini"
        assert config.api_key_env == "OPENAI_API_KEY"
        assert config.timeout == 300
        assert config.max_retries == 2
        assert config.engines == {}
        assert config.tool_permissions == "confirm"
        assert config.context_auto_compact is True
        assert config.provider_healthcheck is True
        assert dumped["recommended_models"]["openai"][0]["id"] == "gpt-4o"
        assert dumped["all_models"]["openai"][0]["id"] == "gpt-4o"
        assert dumped["model_aliases"]["openai"]["mini"] == "gpt-4o-mini"

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
        assert config.small_model == "gpt-4o-mini"
        assert config.tool_permissions == "confirm"
        assert config.timeout == 300  # default
        assert config.engines == {}  # default
        assert config.context_auto_compact is True
        assert config.provider_healthcheck is True
        assert "openai" in config.recommended_models
        assert "openai" in config.all_models
        assert "openai" in config.model_aliases

    def test_load_config_rejects_invalid_tool_permissions(self, tmp_project_dir):
        """load_config raises ConfigError for unsupported tool permission values."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(json.dumps({"tool_permissions": "always"}))

        with pytest.raises(ConfigError, match="Invalid config file"):
            load_config(tmp_project_dir)

    def test_load_config_catalog_fields_have_cli_safe_shape(self, tmp_project_dir):
        """Catalog and alias fields load as provider-keyed structures the CLI can consume."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(
            json.dumps(
                {
                    "recommended_models": {
                        "openai": [
                            {"id": "gpt-4o", "description": "GPT-4o"},
                            {"id": "gpt-4o-mini", "description": "GPT-4o mini"},
                        ]
                    },
                    "all_models": {
                        "openai": [
                            {"id": "gpt-4o", "description": "GPT-4o"},
                            {"id": "gpt-4.1", "description": "GPT-4.1"},
                        ]
                    },
                    "model_aliases": {
                        "openai": {"flagship": "gpt-4o", "mini": "gpt-4o-mini"}
                    },
                }
            )
        )

        config = load_config(tmp_project_dir)
        dumped = config.model_dump()

        assert dumped["recommended_models"]["openai"][1]["id"] == "gpt-4o-mini"
        assert dumped["all_models"]["openai"][1]["id"] == "gpt-4.1"
        assert dumped["model_aliases"]["openai"]["flagship"] == "gpt-4o"

    def test_load_config_invalid_json(self, tmp_project_dir):
        """load_config raises ConfigError on malformed JSON."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text("{ not valid json }")

        with pytest.raises(ConfigError):
            load_config(tmp_project_dir)
