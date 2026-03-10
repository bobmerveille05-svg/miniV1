"""Tests for brief and research CLI commands (Phase 6)."""

import json

import pytest
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from minilegion.cli.commands import app

runner = CliRunner()


def _write_init_state(project_ai: Path) -> None:
    """Create a minimal STATE.json at init stage for test setup."""
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
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")


def _write_brief_state(project_ai: Path) -> None:
    """Create STATE.json at brief stage with brief_approved=True."""
    state_data = {
        "current_stage": "brief",
        "approvals": {"brief_approved": True},
        "history": [{"stage": "brief", "message": "Brief created and approved"}],
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
    # Also create BRIEF.md (required by preflight for research stage)
    (project_ai / "BRIEF.md").write_text(
        "# Project Brief\n\n## Overview\n\nTest brief.\n",
        encoding="utf-8",
    )


class TestBriefCommand:
    def test_brief_creates_brief_md_with_text_arg(self, tmp_path, monkeypatch):
        """brief "my text" creates BRIEF.md in project-ai/."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=True):
            result = runner.invoke(app, ["brief", "my text"])

        assert result.exit_code == 0, result.output
        assert (project_ai / "BRIEF.md").exists()

    def test_brief_content_contains_overview_heading(self, tmp_path, monkeypatch):
        """BRIEF.md contains '## Overview' section with the supplied text."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=True):
            result = runner.invoke(app, ["brief", "hello world"])

        assert result.exit_code == 0, result.output
        content = (project_ai / "BRIEF.md").read_text(encoding="utf-8")
        assert "## Overview" in content
        assert "hello world" in content

    def test_brief_writes_atomically_before_approval(self, tmp_path, monkeypatch):
        """BRIEF.md exists on disk even when approval is rejected."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=False):
            result = runner.invoke(app, ["brief", "some text"])

        # File should exist even though approval was rejected
        assert (project_ai / "BRIEF.md").exists(), (
            "BRIEF.md should exist before approval gate"
        )
        # STATE.json should still be at init
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "init"

    def test_brief_stdin_input(self, tmp_path, monkeypatch):
        """brief with no arg reads text from stdin."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=True):
            result = runner.invoke(app, ["brief"], input="stdin text\n")

        assert result.exit_code == 0, result.output
        content = (project_ai / "BRIEF.md").read_text(encoding="utf-8")
        assert "stdin text" in content

    def test_brief_stdin_empty_creates_empty_overview(self, tmp_path, monkeypatch):
        """brief with empty stdin creates BRIEF.md with empty ## Overview body."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=True):
            result = runner.invoke(app, ["brief"], input="\n")

        assert result.exit_code == 0, result.output
        content = (project_ai / "BRIEF.md").read_text(encoding="utf-8")
        assert "## Overview" in content

    def test_brief_approval_accepted_transitions_state(self, tmp_path, monkeypatch):
        """Approved brief transitions STATE.json current_stage from 'init' to 'brief'."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=True):
            result = runner.invoke(app, ["brief", "approved text"])

        assert result.exit_code == 0, result.output
        # Read STATE.json from disk to confirm transition
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "brief"
        assert state_data["approvals"]["brief_approved"] is True

    def test_brief_rejection_leaves_state_json_unchanged(self, tmp_path, monkeypatch):
        """Rejected brief leaves STATE.json unchanged (current_stage stays 'init')."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        # Capture original STATE.json content
        original_state = (project_ai / "STATE.json").read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=False):
            result = runner.invoke(app, ["brief", "rejected text"])

        # STATE.json current_stage should still be init
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "init"
        assert state_data["approvals"].get("brief_approved") is False

    def test_brief_rejection_exits_0(self, tmp_path, monkeypatch):
        """Rejected brief exits with code 0 (rejection is not an error)."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_init_state(project_ai)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=False):
            result = runner.invoke(app, ["brief", "text"])

        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}: {result.output}"
        )
        assert "rejected" in result.output.lower()

    def test_brief_without_project_dir_exits_1(self, tmp_path, monkeypatch):
        """brief without project-ai/ directory exits with code 1."""
        monkeypatch.chdir(tmp_path)
        # No project-ai/ directory created
        result = runner.invoke(app, ["brief", "text"])
        assert result.exit_code == 1
        assert (
            "No MiniLegion project found" in result.output
            or "project" in result.output.lower()
        )

    def test_brief_from_wrong_stage_exits_1(self, tmp_path, monkeypatch):
        """brief from a wrong stage (e.g. research) exits with code 1."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        # Write STATE.json at 'research' stage — can't go back to 'brief' in forward direction
        # Actually research -> brief is a backtrack (allowed). Use 'brief' -> try 'brief' again (same stage, not allowed).
        # Can't go brief -> brief (same stage). Let's use already at brief stage.
        state_data = {
            "current_stage": "brief",
            "approvals": {
                "brief_approved": True,
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
        (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["brief", "text"])
        assert result.exit_code == 1
        assert "Cannot transition" in result.output or "cannot" in result.output.lower()


# ---------------------------------------------------------------------------
# Valid research data fixture (ResearchSchema-compatible)
# ---------------------------------------------------------------------------

VALID_RESEARCH = {
    "project_overview": "Test project overview",
    "tech_stack": ["python"],
    "architecture_patterns": ["layered"],
    "relevant_files": ["minilegion/cli/commands.py"],
    "existing_conventions": ["type hints"],
    "dependencies_map": {},
    "potential_impacts": ["none"],
    "constraints": ["constraint1"],
    "assumptions_verified": ["assumption1"],
    "open_questions": ["question1"],
    "recommended_focus_files": ["commands.py"],
}


class TestResearchCommand:
    def test_research_calls_preflight(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_preflight_failure_exits_1(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_runs_scanner(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_calls_llm(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_saves_dual_output(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_approval_accepted_transitions_state(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_rejection_leaves_state_unchanged(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_rejection_exits_0(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_llm_error_exits_1(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_missing_brief_md_exits_1(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_research_state_current_stage_is_research_after_approval(
        self, tmp_path, monkeypatch
    ):
        pytest.fail("not implemented")
