"""Tests for minilegion config sub-commands: `config init` and `config model`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from minilegion.cli import app
from minilegion.cli.config_commands import (
    DEFAULT_ENV_VAR,
    PROVIDERS,
    RECOMMENDED_MODELS,
)
from minilegion.core.config import MiniLegionConfig

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project-ai/ directory with STATE.json and config."""
    project_ai = tmp_path / "project-ai"
    project_ai.mkdir()
    config = MiniLegionConfig()
    (project_ai / "minilegion.config.json").write_text(
        config.model_dump_json(indent=2), encoding="utf-8"
    )
    return project_ai


def _read_config(project_ai: Path) -> MiniLegionConfig:
    raw = (project_ai / "minilegion.config.json").read_text(encoding="utf-8")
    return MiniLegionConfig.model_validate_json(raw)


# ---------------------------------------------------------------------------
# Tests: catalogue constants
# ---------------------------------------------------------------------------


class TestCatalogue:
    def test_all_providers_have_default_env_var(self):
        for slug in PROVIDERS:
            assert slug in DEFAULT_ENV_VAR, f"Missing DEFAULT_ENV_VAR for {slug}"

    def test_all_providers_have_model_list(self):
        for slug in PROVIDERS:
            assert slug in RECOMMENDED_MODELS, f"Missing RECOMMENDED_MODELS for {slug}"
            assert len(RECOMMENDED_MODELS[slug]) >= 1

    def test_model_tuples_are_pairs(self):
        for slug, models in RECOMMENDED_MODELS.items():
            for item in models:
                assert len(item) == 2, f"Model entry for {slug} must be (id, desc)"


# ---------------------------------------------------------------------------
# Tests: `config init`
# ---------------------------------------------------------------------------


class TestConfigInit:
    def test_no_project_dir_exits_1(self, tmp_path, monkeypatch):
        """config init without project-ai/ exits with code 1."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 1
        assert "No MiniLegion project found" in result.output

    def test_selects_openai_first_model(self, tmp_path, monkeypatch):
        """Selecting OpenAI (choice 1) + first model writes correct config."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # Inputs: provider=1 (openai), env var=<default>, model=1 (gpt-4o)
        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "openai"
        assert cfg.model == RECOMMENDED_MODELS["openai"][0][0]
        assert cfg.api_key_env == "OPENAI_API_KEY"

    def test_selects_anthropic(self, tmp_path, monkeypatch):
        """Selecting Anthropic (choice 2) + first model writes correct config."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="2\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "anthropic"
        assert cfg.model == RECOMMENDED_MODELS["anthropic"][0][0]
        assert cfg.api_key_env == "ANTHROPIC_API_KEY"

    def test_selects_gemini(self, tmp_path, monkeypatch):
        """Selecting Gemini (choice 3) writes correct config."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="3\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "gemini"

    def test_selects_ollama_no_api_key_prompt(self, tmp_path, monkeypatch):
        """Ollama (choice 4) skips the API key prompt."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # Ollama does not ask for an env var → input: provider=4, model=1
        result = runner.invoke(
            app,
            ["config", "init"],
            input="4\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "ollama"
        assert cfg.api_key_env == ""

    def test_selects_openrouter(self, tmp_path, monkeypatch):
        """OpenRouter/openai-compatible (choice 5) writes correct config."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="5\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "openai-compatible"

    def test_custom_env_var_name(self, tmp_path, monkeypatch):
        """User can override the env var name."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # provider=1 (openai), custom env var, model=1
        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\nMY_CUSTOM_KEY\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.api_key_env == "MY_CUSTOM_KEY"

    def test_env_var_already_set_shows_check(self, tmp_path, monkeypatch):
        """When env var is already set, output shows a check mark."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "already set" in result.output

    def test_env_var_not_set_shows_warning(self, tmp_path, monkeypatch):
        """When env var is not set, output shows a warning."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "not set" in result.output

    def test_output_confirms_save(self, tmp_path, monkeypatch):
        """Output contains 'Saved to project-ai/minilegion.config.json'."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n",
            catch_exceptions=False,
        )
        assert "Saved to project-ai/minilegion.config.json" in result.output

    def test_invalid_then_valid_choice(self, tmp_path, monkeypatch):
        """Entering an invalid number keeps prompting until valid input."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # First type 'abc', then '99', then valid '1'
        result = runner.invoke(
            app,
            ["config", "init"],
            input="abc\n99\n1\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "openai"

    def test_preserves_existing_non_provider_fields(self, tmp_path, monkeypatch):
        """config init only updates provider/model/api_key_env; other fields kept."""
        project_ai = _make_project(tmp_path)
        # Write custom timeout
        cfg_before = MiniLegionConfig(timeout=300, max_retries=5)
        (project_ai / "minilegion.config.json").write_text(
            cfg_before.model_dump_json(indent=2), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        cfg_after = _read_config(project_ai)
        assert cfg_after.timeout == 300
        assert cfg_after.max_retries == 5

    def test_config_json_is_valid_json(self, tmp_path, monkeypatch):
        """Written config file is valid JSON with expected keys."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        runner.invoke(app, ["config", "init"], input="1\n\n2\n", catch_exceptions=False)
        raw = (tmp_path / "project-ai" / "minilegion.config.json").read_text(
            encoding="utf-8"
        )
        data = json.loads(raw)
        assert "provider" in data
        assert "model" in data
        assert "api_key_env" in data


