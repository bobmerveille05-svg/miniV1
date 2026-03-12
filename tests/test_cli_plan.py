"""Tests for the plan() CLI command."""

from __future__ import annotations

import json
from pathlib import Path

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
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
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

        def mock_preflight(stage, pd, skip_stages=None):
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
        assert state_data["current_stage"] == "design"

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


# ---------------------------------------------------------------------------
# Fixture helpers for fast mode
# ---------------------------------------------------------------------------


def _write_brief_state(project_ai: Path) -> None:
    """Create STATE.json at brief stage with only brief_approved=True. No RESEARCH.json or DESIGN.json."""
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
    (project_ai / "BRIEF.md").write_text(
        "# Project Brief\n\n## Overview\n\nTest brief.\n", encoding="utf-8"
    )
    # Intentionally no RESEARCH.json or DESIGN.json


# ---------------------------------------------------------------------------
# Fast mode tests
# ---------------------------------------------------------------------------


class TestFastMode:
    """FAST-01, FAST-02, FAST-03: --fast and --skip-research-design flags."""

    def _mock_fast(self, monkeypatch, project_ai, *, approve=True, fail_llm=False):
        """Shared mock setup for fast mode tests."""
        from minilegion.core.schemas import PlanSchema

        mock_plan = PlanSchema(**VALID_PLAN)

        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase",
            lambda pd, cfg: "## Directory Structure\n\nproject/\n  src/\n",
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

    def test_fast_flag_bypasses_design_preflight(self, monkeypatch, tmp_path):
        """--fast from brief stage with no RESEARCH.json/DESIGN.json succeeds."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)
        self._mock_fast(monkeypatch, project_ai)

        result = runner.invoke(app, ["plan", "--fast"])

        assert result.exit_code == 0
        assert (project_ai / "PLAN.json").exists()

    def test_skip_research_design_flag_equivalent_to_fast(self, monkeypatch, tmp_path):
        """--skip-research-design produces same result as --fast."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)
        self._mock_fast(monkeypatch, project_ai)

        result = runner.invoke(app, ["plan", "--skip-research-design"])

        assert result.exit_code == 0
        assert (project_ai / "PLAN.json").exists()

    def test_fast_mode_sets_skipped_stages_metadata(self, monkeypatch, tmp_path):
        """After fast mode, STATE.json metadata has skipped_stages."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)
        self._mock_fast(monkeypatch, project_ai)

        runner.invoke(app, ["plan", "--fast"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        skipped = json.loads(state_data["metadata"].get("skipped_stages", "[]"))
        assert "research" in skipped
        assert "design" in skipped

    def test_fast_mode_sets_synthetic_approvals(self, monkeypatch, tmp_path):
        """After fast mode, STATE.json has research_approved=True and design_approved=True."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)
        self._mock_fast(monkeypatch, project_ai)

        runner.invoke(app, ["plan", "--fast"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["approvals"]["research_approved"] is True
        assert state_data["approvals"]["design_approved"] is True

    def test_fast_mode_transitions_to_plan_stage(self, monkeypatch, tmp_path):
        """After fast mode approval, current_stage is 'plan'."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)
        self._mock_fast(monkeypatch, project_ai)

        runner.invoke(app, ["plan", "--fast"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "brief"

    def test_fast_mode_uses_scan_codebase(self, monkeypatch, tmp_path):
        """scan_codebase is called when --fast is used."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)

        scan_called = {}

        def mock_scan(pd, cfg):
            scan_called["called"] = True
            return "## Directory Structure\n\nproject/\n"

        self._mock_fast(monkeypatch, project_ai)
        monkeypatch.setattr("minilegion.cli.commands.scan_codebase", mock_scan)

        runner.invoke(app, ["plan", "--fast"])

        assert scan_called.get("called") is True

    def test_fast_mode_from_brief_stage(self, monkeypatch, tmp_path):
        """Fast mode can start from 'brief' stage (not 'design')."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)  # current_stage = "brief"
        self._mock_fast(monkeypatch, project_ai)

        result = runner.invoke(app, ["plan", "--fast"])

        assert result.exit_code == 0

    def test_normal_mode_unchanged(self, monkeypatch, tmp_path):
        """plan without flags still requires preflight (DESIGN.json not bypassed)."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_brief_state(project_ai)

        preflight_called_with = {}

        def capture_preflight(stage, pd, skip_stages=None):
            preflight_called_with["skip_stages"] = skip_stages

        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", capture_preflight
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: None,
        )

        runner.invoke(app, ["plan"])

        # Normal mode passes skip_stages=None (no bypass)
        assert preflight_called_with.get("skip_stages") is None
