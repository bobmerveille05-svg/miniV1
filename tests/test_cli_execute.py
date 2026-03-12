"""Tests for the execute() CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

VALID_EXECUTION_LOG = {
    "tasks": [
        {
            "task_id": "T1",
            "changed_files": [
                {
                    "path": "minilegion/core/new_module.py",
                    "action": "create",
                    "content": "# new module\n",
                }
            ],
            "unchanged_files": [],
            "tests_run": [],
            "test_result": "",
            "blockers": [],
            "out_of_scope_needed": [],
        }
    ]
}

VALID_PLAN = {
    "objective": "Implement core module",
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
    "risks": [],
    "success_criteria": ["Module importable"],
    "test_plan": "Run pytest",
}


def _write_plan_state(project_ai: Path) -> None:
    """Create STATE.json at plan stage with all 4 approvals True, plus all prior artifacts."""
    state_data = {
        "current_stage": "plan",
        "approvals": {
            "brief_approved": True,
            "research_approved": True,
            "design_approved": True,
            "plan_approved": True,
            "execute_approved": False,
            "review_approved": False,
        },
        "completed_tasks": [],
        "history": [],
        "metadata": {},
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
    (project_ai / "BRIEF.md").write_text(
        "# Project Brief\n\n## Overview\n\nTest.\n", encoding="utf-8"
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
    (project_ai / "PLAN.json").write_text(json.dumps(VALID_PLAN), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExecuteCommand:
    def _mock_all(
        self,
        monkeypatch,
        project_ai: Path,
        *,
        approve: bool = True,
        fail_llm: bool = False,
    ) -> None:
        """Shared mock setup for execute command tests."""
        from minilegion.core.schemas import ExecutionLogSchema

        mock_log = ExecutionLogSchema(**VALID_EXECUTION_LOG)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Build {{project_name}} {{plan_json}} {{source_files}}",
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
                lambda *a, **kw: mock_log,
            )

        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm",
            lambda *a, **kw: approve,
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        # Prevent scope validation from raising; allow all files through
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_scope",
            lambda changed, allowed: None,
        )
        # Mock apply_patch to avoid touching disk; return a description string
        monkeypatch.setattr(
            "minilegion.cli.commands.apply_patch",
            lambda cf, root, dry_run=False: f"CREATE {cf.path} (1 lines)",
        )

    def test_execute_calls_preflight(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        called_with = {}

        def mock_preflight(stage, pd, skip_stages=None):
            called_with["stage"] = stage

        self._mock_all(monkeypatch, project_ai)
        monkeypatch.setattr("minilegion.cli.commands.check_preflight", mock_preflight)

        runner.invoke(app, ["execute"])

        from minilegion.core.state import Stage

        assert called_with.get("stage") == Stage.EXECUTE

    def test_execute_calls_llm_with_execution_log_artifact(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        called_with = {}
        from minilegion.core.schemas import ExecutionLogSchema

        mock_log = ExecutionLogSchema(**VALID_EXECUTION_LOG)

        def mock_validate(llm_call, prompt, artifact, config, pd):
            called_with["artifact"] = artifact
            return mock_log

        self._mock_all(monkeypatch, project_ai)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate
        )

        runner.invoke(app, ["execute"])

        assert called_with.get("artifact") == "execution_log"

    def test_execute_saves_execution_log(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai)

        runner.invoke(app, ["execute"])

        assert (project_ai / "EXECUTION_LOG.json").exists()
        assert (project_ai / "EXECUTION_LOG.md").exists()

    def test_execute_scope_violation_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        from minilegion.core.exceptions import ValidationError

        self._mock_all(monkeypatch, project_ai)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_scope",
            lambda changed, allowed: (_ for _ in ()).throw(
                ValidationError("Out-of-scope: secret.py")
            ),
        )

        result = runner.invoke(app, ["execute"])

        assert result.exit_code == 1

    def test_execute_dry_run_no_files_written(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai)

        result = runner.invoke(app, ["execute", "--dry-run"])

        assert result.exit_code == 0
        assert not (project_ai / "EXECUTION_LOG.json").exists()
        assert "[DRY RUN]" in result.output

    def test_execute_patch_approved_transitions_state(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve=True)

        runner.invoke(app, ["execute"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["approvals"]["execute_approved"] is True

    def test_execute_state_current_stage_is_execute_after_approval(
        self, monkeypatch, tmp_path
    ):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve=True)

        runner.invoke(app, ["execute"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "plan"

    def test_execute_patch_rejected_exits_0(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve=False)

        result = runner.invoke(app, ["execute"])

        assert result.exit_code == 0
        assert "rejected" in result.output.lower()

    def test_execute_task_filter_valid(self, monkeypatch, tmp_path):
        """--task 1 filters to the first (and only) task; should succeed."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve=True)

        result = runner.invoke(app, ["execute", "--task", "1"])

        assert result.exit_code == 0

    def test_execute_task_filter_out_of_range_exits_1(self, monkeypatch, tmp_path):
        """--task 99 is out of range → exit 1."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve=True)

        result = runner.invoke(app, ["execute", "--task", "99"])

        assert result.exit_code == 1

    def test_execute_llm_error_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_plan_state(project_ai)

        self._mock_all(monkeypatch, project_ai, fail_llm=True)

        result = runner.invoke(app, ["execute"])

        assert result.exit_code == 1
