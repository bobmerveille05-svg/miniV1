"""Init command integration tests.

Tests for all init artifacts (STATE.json, config, BRIEF.md, prompts/).
"""

import json

from typer.testing import CliRunner

from minilegion.cli import app
from minilegion.core.state import ProjectState

runner = CliRunner()


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_project_dir(self, tmp_path, monkeypatch):
        """init creates project-ai/ directory."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "myproject"])
        assert result.exit_code == 0
        assert (tmp_path / "myproject" / "project-ai").is_dir()

    def test_init_creates_state_json(self, tmp_path, monkeypatch):
        """init creates STATE.json with correct initial state."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        state_path = tmp_path / "myproject" / "project-ai" / "STATE.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert data["current_stage"] == "init"

    def test_init_creates_config_json(self, tmp_path, monkeypatch):
        """init creates minilegion.config.json with default values."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        config_path = tmp_path / "myproject" / "project-ai" / "minilegion.config.json"
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o"

    def test_init_creates_brief_template(self, tmp_path, monkeypatch):
        """init creates BRIEF.md with template content."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        brief_path = tmp_path / "myproject" / "project-ai" / "BRIEF.md"
        assert brief_path.exists()
        content = brief_path.read_text()
        assert "Brief" in content or "brief" in content

    def test_init_creates_prompts_dir(self, tmp_path, monkeypatch):
        """init creates prompts/ directory."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        prompts_dir = tmp_path / "myproject" / "project-ai" / "prompts"
        assert prompts_dir.is_dir()

    def test_init_state_json_valid_model(self, tmp_path, monkeypatch):
        """STATE.json is valid JSON parseable by ProjectState model."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        state_path = tmp_path / "myproject" / "project-ai" / "STATE.json"
        raw = state_path.read_text()
        state = ProjectState.model_validate_json(raw)
        assert state.current_stage == "init"

    def test_init_existing_dir_warns(self, tmp_path, monkeypatch):
        """init warns when directory already exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "myproject").mkdir()
        result = runner.invoke(app, ["init", "myproject"])
        assert (
            "already exists" in result.output.lower()
            or "warning" in result.output.lower()
        )

    def test_init_state_has_history_entry(self, tmp_path, monkeypatch):
        """STATE.json history has init entry."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        state_path = tmp_path / "myproject" / "project-ai" / "STATE.json"
        data = json.loads(state_path.read_text())
        assert len(data["history"]) >= 1
        assert data["history"][0]["action"] == "init"
