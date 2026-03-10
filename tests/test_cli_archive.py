"""Tests for the archive() CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
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

VALID_EXECUTION_LOG = {
    "tasks": [
        {
            "task_id": "T1",
            "changed_files": [
                {
                    "path": "minilegion/core/new_module.py",
                    "action": "create",
                    "content": "",
                }
            ],
            "unchanged_files": [],
            "tests_run": [],
            "test_result": "",
            "blockers": [],
            "out_of_scope_needed": [],
        },
        {
            "task_id": "T2",
            "changed_files": [],
            "unchanged_files": [],
            "tests_run": [],
            "test_result": "",
            "blockers": [],
            "out_of_scope_needed": [],
        },
    ]
}

VALID_PLAN = {
    "objective": "Implement core module",
    "design_ref": "DESIGN.json v1",
    "assumptions": [],
    "tasks": [
        {
            "id": "T1",
            "name": "Create module",
            "description": "Create the module",
            "files": ["minilegion/core/new_module.py"],
            "depends_on": [],
            "component": "Core",
        },
        {
            "id": "T2",
            "name": "Test module",
            "description": "Write tests",
            "files": [],
            "depends_on": ["T1"],
            "component": "Core",
        },
    ],
    "touched_files": ["minilegion/core/new_module.py"],
    "risks": [],
    "success_criteria": ["Module importable"],
    "test_plan": "pytest",
}

VALID_DESIGN = {
    "design_approach": "Layered architecture",
    "architecture_decisions": [
        {
            "decision": "Use dataclasses",
            "rationale": "Simple and effective",
            "alternatives_rejected": ["Pydantic"],
        }
    ],
    "components": [
        {
            "name": "Core",
            "description": "Core module",
            "files": ["minilegion/core/new_module.py"],
        }
    ],
    "data_models": [],
    "api_contracts": [],
    "integration_points": [],
    "design_patterns_used": [],
    "conventions_to_follow": [],
    "technical_risks": [],
    "out_of_scope": [],
    "test_strategy": "Unit tests",
    "estimated_complexity": "low",
}


def _write_review_state(project_ai: Path, review_approved: bool = True) -> None:
    """Write STATE.json at review stage with review_approved as specified."""
    state_data = {
        "current_stage": "review",
        "approvals": {
            "brief_approved": True,
            "research_approved": True,
            "design_approved": True,
            "plan_approved": True,
            "execute_approved": True,
            "review_approved": review_approved,
        },
        "completed_tasks": [],
        "history": [],
        "metadata": {},
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")


def _setup_archive_artifacts(project_ai: Path) -> None:
    """Write all 4 required JSON artifacts for archive."""
    (project_ai / "REVIEW.json").write_text(
        json.dumps(VALID_REVIEW_PASS), encoding="utf-8"
    )
    (project_ai / "EXECUTION_LOG.json").write_text(
        json.dumps(VALID_EXECUTION_LOG), encoding="utf-8"
    )
    (project_ai / "PLAN.json").write_text(json.dumps(VALID_PLAN), encoding="utf-8")
    (project_ai / "DESIGN.json").write_text(json.dumps(VALID_DESIGN), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestArchiveNoLlmCalls:
    """ARCH-01: archive command makes zero LLM calls."""

    def test_archive_no_llm_calls(self, tmp_project_dir, monkeypatch):
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)
        _setup_archive_artifacts(project_ai)

        with (
            patch("minilegion.adapters.factory.get_adapter") as mock_adapter,
            patch("minilegion.cli.commands.load_config") as mock_config,
        ):
            result = runner.invoke(app, ["archive"])
            mock_adapter.assert_not_called()
            mock_config.assert_not_called()

        assert result.exit_code == 0


class TestArchiveStateUpdates:
    """ARCH-02: archive updates STATE.json correctly."""

    def test_archive_sets_completed_tasks(self, tmp_project_dir, monkeypatch):
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)
        _setup_archive_artifacts(project_ai)

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["completed_tasks"] == ["T1", "T2"]

    def test_archive_sets_final_verdict(self, tmp_project_dir, monkeypatch):
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)
        _setup_archive_artifacts(project_ai)

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["metadata"]["final_verdict"] == "pass"

    def test_archive_adds_history_entry(self, tmp_project_dir, monkeypatch):
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)
        _setup_archive_artifacts(project_ai)

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        actions = [entry.get("action") for entry in state["history"]]
        assert "archive" in actions

    def test_archive_transitions_state(self, tmp_project_dir, monkeypatch):
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)
        _setup_archive_artifacts(project_ai)

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["current_stage"] == "archive"

    def test_archive_preflight_requires_review_approved(
        self, tmp_project_dir, monkeypatch
    ):
        """archive exits 1 when review_approved=False."""
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai, review_approved=False)
        _setup_archive_artifacts(project_ai)

        result = runner.invoke(app, ["archive"])
        assert result.exit_code != 0


class TestArchiveDecisionsMd:
    """ARCH-03: archive writes DECISIONS.md."""

    def test_archive_writes_decisions_md(self, tmp_project_dir, monkeypatch):
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)
        _setup_archive_artifacts(project_ai)

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output

        decisions_md = project_ai / "DECISIONS.md"
        assert decisions_md.exists()
        content = decisions_md.read_text(encoding="utf-8")
        assert "# Architecture Decisions" in content
        assert "Use dataclasses" in content


class TestArchiveCoherence:
    """COHR integration: coherence issues printed and stored in metadata."""

    def test_archive_coherence_issues_printed_as_warnings_or_errors(
        self, tmp_project_dir, monkeypatch
    ):
        """Archive prints coherence issues as [WARNING] or [ERROR]."""
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)

        # Create an execution log with a file NOT in plan's touched_files → COHR-03 error
        log_with_surprise = {
            "tasks": [
                {
                    "task_id": "T1",
                    "changed_files": [
                        {
                            "path": "minilegion/core/surprise.py",
                            "action": "create",
                            "content": "",
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
        (project_ai / "REVIEW.json").write_text(
            json.dumps(VALID_REVIEW_PASS), encoding="utf-8"
        )
        (project_ai / "EXECUTION_LOG.json").write_text(
            json.dumps(log_with_surprise), encoding="utf-8"
        )
        (project_ai / "PLAN.json").write_text(json.dumps(VALID_PLAN), encoding="utf-8")
        (project_ai / "DESIGN.json").write_text(
            json.dumps(VALID_DESIGN), encoding="utf-8"
        )

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output
        assert "[WARNING]" in result.output or "[ERROR]" in result.output

    def test_archive_coherence_issues_stored_in_metadata(
        self, tmp_project_dir, monkeypatch
    ):
        """Archive stores coherence issues JSON in state.metadata['coherence_issues']."""
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )
        _write_review_state(project_ai)

        # Design conformity=False → COHR-04 error
        review_nonconforming = dict(VALID_REVIEW_PASS)
        review_nonconforming["design_conformity"] = {
            "conforms": False,
            "deviations": ["Missing tests"],
        }
        (project_ai / "REVIEW.json").write_text(
            json.dumps(review_nonconforming), encoding="utf-8"
        )
        (project_ai / "EXECUTION_LOG.json").write_text(
            json.dumps(VALID_EXECUTION_LOG), encoding="utf-8"
        )
        (project_ai / "PLAN.json").write_text(json.dumps(VALID_PLAN), encoding="utf-8")
        (project_ai / "DESIGN.json").write_text(
            json.dumps(VALID_DESIGN), encoding="utf-8"
        )

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0, result.output

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert "coherence_issues" in state["metadata"]
        issues = json.loads(state["metadata"]["coherence_issues"])
        assert len(issues) >= 1


class TestArchiveGuards:
    """Transition guard and wrong-stage handling."""

    def test_archive_wrong_stage_exits_1(self, tmp_project_dir, monkeypatch):
        """archive exits 1 when called from a non-review stage."""
        project_ai = tmp_project_dir / "project-ai"
        monkeypatch.setattr(
            "minilegion.cli.commands.find_project_dir", lambda: project_ai
        )

        # Put state at "brief" — cannot transition to archive from here
        state_data = {
            "current_stage": "brief",
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

        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 1
