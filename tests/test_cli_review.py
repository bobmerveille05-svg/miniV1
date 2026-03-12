"""Tests for the review() CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

VALID_REVIEW_PASS = {
    "bugs": [],
    "scope_deviations": [],
    "design_conformity": {"conforms": True, "deviations": []},
    "convention_violations": [],
    "security_risks": [],
    "performance_risks": [],
    "tech_debt": [],
    "out_of_scope_files": [],
    "success_criteria_met": ["Module importable"],
    "verdict": "pass",
    "corrective_actions": [],
}

VALID_REVIEW_REVISE = {
    "bugs": ["Missing error handling"],
    "scope_deviations": [],
    "design_conformity": {"conforms": True, "deviations": []},
    "convention_violations": [],
    "security_risks": [],
    "performance_risks": [],
    "tech_debt": [],
    "out_of_scope_files": [],
    "success_criteria_met": [],
    "verdict": "revise",
    "corrective_actions": ["Add try/except around IO calls"],
}

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
    "assumptions": [],
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


def _write_execute_state(project_ai: Path) -> None:
    """Create STATE.json at execute stage with all 5 approvals True."""
    state_data = {
        "current_stage": "execute",
        "approvals": {
            "brief_approved": True,
            "research_approved": True,
            "design_approved": True,
            "plan_approved": True,
            "execute_approved": True,
            "review_approved": False,
        },
        "completed_tasks": [],
        "history": [],
        "metadata": {},
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
    (project_ai / "BRIEF.md").write_text("# Brief\n", encoding="utf-8")
    (project_ai / "RESEARCH.json").write_text(
        '{"project_overview": "test", "tech_stack": [], "architecture_patterns": [],'
        ' "relevant_files": [], "existing_conventions": ["Use Pydantic"], "dependencies_map": {},'
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
    (project_ai / "EXECUTION_LOG.json").write_text(
        json.dumps(VALID_EXECUTION_LOG), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReviewCommand:
    def _mock_all(
        self,
        monkeypatch,
        project_ai: Path,
        *,
        approve_review: bool = True,
        verdict: str = "pass",
        fail_llm: bool = False,
    ) -> None:
        """Shared mock setup for review command tests."""
        from minilegion.core.schemas import ReviewSchema

        review_dict = (
            VALID_REVIEW_PASS.copy()
            if verdict == "pass"
            else VALID_REVIEW_REVISE.copy()
        )
        mock_review = ReviewSchema(**review_dict)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Review {{project_name}} {{diff_text}} {{plan_json}} {{design_json}} {{conventions}}",
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
                lambda *a, **kw: mock_review,
            )

        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm",
            lambda *a, **kw: approve_review,
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.generate_diff_text",
            lambda *a, **kw: "diff text",
        )

    def test_review_calls_preflight(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        called_with = {}

        def mock_preflight(stage, pd, skip_stages=None):
            called_with["stage"] = stage

        self._mock_all(monkeypatch, project_ai)
        monkeypatch.setattr("minilegion.cli.commands.check_preflight", mock_preflight)

        runner.invoke(app, ["review"])

        from minilegion.core.state import Stage

        assert called_with.get("stage") == Stage.REVIEW

    def test_review_calls_llm_with_review_artifact(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        called_with = {}
        from minilegion.core.schemas import ReviewSchema

        mock_review = ReviewSchema(**VALID_REVIEW_PASS)

        def mock_validate(llm_call, prompt, artifact, config, pd):
            called_with["artifact"] = artifact
            return mock_review

        self._mock_all(monkeypatch, project_ai)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate
        )

        runner.invoke(app, ["review"])

        assert called_with.get("artifact") == "review"

    def test_review_saves_review_files(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        self._mock_all(monkeypatch, project_ai)

        runner.invoke(app, ["review"])

        assert (project_ai / "REVIEW.json").exists()
        assert (project_ai / "REVIEW.md").exists()

    def test_review_pass_transitions_state(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve_review=True, verdict="pass")

        runner.invoke(app, ["review"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "review"

    def test_review_pass_sets_review_approved(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve_review=True, verdict="pass")

        runner.invoke(app, ["review"])

        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["approvals"]["review_approved"] is True

    def test_review_rejection_exits_0(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        self._mock_all(monkeypatch, project_ai, approve_review=False)

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 0
        assert "rejected" in result.output.lower()

    def test_review_llm_error_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        self._mock_all(monkeypatch, project_ai, fail_llm=True)

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 1

    def test_review_revise_triggers_builder_rerun(self, monkeypatch, tmp_path):
        """When verdict=revise, builder validate_with_retry is called again."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        call_count = {"n": 0}
        from minilegion.core.schemas import ReviewSchema, ExecutionLogSchema

        def mock_validate(llm_call, prompt, artifact, config, pd):
            call_count["n"] += 1
            if artifact == "execution_log":
                return ExecutionLogSchema(**VALID_EXECUTION_LOG)
            if call_count["n"] == 1:
                # First review call → revise
                return ReviewSchema(**VALID_REVIEW_REVISE)
            # Second review call → pass
            return ReviewSchema(**VALID_REVIEW_PASS)

        def mock_load_prompt(role):
            if role == "reviewer":
                return (
                    "system prompt",
                    "{{project_name}} {{diff_text}} {{plan_json}} {{design_json}} {{conventions}}",
                )
            # builder
            return (
                "system prompt",
                "{{project_name}} {{plan_json}} {{source_files}} {{corrective_actions}}",
            )

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr("minilegion.cli.commands.load_prompt", mock_load_prompt)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.generate_diff_text", lambda *a, **kw: "diff"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_scope", lambda *a, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.apply_patch",
            lambda cf, root, dry_run=False: f"CREATE {cf.path}",
        )

        runner.invoke(app, ["review"])

        # Should have been called at least 3 times: review(revise) + execution_log + review(pass)
        assert call_count["n"] >= 3

    def test_review_revise_count_incremented(self, monkeypatch, tmp_path):
        """After a revise, state.metadata['revise_count'] is incremented."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        from minilegion.core.schemas import ReviewSchema, ExecutionLogSchema

        call_count = {"n": 0}

        def mock_validate(llm_call, prompt, artifact, config, pd):
            call_count["n"] += 1
            if artifact == "execution_log":
                return ExecutionLogSchema(**VALID_EXECUTION_LOG)
            if call_count["n"] == 1:
                return ReviewSchema(**VALID_REVIEW_REVISE)
            return ReviewSchema(**VALID_REVIEW_PASS)

        def mock_load_prompt(role):
            if role == "reviewer":
                return (
                    "system prompt",
                    "{{project_name}} {{diff_text}} {{plan_json}} {{design_json}} {{conventions}}",
                )
            return (
                "system prompt",
                "{{project_name}} {{plan_json}} {{source_files}} {{corrective_actions}}",
            )

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr("minilegion.cli.commands.load_prompt", mock_load_prompt)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.generate_diff_text", lambda *a, **kw: "diff"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_scope", lambda *a, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.apply_patch",
            lambda cf, root, dry_run=False: f"CREATE {cf.path}",
        )

        runner.invoke(app, ["review"])

        # After revise(1) + review(pass), state should be at "review"
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "review"

    def test_review_revise_limit_escalates(self, monkeypatch, tmp_path):
        """When revise_count reaches max, escalation message is shown."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        # Pre-set revise_count to max
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        state_data["metadata"] = {"revise_count": "2"}
        (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")

        from minilegion.core.schemas import ReviewSchema

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "{{project_name}} {{diff_text}} {{plan_json}} {{design_json}} {{conventions}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: ReviewSchema(**VALID_REVIEW_REVISE),
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.generate_diff_text", lambda *a, **kw: "diff"
        )

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 0
        assert "limit" in result.output.lower() or "manual" in result.output.lower()

    def test_review_design_nonconformity_shows_redesign_prompt(
        self, monkeypatch, tmp_path
    ):
        """When design_conformity.conforms=False and verdict=revise, re-design prompt shown."""
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        from minilegion.core.schemas import ReviewSchema

        nonconform_review = {
            **VALID_REVIEW_REVISE,
            "design_conformity": {
                "conforms": False,
                "deviations": ["Wrong pattern used"],
            },
        }

        def mock_load_prompt(role):
            if role == "reviewer":
                return (
                    "system prompt",
                    "{{project_name}} {{diff_text}} {{plan_json}} {{design_json}} {{conventions}}",
                )
            # builder
            return (
                "system prompt",
                "{{project_name}} {{plan_json}} {{source_files}} {{corrective_actions}}",
            )

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr("minilegion.cli.commands.load_prompt", mock_load_prompt)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: ReviewSchema(**nonconform_review),
        )
        # approval gate confirm (approve_review) → True
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm",
            lambda *a, **kw: True,
        )
        # re-design prompt confirm (called directly in commands.py) → False (decline re-design)
        monkeypatch.setattr(
            "minilegion.cli.commands.typer.confirm",
            lambda *a, **kw: False,
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.generate_diff_text", lambda *a, **kw: "diff"
        )

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 0
        assert (
            "re-design" in result.output.lower()
            or "redesign" in result.output.lower()
            or "design" in result.output.lower()
        )

    def test_review_preflight_failure_exits_1(self, monkeypatch, tmp_path):
        project_ai = tmp_path / "myproject" / "project-ai"
        project_ai.mkdir(parents=True)
        _write_execute_state(project_ai)

        from minilegion.core.exceptions import PreflightError

        self._mock_all(monkeypatch, project_ai)
        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight",
            lambda s, pd: (_ for _ in ()).throw(
                PreflightError("EXECUTION_LOG.json missing")
            ),
        )

        result = runner.invoke(app, ["review"])

        assert result.exit_code == 1
