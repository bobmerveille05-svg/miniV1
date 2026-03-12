"""Tests for rollback and doctor CLI commands."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from minilegion.cli import app

runner = CliRunner()


def _write_state(
    project_ai: Path,
    current_stage: str,
    approvals: dict[str, bool] | None = None,
) -> None:
    """Write a minimal STATE.json for testing."""
    default_approvals: dict[str, bool] = {
        k: False
        for k in [
            "brief_approved",
            "research_approved",
            "design_approved",
            "plan_approved",
            "execute_approved",
            "review_approved",
        ]
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


class TestRollback:
    """Tests for `minilegion rollback "<reason>"` command."""

    def test_rollback_resets_stage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rolling back from design should reset STATE.json current_stage to research."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        (project_ai / "DESIGN.json").write_text('{"data": "ok"}', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["rollback", "rejected"])

        assert result.exit_code == 0
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "research"

    def test_rollback_moves_artifact_to_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rolling back from design should move DESIGN.json to rejected/ with timestamped name."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        (project_ai / "DESIGN.json").write_text(
            '{"important": "data"}', encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["rollback", "bad design"])

        assert result.exit_code == 0
        # Original artifact should be gone
        assert not (project_ai / "DESIGN.json").exists()
        # Rejected dir should exist and contain the file
        rejected_dir = project_ai / "rejected"
        assert rejected_dir.exists()
        pattern = re.compile(r"DESIGN\.\d{8}T\d{6}Z\.rejected\.json")
        rejected_files = list(rejected_dir.iterdir())
        assert len(rejected_files) == 1
        assert pattern.match(rejected_files[0].name), (
            f"Unexpected name: {rejected_files[0].name}"
        )
        # Content should be preserved
        assert rejected_files[0].read_text(encoding="utf-8") == '{"important": "data"}'

    def test_rollback_from_init_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rolling back from init should exit 1 with a clear error — no state mutation."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "init")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["rollback", "oops"])

        assert result.exit_code == 1
        output_lower = result.output.lower()
        assert "init" in output_lower or "first" in output_lower
        # State must not have changed
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "init"

    def test_rollback_no_artifact_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rolling back from design with no artifact present should still succeed (artifact_moved=None)."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        # Intentionally no DESIGN.json
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["rollback", "no art"])

        assert result.exit_code == 0
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "research"
        # No rejected dir or it's empty
        rejected_dir = project_ai / "rejected"
        if rejected_dir.exists():
            assert len(list(rejected_dir.iterdir())) == 0

    def test_rollback_clears_downstream_approvals(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rolling back from plan should clear design and plan approvals, keep brief/research."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(
            project_ai,
            "plan",
            approvals={
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
                "plan_approved": True,
            },
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["rollback", "plan bad"])

        assert result.exit_code == 0
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        # brief and research should remain approved
        assert state_data["approvals"]["brief_approved"] is True
        assert state_data["approvals"]["research_approved"] is True
        # design and plan approvals must be cleared (rolled back TO design, so design+ cleared)
        assert state_data["approvals"]["design_approved"] is False
        assert state_data["approvals"]["plan_approved"] is False

    def test_rollback_appends_history_event(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rolling back should append a history event with event_type='rollback' and correct notes."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        (project_ai / "DESIGN.json").write_text(
            '{"data": "to reject"}', encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["rollback", "not good"])

        assert result.exit_code == 0
        history_dir = project_ai / "history"
        assert history_dir.exists()
        history_files = list(history_dir.glob("*.json"))
        assert len(history_files) >= 1

        # Get the last (most recent) history event by filename
        last_file = max(history_files, key=lambda p: p.name)
        event_data = json.loads(last_file.read_text(encoding="utf-8"))
        assert event_data["event_type"] == "rollback"

        notes = json.loads(event_data["notes"])
        assert notes["reason"] == "not good"
        assert notes["from_stage"] == "design"
        assert notes["to_stage"] == "research"
        assert notes["artifact_moved"] is not None


class TestDoctor:
    """Tests for `minilegion doctor` command."""

    def test_doctor_healthy_project_exits_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fully healthy project should exit 0, output Doctor: pass, and show ≥4 [PASS] lines."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "research")
        (project_ai / "RESEARCH.json").write_text('{"data": "ok"}', encoding="utf-8")
        (project_ai / "BRIEF.md").write_text("# Brief", encoding="utf-8")
        history_dir = project_ai / "history"
        history_dir.mkdir()
        event = {
            "event_type": "init",
            "stage": "init",
            "timestamp": "2026-03-12T00:00:00",
            "actor": "system",
            "tool_used": "minilegion",
            "notes": "",
        }
        (history_dir / "001_init.json").write_text(json.dumps(event), encoding="utf-8")
        adapters_dir = project_ai / "adapters"
        adapters_dir.mkdir()
        (adapters_dir / "_base.md").write_text("# Base", encoding="utf-8")
        (adapters_dir / "claude.md").write_text("# Claude", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "Doctor: pass" in result.output
        assert result.output.count("[PASS]") >= 4

    def test_doctor_invalid_state_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid STATE.json should produce [FAIL] output and exit code 2."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        (project_ai / "STATE.json").write_text("not valid json!!!", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 2
        assert "[FAIL]" in result.output
        assert "Doctor: fail" in result.output

    def test_doctor_missing_artifact_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing current-stage artifact should produce [FAIL] and exit 2."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        # Intentionally no DESIGN.json
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 2
        assert "[FAIL]" in result.output

    def test_doctor_corrupt_history_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Corrupt history event file should produce a warning and exit ≥1."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "research")
        (project_ai / "RESEARCH.json").write_text('{"data": "ok"}', encoding="utf-8")
        history_dir = project_ai / "history"
        history_dir.mkdir()
        (history_dir / "001_corrupt.json").write_text(
            "not-valid-json!!!", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code >= 1
        assert "[WARN]" in result.output or "[FAIL]" in result.output

    def test_doctor_stage_artifact_mismatch_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stage=design with no DESIGN.json should fail stage_coherence check."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        (project_ai / "BRIEF.md").write_text("# Brief", encoding="utf-8")
        (project_ai / "RESEARCH.json").write_text('{"data": "ok"}', encoding="utf-8")
        # Intentionally no DESIGN.json
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 2
        assert "stage_coherence" in result.output

    def test_doctor_missing_adapter_base_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing _base.md should produce [WARN] for adapter_base, exit 1."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "init")
        adapters_dir = project_ai / "adapters"
        adapters_dir.mkdir()
        # Intentionally no _base.md
        (adapters_dir / "claude.md").write_text("# Claude", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "[WARN]" in result.output
        assert "adapter_base" in result.output

    def test_doctor_warn_only_exits_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A project with only WARN-level issues (missing history) should exit 1 with Doctor: warn."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "init")
        # No artifact required for init stage
        adapters_dir = project_ai / "adapters"
        adapters_dir.mkdir()
        (adapters_dir / "_base.md").write_text("# Base", encoding="utf-8")
        (adapters_dir / "claude.md").write_text("# Claude", encoding="utf-8")
        # history/ intentionally absent → WARN
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 1
        assert "Doctor: warn" in result.output

    def test_doctor_output_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every output line should match [PASS/WARN/FAIL] or Doctor: prefix."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "research")
        (project_ai / "RESEARCH.json").write_text('{"data": "ok"}', encoding="utf-8")
        (project_ai / "BRIEF.md").write_text("# Brief", encoding="utf-8")
        history_dir = project_ai / "history"
        history_dir.mkdir()
        event = {
            "event_type": "init",
            "stage": "init",
            "timestamp": "2026-03-12T00:00:00",
            "actor": "system",
            "tool_used": "minilegion",
            "notes": "",
        }
        (history_dir / "001_init.json").write_text(json.dumps(event), encoding="utf-8")
        adapters_dir = project_ai / "adapters"
        adapters_dir.mkdir()
        (adapters_dir / "_base.md").write_text("# Base", encoding="utf-8")
        (adapters_dir / "claude.md").write_text("# Claude", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        for line in result.output.strip().splitlines():
            assert re.match(r"^\[(PASS|WARN|FAIL)\] |^Doctor:", line), (
                f"Unexpected line: {line!r}"
            )

    def test_doctor_summary_line(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Output should end with 'Doctor: fail' when there is a FAIL-level issue."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_state(project_ai, "design")
        # Intentionally no DESIGN.json → FAIL
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])

        assert result.output.strip().endswith("Doctor: fail")
