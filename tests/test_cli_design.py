"""Tests for the design() CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_DESIGN = {
    "design_approach": "Modular architecture",
    "architecture_decisions": [
        {
            "decision": "Use Pydantic",
            "rationale": "Type safety",
            "alternatives_rejected": ["dataclasses"],
        }
    ],
    "components": [
        {"name": "Core", "description": "Core logic", "files": ["minilegion/core/"]}
    ],
    "data_models": ["ProjectState"],
    "api_contracts": [],
    "integration_points": [],
    "design_patterns_used": ["Repository"],
    "conventions_to_follow": ["snake_case"],
    "technical_risks": [],
    "out_of_scope": [],
    "test_strategy": "pytest unit tests",
    "estimated_complexity": "medium",
}


def _write_research_state(project_ai: Path) -> None:
    """Create STATE.json at research stage with both approvals True, plus BRIEF.md and RESEARCH.json."""
    state_data = {
        "current_stage": "research",
        "approvals": {
            "brief_approved": True,
            "research_approved": True,
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
    (project_ai / "BRIEF.md").write_text(
        "# Project Brief\n\n## Overview\n\nTest brief.\n", encoding="utf-8"
    )
    (project_ai / "RESEARCH.json").write_text(
        '{"project_overview": "test", "tech_stack": [], "architecture_patterns": [],'
        ' "relevant_files": [], "existing_conventions": [], "dependencies_map": {},'
        ' "potential_impacts": [], "constraints": [], "assumptions_verified": [],'
        ' "open_questions": [], "recommended_focus_files": []}',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDesignCommand:
    def _mock_all(self, monkeypatch, tmp_path, *, approve=True, fail_llm=False):
        """Shared mock setup for design command tests."""
        from minilegion.core.schemas import DesignSchema

        mock_design = DesignSchema(**VALID_DESIGN)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Design {{project_name}} {{brief_content}} {{research_json}} {{focus_files_content}}",
            ),
        )
        if fail_llm:
            from minilegion.core.exceptions import LLMError

            monkeypatch.setattr(
                "minilegion.cli.commands.validate_with_retry",
                lambda *a, **kw: (_ for _ in ()).throw(LLMError("API error")),
            )
        else:
            monkeypatch.setattr(
                "minilegion.cli.commands.validate_with_retry",
                lambda *a, **kw: mock_design,
            )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm",
            lambda *a, **kw: approve,
        )

    def test_design_calls_preflight(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        called_with = {}

        def mock_preflight(stage, pd, skip_stages=None):
            called_with["stage"] = stage
            called_with["pd"] = pd

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr("minilegion.cli.commands.check_preflight", mock_preflight)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        from minilegion.core.state import Stage

        assert called_with.get("stage") == Stage.DESIGN

    def test_design_calls_llm(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        called_with = {}
        from minilegion.core.schemas import DesignSchema

        mock_design = DesignSchema(**VALID_DESIGN)

        def mock_validate(llm_call, prompt, artifact, config, pd):
            called_with["artifact"] = artifact
            return mock_design

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        assert called_with.get("artifact") == "design"

    def test_design_saves_dual_output(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        assert (project_ai / "DESIGN.json").exists()
        assert (project_ai / "DESIGN.md").exists()

    def test_design_preflight_failure_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        from minilegion.core.exceptions import PreflightError

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight",
            lambda s, pd: (_ for _ in ()).throw(
                PreflightError("RESEARCH.json missing")
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        result = runner.invoke(app, ["design"])

        assert result.exit_code == 1

    def test_design_llm_error_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, fail_llm=True)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        result = runner.invoke(app, ["design"])

        assert result.exit_code == 1

    def test_design_writes_atomically_before_approval(self, monkeypatch, tmp_path):
        """DESIGN.json and DESIGN.md must exist on disk even when user rejects."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=False)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        assert (project_ai / "DESIGN.json").exists()
        assert (project_ai / "DESIGN.md").exists()

    def test_design_approval_accepted_transitions_state(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=True)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["approvals"]["design_approved"] is True

    def test_design_state_current_stage_is_design_after_approval(
        self, monkeypatch, tmp_path
    ):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=True)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "design"

    def test_design_rejection_exits_0(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=False)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        result = runner.invoke(app, ["design"])

        assert result.exit_code == 0
        assert "rejected" in result.output.lower()

    def test_design_rejection_leaves_state_unchanged(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_research_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=False)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["design"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "research"
