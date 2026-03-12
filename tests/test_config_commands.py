"""Tests for minilegion config sub-commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from minilegion.cli import app
from minilegion.cli.config_commands import DEFAULT_ENV_VAR, PROVIDERS
from minilegion.core.config import MiniLegionConfig

runner = CliRunner()


def _make_project(tmp_path: Path, config: MiniLegionConfig | None = None) -> Path:
    """Create a minimal project-ai/ directory with a config file."""
    project_ai = tmp_path / "project-ai"
    project_ai.mkdir()
    config = config or MiniLegionConfig()
    (project_ai / "minilegion.config.json").write_text(
        config.model_dump_json(indent=2), encoding="utf-8"
    )
    return project_ai


def _read_config(project_ai: Path) -> MiniLegionConfig:
    raw = (project_ai / "minilegion.config.json").read_text(encoding="utf-8")
    return MiniLegionConfig.model_validate_json(raw)


class TestCatalogue:
    def test_all_providers_have_default_env_var(self):
        for slug in PROVIDERS:
            assert slug in DEFAULT_ENV_VAR, f"Missing DEFAULT_ENV_VAR for {slug}"

    def test_default_config_exposes_recommended_and_full_catalogs(self):
        config = MiniLegionConfig()

        for slug in PROVIDERS:
            assert slug in config.recommended_models
            assert slug in config.all_models
            assert slug in config.model_aliases
            assert len(config.recommended_models[slug]) >= 1
            assert len(config.all_models[slug]) >= len(config.recommended_models[slug])


class TestConfigInit:
    def test_no_project_dir_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 1
        assert "No MiniLegion project found" in result.output

    def test_recommended_catalog_is_default_path(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n2\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o-mini"
        assert "Recommended" in result.output

    def test_can_switch_to_full_catalog(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n2\n4\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.model == "gpt-4.1"
        assert "All configured models" in result.output

    def test_alias_input_persists_canonical_model(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n3\nmini\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.model == "gpt-4o-mini"
        assert "Alias resolved" in result.output

    def test_unknown_alias_fails_with_clear_feedback(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n3\nnot-a-real-model\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "Unknown model or alias" in result.output

    def test_missing_catalog_entries_fail_clearly(self, tmp_path, monkeypatch):
        config = MiniLegionConfig(
            recommended_models={"openai": []},
            all_models={"openai": []},
            model_aliases={"openai": {}},
        )
        _make_project(tmp_path, config)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "init"],
            input="1\n\n1\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "No configured models available" in result.output


class TestConfigModel:
    def test_no_project_dir_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "model"])
        assert result.exit_code == 1
        assert "No MiniLegion project found" in result.output

    def test_shows_current_provider_and_model(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "model"],
            input="1\n1\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Current configuration" in result.output
        assert "gpt-4o" in result.output

    def test_changes_model_from_full_catalog(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "model"],
            input="2\n5\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.model == "o1"

    def test_alias_input_updates_to_canonical_model(self, tmp_path, monkeypatch):
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "model"],
            input="3\nmini\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(tmp_path / "project-ai")
        assert cfg.model == "gpt-4o-mini"
        assert "Alias resolved" in result.output

    def test_same_model_alias_says_unchanged(self, tmp_path, monkeypatch):
        _make_project(tmp_path, MiniLegionConfig(model="gpt-4o-mini"))
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["config", "model"],
            input="3\nmini\n",
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "unchanged" in result.output.lower()

    def test_missing_catalog_for_current_provider_fails_clearly(
        self, tmp_path, monkeypatch
    ):
        config = MiniLegionConfig(
            provider="openai",
            recommended_models={"openai": []},
            all_models={"openai": []},
            model_aliases={"openai": {}},
        )
        _make_project(tmp_path, config)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "model"], catch_exceptions=False)

        assert result.exit_code == 1
        assert "No configured models available" in result.output

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


class TestConfigInitCopilot:
    def test_copilot_skips_api_key_prompt(self, tmp_path, monkeypatch):
        """Selecting copilot as provider should skip the API key env var prompt."""
        _make_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # provider=6 (copilot), model source=1 (recommended), model=1
        result = runner.invoke(app, ["config", "init"], input="6\n1\n1\n")
        assert result.exit_code == 0, result.output
        assert "minilegion auth login copilot" in result.output

        config = _read_config(tmp_path / "project-ai")
        assert config.provider == "copilot"
        assert config.api_key_env == ""
