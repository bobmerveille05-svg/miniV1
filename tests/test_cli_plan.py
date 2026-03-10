"""Tests for the plan() CLI command."""

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

VALID_PLAN = {
    "objective": "Implement the core module",
    "design_ref": "DESIGN.json v1",
    "assumptions": ["Python 3.11+"],
    "tasks": [
        {
            "id": "T1",
            "name": "Create core module",
            "description": "Create minilegion/core/new_module.py",
            "files": ["minilegion/core/new_module.py"],
            "depends_on": [],
            "component": "Core",
        }
    ],
    "touched_files": ["minilegion/core/new_module.py"],
    "risks": ["Circular imports"],
    "success_criteria": ["Module importable without errors"],
    "test_plan": "Run pytest tests/test_new_module.py",
}


def _write_design_state(project_ai: Path) -> None:
    """Create STATE.json at design stage with all approvals True, plus BRIEF.md, RESEARCH.json, DESIGN.json."""
    state_data = {
        "current_stage": "design",
        "approvals": {
            "brief_approved": True,
            "research_approved": True,
            "design_approved": True,
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
    (project_ai / "DESIGN.json").write_text(
        '{"design_approach": "Modular", "architecture_decisions": ['
        '{"decision": "Use Pydantic", "rationale": "Type safety", "alternatives_rejected": ["dataclasses"]}],'
        ' "components": [{"name": "Core", "description": "Core logic", "files": ["minilegion/core/"]}],'
        ' "data_models": [], "api_contracts": [], "integration_points": [],'
        ' "design_patterns_used": [], "conventions_to_follow": [],'
        ' "technical_risks": [], "out_of_scope": [], "test_strategy": "pytest", "estimated_complexity": "medium"}',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPlanCommand:
    def _mock_all(self, monkeypatch, tmp_path, *, approve=True, fail_llm=False):
        """Shared mock setup for plan command tests."""
        from minilegion.core.schemas import PlanSchema

        mock_plan = PlanSchema(**VALID_PLAN)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Plan {{project_name}} {{brief_content}} {{research_json}} {{design_json}}",
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
                lambda *a, **kw: mock_plan,
            )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm",
            lambda *a, **kw: approve,
        )

    def test_plan_calls_preflight(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        called_with = {}

        def mock_preflight(stage, pd):
            called_with["stage"] = stage
            called_with["pd"] = pd

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr("minilegion.cli.commands.check_preflight", mock_preflight)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        from minilegion.core.state import Stage

        assert called_with.get("stage") == Stage.PLAN

    def test_plan_calls_llm(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        called_with = {}
        from minilegion.core.schemas import PlanSchema

        mock_plan = PlanSchema(**VALID_PLAN)

        def mock_validate(llm_call, prompt, artifact, config, pd):
            called_with["artifact"] = artifact
            return mock_plan

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        assert called_with.get("artifact") == "plan"

    def test_plan_saves_dual_output(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        assert (project_ai / "PLAN.json").exists()
        assert (project_ai / "PLAN.md").exists()

    def test_plan_preflight_failure_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        from minilegion.core.exceptions import PreflightError

        self._mock_all(monkeypatch, tmp_path)
        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight",
            lambda s, pd: (_ for _ in ()).throw(PreflightError("DESIGN.json missing")),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        result = runner.invoke(app, ["plan"])

        assert result.exit_code == 1

    def test_plan_llm_error_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, fail_llm=True)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        result = runner.invoke(app, ["plan"])

        assert result.exit_code == 1

    def test_plan_writes_atomically_before_approval(self, monkeypatch, tmp_path):
        """PLAN.json and PLAN.md must exist on disk even when user rejects."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=False)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        assert (project_ai / "PLAN.json").exists()
        assert (project_ai / "PLAN.md").exists()

    def test_plan_approval_accepted_transitions_state(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=True)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["approvals"]["plan_approved"] is True

    def test_plan_state_current_stage_is_plan_after_approval(
        self, monkeypatch, tmp_path
    ):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=True)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "plan"

    def test_plan_rejection_exits_0(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=False)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        result = runner.invoke(app, ["plan"])

        assert result.exit_code == 0
        assert "rejected" in result.output.lower()

    def test_plan_rejection_leaves_state_unchanged(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_design_state(project_ai)

        self._mock_all(monkeypatch, tmp_path, approve=False)
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        runner.invoke(app, ["plan"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "design"
