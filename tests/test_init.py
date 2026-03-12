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
        """STATE.json does not persist embedded history."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        state_path = tmp_path / "myproject" / "project-ai" / "STATE.json"
        data = json.loads(state_path.read_text())
        assert "history" not in data

    def test_init_creates_history_event_file(self, tmp_path, monkeypatch):
        """init writes first event under project-ai/history/."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        history_dir = tmp_path / "myproject" / "project-ai" / "history"
        assert history_dir.is_dir()
        event_files = sorted(history_dir.glob("*.json"))
        assert event_files
        payload = json.loads(event_files[0].read_text())
        assert payload["event_type"] == "init"


class TestInitContextScaffolding:
    """Tests for adapter, template, and memory scaffolding created by init."""

    def test_init_creates_adapters_dir(self, tmp_path, monkeypatch):
        """init creates project-ai/adapters/ directory."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        assert (tmp_path / "myproject" / "project-ai" / "adapters").is_dir()

    def test_init_creates_claude_adapter(self, tmp_path, monkeypatch):
        """init creates project-ai/adapters/claude.md."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        adapter_path = tmp_path / "myproject" / "project-ai" / "adapters" / "claude.md"
        assert adapter_path.exists()
        assert len(adapter_path.read_text()) > 0

    def test_init_creates_all_adapter_files(self, tmp_path, monkeypatch):
        """init creates all 5 adapter files (_base, claude, chatgpt, copilot, opencode)."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        adapters_dir = tmp_path / "myproject" / "project-ai" / "adapters"
        for name in (
            "_base.md",
            "claude.md",
            "chatgpt.md",
            "copilot.md",
            "opencode.md",
        ):
            assert (adapters_dir / name).exists(), f"Missing adapter: {name}"

    def test_init_creates_templates_dir(self, tmp_path, monkeypatch):
        """init creates project-ai/templates/ directory."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        assert (tmp_path / "myproject" / "project-ai" / "templates").is_dir()

    def test_init_creates_research_template(self, tmp_path, monkeypatch):
        """init creates project-ai/templates/research.md."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        template_path = (
            tmp_path / "myproject" / "project-ai" / "templates" / "research.md"
        )
        assert template_path.exists()
        assert len(template_path.read_text()) > 0

    def test_init_creates_all_stage_templates(self, tmp_path, monkeypatch):
        """init creates all 8 stage templates (init through archive)."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        templates_dir = tmp_path / "myproject" / "project-ai" / "templates"
        for stage in (
            "init",
            "brief",
            "research",
            "design",
            "plan",
            "execute",
            "review",
            "archive",
        ):
            assert (templates_dir / f"{stage}.md").exists(), (
                f"Missing template: {stage}.md"
            )

    def test_init_creates_memory_dir(self, tmp_path, monkeypatch):
        """init creates project-ai/memory/ directory."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        assert (tmp_path / "myproject" / "project-ai" / "memory").is_dir()

    def test_init_creates_decisions_memory(self, tmp_path, monkeypatch):
        """init creates project-ai/memory/decisions.md."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        mem_path = tmp_path / "myproject" / "project-ai" / "memory" / "decisions.md"
        assert mem_path.exists()
        assert len(mem_path.read_text()) > 0

    def test_init_creates_all_memory_files(self, tmp_path, monkeypatch):
        """init creates all 3 memory scaffold files."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "myproject"])
        memory_dir = tmp_path / "myproject" / "project-ai" / "memory"
        for name in ("decisions.md", "glossary.md", "constraints.md"):
            assert (memory_dir / name).exists(), f"Missing memory file: {name}"
