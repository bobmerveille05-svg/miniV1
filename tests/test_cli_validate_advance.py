"""Tests for validate/advance CLI commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()


def _write_state(
    project_ai, current_stage: str, approvals: dict[str, bool] | None = None
):
    default_approvals = {
        "brief_approved": False,
        "research_approved": False,
        "design_approved": False,
        "plan_approved": False,
        "execute_approved": False,
        "review_approved": False,
    }
    if approvals:
        default_approvals.update(approvals)
    state_data = {
        "current_stage": current_stage,
        "approvals": default_approvals,
        "completed_tasks": [],
        "metadata": {},
    }
    (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")


class TestValidate:
    def test_validate_pass_writes_evidence_and_keeps_stage(self, tmp_path, monkeypatch):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "brief")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda stage, pd, **kw: None
        )

        result = runner.invoke(app, ["validate", "brief"])
        assert result.exit_code == 0, result.output

        evidence_path = project_ai / "evidence" / "brief.validation.json"
        assert evidence_path.exists()

        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert evidence["step"] == "brief"
        assert evidence["status"] == "pass"

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["current_stage"] == "brief"

    def test_validate_fail_writes_evidence_and_exits_nonzero(
        self, tmp_path, monkeypatch
    ):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "brief")
        monkeypatch.chdir(tmp_path)

        from minilegion.core.exceptions import PreflightError

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight",
            lambda stage, pd, **kw: (_ for _ in ()).throw(
                PreflightError("Missing required approval: brief_approved")
            ),
        )

        result = runner.invoke(app, ["validate", "brief"])
        assert result.exit_code == 1

        evidence_path = project_ai / "evidence" / "brief.validation.json"
        assert evidence_path.exists()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert evidence["status"] == "fail"

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["current_stage"] == "brief"


class TestAdvancePass:
    def test_advance_with_passing_evidence_moves_one_stage(self, tmp_path, monkeypatch):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(
            project_ai,
            "brief",
            approvals={"brief_approved": True},
        )
        monkeypatch.chdir(tmp_path)

        evidence_dir = project_ai / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "brief.validation.json").write_text(
            json.dumps(
                {
                    "step": "brief",
                    "status": "pass",
                    "checks_passed": ["brief_approved"],
                    "validator": "preflight",
                    "tool_used": "minilegion",
                    "date": "2026-03-12T00:00:00",
                    "notes": "ok",
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(app, ["advance"])
        assert result.exit_code == 0, result.output

        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["current_stage"] == "research"
        history_files = list((project_ai / "history").glob("*.json"))
        assert history_files


class TestAdvanceReject:
    def test_advance_missing_evidence_exits_nonzero(self, tmp_path, monkeypatch):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "brief")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["advance"])
        assert result.exit_code == 1
        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["current_stage"] == "brief"

    def test_advance_failing_evidence_exits_nonzero(self, tmp_path, monkeypatch):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "brief")
        monkeypatch.chdir(tmp_path)

        evidence_dir = project_ai / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "brief.validation.json").write_text(
            json.dumps(
                {
                    "step": "brief",
                    "status": "fail",
                    "checks_passed": [],
                    "validator": "preflight",
                    "tool_used": "minilegion",
                    "date": "2026-03-12T00:00:00",
                    "notes": "missing approval",
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(app, ["advance"])
        assert result.exit_code == 1
        state = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state["current_stage"] == "brief"