# ---------------------------------------------------------------------------
# Tests: `config model`
# ---------------------------------------------------------------------------


class TestConfigModel:
    def test_no_project_dir_exits_1(self, tmp_path, monkeypatch):
        """config model without project-ai/ exits with code 1."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "model"])
        assert result.exit_code == 1
        assert "No MiniLegion project found" in result.output

    def test_shows_current_provider_and_model(self, tmp_path, monkeypatch):
        """config model displays current provider and model."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # Select first model to exit normally
        result = runner.invoke(
            app, ["config", "model"], input="1\n", catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "openai" in result.output.lower() or "OpenAI" in result.output
        assert "gpt-4o" in result.output

    def test_changes_model(self, tmp_path, monkeypatch):
        """Selecting a different model updates config."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # Default is openai / gpt-4o; pick model 2 (gpt-4o-mini)
        result = runner.invoke(
            app, ["config", "model"], input="2\n", catch_exceptions=False
        )
        assert result.exit_code == 0
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.model == RECOMMENDED_MODELS["openai"][1][0]

    def test_same_model_says_unchanged(self, tmp_path, monkeypatch):
        """Selecting the current model prints 'unchanged' and does not rewrite."""
        _make_project(tmp_path)
        # Default model is gpt-4o which is index 1 → pick "1"
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app, ["config", "model"], input="1\n", catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "unchanged" in result.output

    def test_output_confirms_save_on_change(self, tmp_path, monkeypatch):
        """Output contains 'Saved to' when model actually changed."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app, ["config", "model"], input="2\n", catch_exceptions=False
        )
        assert "Saved to project-ai/minilegion.config.json" in result.output

    def test_provider_preserved_after_model_change(self, tmp_path, monkeypatch):
        """Provider field is untouched when only model changes."""
        project_ai = _make_project(tmp_path)
        cfg = MiniLegionConfig(provider="anthropic", model="claude-3-opus-20240229")
        (project_ai / "minilegion.config.json").write_text(
            cfg.model_dump_json(indent=2), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        # Pick first Anthropic model
        result = runner.invoke(
            app, ["config", "model"], input="1\n", catch_exceptions=False
        )
        assert result.exit_code == 0
        cfg_after = _read_config(project_ai)
        assert cfg_after.provider == "anthropic"

    def test_unknown_provider_shows_edit_hint(self, tmp_path, monkeypatch):
        """Unknown provider (no model list) prints edit hint and exits 0."""
        project_ai = _make_project(tmp_path)
        cfg = MiniLegionConfig(provider="custom-llm", model="some-model")
        (project_ai / "minilegion.config.json").write_text(
            cfg.model_dump_json(indent=2), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "model"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Edit project-ai/minilegion.config.json" in result.output

    def test_invalid_then_valid_model_choice(self, tmp_path, monkeypatch):
        """Invalid model number keeps prompting until a valid one is given."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app, ["config", "model"], input="0\n99\n2\n", catch_exceptions=False
        )
        assert result.exit_code == 0
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.model == RECOMMENDED_MODELS["openai"][1][0]

    def test_help_is_available(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "model", "--help"])
        assert result.exit_code == 0
        assert "model" in result.output.lower()

    def test_config_init_help_is_available(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "init", "--help"])
        assert result.exit_code == 0
        assert "provider" in result.output.lower() or "init" in result.output.lower()
