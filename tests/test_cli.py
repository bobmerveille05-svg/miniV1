"""CLI integration tests using CliRunner.

Tests all 8 commands, flags, no-args help, and state transition validation.
"""

import json

from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()


class TestCLIHelp:
    """Tests for help output and command registration."""

    def test_no_args_shows_help(self):
        """No args shows help text with Usage."""
        result = runner.invoke(app, [])
        # Typer/Click exits with code 0 or 2 depending on version when showing help
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output

    def test_help_flag(self):
        """--help shows help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_all_commands_registered(self):
        """All 8 commands appear in help output."""
        result = runner.invoke(app, ["--help"])
        commands = [
            "init",
            "brief",
            "research",
            "design",
            "plan",
            "execute",
            "review",
            "status",
        ]
        for cmd in commands:
            assert cmd in result.output, f"Command '{cmd}' not found in help output"


class TestCLIFlags:
    """Tests for command-specific flags."""

    def test_plan_fast_flag(self):
        """plan --fast flag is accepted (may error on missing project, not 'no such option')."""
        result = runner.invoke(app, ["plan", "--fast"])
        assert "No such option" not in result.output

    def test_plan_skip_research_design_flag(self):
        """plan --skip-research-design flag is accepted."""
        result = runner.invoke(app, ["plan", "--skip-research-design"])
        assert "No such option" not in result.output

    def test_execute_task_flag(self):
        """execute --task 1 flag is accepted."""
        result = runner.invoke(app, ["execute", "--task", "1"])
        assert "No such option" not in result.output

    def test_execute_dry_run_flag(self):
        """execute --dry-run flag is accepted."""
        result = runner.invoke(app, ["execute", "--dry-run"])
        assert "No such option" not in result.output

    def test_verbose_flag(self):
        """--verbose flag does not cause error."""
        result = runner.invoke(app, ["--verbose", "--help"])
        assert result.exit_code == 0


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_without_project(self, tmp_path, monkeypatch):
        """status without project-ai/ shows error message."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "No MiniLegion project found" in result.output

    def test_status_with_project(self, tmp_path, monkeypatch):
        """status with project-ai/STATE.json shows stage info."""
        monkeypatch.chdir(tmp_path)
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir()
        state_data = {
            "current_stage": "init",
            "approvals": {
                "brief_approved": False,
                "research_approved": False,
                "design_approved": False,
                "plan_approved": False,
                "execute_approved": False,
                "review_approved": False,
            },
            "completed_tasks": [],
            "history": [
                {
                    "timestamp": "2026-01-01T00:00:00",
                    "action": "init",
                    "details": "Project initialized",
                }
            ],
            "metadata": {},
        }
        (project_dir / "STATE.json").write_text(json.dumps(state_data, indent=2))
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "init" in result.output


class TestStateTransitionValidation:
    """Tests for state machine validation on pipeline commands."""

    def test_invalid_transition_rejected(self, tmp_path, monkeypatch):
        """design from init state is rejected with error."""
        monkeypatch.chdir(tmp_path)
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir()
        state_data = {
            "current_stage": "init",
            "approvals": {
                "brief_approved": False,
                "research_approved": False,
                "design_approved": False,
                "plan_approved": False,
                "execute_approved": False,
                "review_approved": False,
            },
            "completed_tasks": [],
            "history": [],
            "metadata": {},
        }
        (project_dir / "STATE.json").write_text(json.dumps(state_data, indent=2))
        result = runner.invoke(app, ["design"])
        assert result.exit_code == 1
        assert (
            "Cannot transition" in result.output or "invalid" in result.output.lower()
        )
