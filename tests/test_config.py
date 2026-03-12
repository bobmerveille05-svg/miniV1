"""Tests for minilegion.core.config — config model and loading."""

import json

import pytest

from minilegion.core.config import (
    ContextConfig,
    GitConfig,
    MiniLegionConfig,
    TestConfig,
    load_config,
)
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


class TestContextConfig:
    """Tests for ContextConfig sub-model (CFG-08, CFG-09)."""

    def test_context_config_defaults(self):
        """ContextConfig() has correct defaults."""
        ctx = ContextConfig()
        assert ctx.max_injection_tokens == 3000
        assert ctx.lookahead_tasks == 2
        assert ctx.warn_threshold == 0.7

    def test_minilegion_config_has_context_field(self):
        """MiniLegionConfig() has a context field of type ContextConfig."""
        config = MiniLegionConfig()
        assert hasattr(config, "context")
        assert isinstance(config.context, ContextConfig)

    def test_minilegion_config_context_defaults(self):
        """MiniLegionConfig().context has correct defaults (CFG-09)."""
        config = MiniLegionConfig()
        assert config.context.max_injection_tokens == 3000
        assert config.context.lookahead_tasks == 2
        assert config.context.warn_threshold == 0.7

    def test_context_partial_override(self, tmp_project_dir):
        """Config JSON with partial context block sets specified fields; unset fields keep defaults."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(json.dumps({"context": {"max_injection_tokens": 1500}}))

        config = load_config(tmp_project_dir)
        assert config.context.max_injection_tokens == 1500
        assert config.context.lookahead_tasks == 2  # unchanged default
        assert config.context.warn_threshold == 0.7  # unchanged default

    def test_context_absent_in_config_json_gives_defaults(self, tmp_project_dir):
        """Config JSON without a 'context' key produces identical ContextConfig defaults (CFG-09)."""
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(json.dumps({"model": "gpt-4o-mini"}))

        config = load_config(tmp_project_dir)
        assert config.context.max_injection_tokens == 3000
        assert config.context.lookahead_tasks == 2
        assert config.context.warn_threshold == 0.7

    def test_existing_config_tests_unaffected(self):
        """Regression: Adding ContextConfig does not break existing MiniLegionConfig defaults."""
        config = MiniLegionConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.small_model == "gpt-4o-mini"
        assert config.timeout == 300
        assert config.max_retries == 2
        assert config.engines == {}


class TestWorkflowConfig:
    """Tests for workflow strict/validation defaults (CFG-07)."""

    def test_workflow_defaults_when_omitted(self, tmp_project_dir):
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(json.dumps({"model": "gpt-4o-mini"}), encoding="utf-8")

        config = load_config(tmp_project_dir)
        assert config.workflow.strict_mode is True
        assert config.workflow.require_validation is True

    def test_workflow_partial_override_keeps_unspecified_default(self, tmp_project_dir):
        config_path = tmp_project_dir / "project-ai" / "minilegion.config.json"
        config_path.write_text(
            json.dumps({"workflow": {"strict_mode": False}}), encoding="utf-8"
        )

        config = load_config(tmp_project_dir)
        assert config.workflow.strict_mode is False
        assert config.workflow.require_validation is True


class TestGitConfig:
    """Tests for GitConfig sub-model."""

    def test_default_git_config(self):
        config = MiniLegionConfig()
        assert config.git.enabled is True
        assert "project-ai/EXECUTION_LOG.json" in config.git.commit_artifacts
        assert "project-ai/STATE.json" in config.git.commit_artifacts

    def test_git_config_can_be_disabled(self):
        config = MiniLegionConfig.model_validate({"git": {"enabled": False}})
        assert config.git.enabled is False


class TestTestConfig:
    """Tests for TestConfig sub-model."""

    def test_default_test_config(self):
        config = MiniLegionConfig()
        assert config.test.enabled is True
        assert config.test.timeout == 120
        assert config.test.command is None

    def test_test_config_accepts_command_override(self):
        config = MiniLegionConfig.model_validate(
            {"test": {"command": ["make", "test"]}}
        )
        assert config.test.command == ["make", "test"]

    def test_config_loads_without_git_test_fields(self, tmp_path):
        """Old config files without git/test fields must still load."""
        cfg_path = tmp_path / "project-ai"
        cfg_path.mkdir()
        (cfg_path / "minilegion.config.json").write_text(
            json.dumps({"provider": "openai", "model": "gpt-4o"})
        )
        from minilegion.core.config import load_config

        config = load_config(tmp_path)
        assert config.git.enabled is True
        assert config.test.enabled is True
