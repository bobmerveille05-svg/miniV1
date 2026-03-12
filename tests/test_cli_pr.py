# tests/test_cli_pr.py
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from minilegion.cli import app

runner = CliRunner()


def _setup_project(tmp_path: Path) -> Path:
    """Create minimal project-ai/ structure for pr command."""
    project_ai = tmp_path / "project-ai"
    project_ai.mkdir()
    (project_ai / "STATE.json").write_text(
        json.dumps(
            {
                "current_stage": "review",
                "approvals": {},
                "completed_tasks": [],
                "history": [],
                "metadata": {},
            }
        )
    )
    (project_ai / "BRIEF.md").write_text("Add dark mode toggle")
    (project_ai / "PLAN.json").write_text(
        json.dumps(
            {
                "objective": "Add dark mode",
                "design_ref": "DESIGN.json",
                "test_plan": "unit tests",
                "tasks": [{"id": "task-1", "name": "Add toggle", "description": "..."}],
                "touched_files": ["src/settings.py"],
            }
        )
    )
    review = {
        "design_conformity": {"conforms": True},
        "verdict": "pass",
        "corrective_actions": [],
        "success_criteria_met": ["dark mode works"],
    }
    (project_ai / "REVIEW.json").write_text(json.dumps(review))
    (project_ai / "minilegion.config.json").write_text(
        json.dumps({"provider": "openai", "model": "gpt-4o"})
    )
    return project_ai


def test_pr_command_writes_pr_md_when_gh_unavailable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    with patch("minilegion.core.git_integration.shutil.which", return_value=None):
        with patch("minilegion.core.git_integration.is_git_repo", return_value=False):
            result = runner.invoke(app, ["pr"])
    assert result.exit_code == 0
    assert (tmp_path / "PR.md").exists()
    assert "PR.md" in result.output or "pr" in result.output.lower()


def test_pr_command_uses_gh_when_available(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "https://github.com/owner/repo/pull/42\n"
    with patch(
        "minilegion.core.git_integration.shutil.which", return_value="/usr/bin/gh"
    ):
        with patch("minilegion.core.git_integration.is_git_repo", return_value=True):
            with patch("minilegion.core.git_integration._git") as mock_git:
                mock_git.return_value.stdout = "minilegion/myproject-20260101\n"
                with patch(
                    "minilegion.core.git_integration.subprocess.run",
                    return_value=mock_proc,
                ):
                    result = runner.invoke(app, ["pr"])
    assert result.exit_code == 0
    assert "github.com" in result.output or "PR" in result.output


def test_pr_command_exits_1_when_no_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["pr"])
    assert result.exit_code == 1


def test_pr_body_includes_brief_and_tasks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    with patch("minilegion.core.git_integration.shutil.which", return_value=None):
        with patch("minilegion.core.git_integration.is_git_repo", return_value=False):
            runner.invoke(app, ["pr"])
    pr_content = (tmp_path / "PR.md").read_text()
    assert "Add dark mode toggle" in pr_content
    assert "task-1" in pr_content
