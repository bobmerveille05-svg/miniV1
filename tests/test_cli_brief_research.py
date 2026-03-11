"""Tests for brief and research CLI commands (Phase 6)."""

import json

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
        "history": [],
        "completed_tasks": [],
        "metadata": {},
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
            runner.invoke(app, ["brief", "some text"])

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
        # Capture original STATE.json content (kept for documentation only)
        monkeypatch.chdir(tmp_path)

        with patch("minilegion.core.approval.typer.confirm", return_value=False):
            runner.invoke(app, ["brief", "rejected text"])

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
        """research() calls check_preflight(Stage.RESEARCH, project_dir)."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        preflight_calls = []

        def mock_preflight(stage, project_dir, skip_stages=None):
            preflight_calls.append((stage, project_dir))

        monkeypatch.setattr("minilegion.cli.commands.check_preflight", mock_preflight)
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "codebase context"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.save_dual", lambda data, jp, mp: None
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        # Also mock read_text on RESEARCH.md path since save_dual is mocked
        (project_ai / "RESEARCH.md").write_text("# Research Report\n", encoding="utf-8")

        runner.invoke(app, ["research"])
        assert len(preflight_calls) == 1
        from minilegion.core.state import Stage

        assert preflight_calls[0][0] == Stage.RESEARCH

    def test_research_preflight_failure_exits_1(self, tmp_path, monkeypatch):
        """PreflightError from check_preflight exits with code 1 and red message."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.exceptions import PreflightError

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight",
            lambda stage, project_dir: (_ for _ in ()).throw(
                PreflightError("Missing required file: BRIEF.md")
            ),
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 1
        assert "Missing required file" in result.output or "BRIEF.md" in result.output

    def test_research_runs_scanner(self, tmp_path, monkeypatch):
        """research() calls scan_codebase(project_dir, config)."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        scan_calls = []

        def mock_scan(project_dir, config):
            scan_calls.append((project_dir, config))
            return "scanned context"

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr("minilegion.cli.commands.scan_codebase", mock_scan)
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "system prompt",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.save_dual", lambda data, jp, mp: None
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        (project_ai / "RESEARCH.md").write_text("# Research Report\n", encoding="utf-8")

        runner.invoke(app, ["research"])
        assert len(scan_calls) == 1
        assert scan_calls[0][0] == project_ai

    def test_research_calls_llm(self, tmp_path, monkeypatch):
        """research() calls validate_with_retry with correct 5-arg signature."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        retry_calls = []

        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)

        def mock_validate_with_retry(
            llm_call, prompt, artifact_name, config, project_dir
        ):
            retry_calls.append(
                {
                    "artifact_name": artifact_name,
                    "config": config,
                    "project_dir": project_dir,
                }
            )
            return mock_research

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "context"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry", mock_validate_with_retry
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.save_dual", lambda data, jp, mp: None
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        (project_ai / "RESEARCH.md").write_text("# Research Report\n", encoding="utf-8")

        runner.invoke(app, ["research"])
        assert len(retry_calls) == 1
        assert retry_calls[0]["artifact_name"] == "research"
        assert retry_calls[0]["project_dir"] == project_ai

    def test_research_saves_dual_output(self, tmp_path, monkeypatch):
        """research() calls save_dual and RESEARCH.json + RESEARCH.md are created."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        # Use real save_dual so files are actually written
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        assert (project_ai / "RESEARCH.json").exists()
        assert (project_ai / "RESEARCH.md").exists()
        assert "RESEARCH.json + RESEARCH.md saved." in result.output

    def test_research_approval_accepted_transitions_state(self, tmp_path, monkeypatch):
        """Approved research transitions STATE.json current_stage from 'brief' to 'research'."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "research"
        assert state_data["approvals"].get("research_approved") is True

    def test_research_rejection_leaves_state_unchanged(self, tmp_path, monkeypatch):
        """Rejected research leaves STATE.json current_stage as 'brief'."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )

        runner.invoke(app, ["research"])
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        assert state_data["current_stage"] == "brief"

    def test_research_rejection_exits_0(self, tmp_path, monkeypatch):
        """Rejected research exits with code 0 (rejection is not an error)."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}: {result.output}"
        )
        assert "rejected" in result.output.lower()

    def test_research_llm_error_exits_1(self, tmp_path, monkeypatch):
        """LLM error (LLMError/MiniLegionError) from validate_with_retry exits with code 1."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.exceptions import LLMError

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: (_ for _ in ()).throw(LLMError("API connection failed")),
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 1
        assert (
            "API connection failed" in result.output or "error" in result.output.lower()
        )

    def test_research_missing_brief_md_exits_1(self, tmp_path, monkeypatch):
        """research without BRIEF.md (real preflight) exits with code 1."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        # Write brief state but do NOT create BRIEF.md
        state_data = {
            "current_stage": "brief",
            "approvals": {"brief_approved": True},
            "history": [],
            "completed_tasks": [],
            "metadata": {},
        }
        (project_ai / "STATE.json").write_text(json.dumps(state_data), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 1
        assert "BRIEF.md" in result.output or "Missing" in result.output

    def test_research_state_current_stage_is_research_after_approval(
        self, tmp_path, monkeypatch
    ):
        """STATE.json has current_stage == 'research' after successful approval (sync gap test)."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        _write_brief_state(project_ai)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)

        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        state_data = json.loads((project_ai / "STATE.json").read_text(encoding="utf-8"))
        # Verify state.current_stage was synced before save_state (the sync gap fix)
        assert state_data["current_stage"] == "research", (
            f"Expected 'research', got '{state_data['current_stage']}'"
        )


class TestResearchHealthcheckGate:
    """Tests for provider healthcheck gate wired into research()."""

    def _setup(self, project_ai, monkeypatch):
        """Common mock setup for research command tests."""
        _write_brief_state(project_ai)
        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)
        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: "ctx"
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )

    def test_healthcheck_called_before_scanner_when_enabled(
        self, tmp_path, monkeypatch
    ):
        """run_provider_healthcheck() is called before scan_codebase() when enabled."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        call_order = []

        monkeypatch.setattr(
            "minilegion.cli.commands.run_provider_healthcheck",
            lambda cfg: call_order.append("healthcheck"),
        )
        original_scan = monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase",
            lambda pd, cfg: call_order.append("scan") or "ctx",
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        assert "healthcheck" in call_order, "healthcheck was not called"
        assert "scan" in call_order, "scan was not called"
        assert call_order.index("healthcheck") < call_order.index("scan"), (
            "healthcheck must run before scan"
        )

    def test_healthcheck_failure_exits_1_without_calling_scanner(
        self, tmp_path, monkeypatch
    ):
        """Failed healthcheck exits code 1 and never calls scan_codebase()."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.exceptions import ConfigError

        scan_called = []
        monkeypatch.setattr(
            "minilegion.cli.commands.run_provider_healthcheck",
            lambda cfg: (_ for _ in ()).throw(
                ConfigError("OPENAI_API_KEY not set. Export OPENAI_API_KEY first.")
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase",
            lambda pd, cfg: scan_called.append(True) or "ctx",
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 1, result.output
        assert len(scan_called) == 0, (
            "scan_codebase must NOT be called after healthcheck failure"
        )
        assert "OPENAI_API_KEY" in result.output or "not set" in result.output.lower()

    def test_healthcheck_failure_exits_1_without_calling_llm(
        self, tmp_path, monkeypatch
    ):
        """Failed healthcheck exits code 1 and never calls validate_with_retry()."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        from minilegion.core.exceptions import ConfigError

        llm_called = []
        monkeypatch.setattr(
            "minilegion.cli.commands.run_provider_healthcheck",
            lambda cfg: (_ for _ in ()).throw(ConfigError("Provider not ready.")),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: llm_called.append(True),
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 1
        assert len(llm_called) == 0, "LLM must NOT be called after healthcheck failure"

    def test_healthcheck_skipped_when_disabled_in_config(self, tmp_path, monkeypatch):
        """run_provider_healthcheck() is not called when provider_healthcheck=False."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        # Write config with healthcheck disabled
        import json as _json

        config_data = {"provider_healthcheck": False}
        (project_ai / "minilegion.config.json").write_text(
            _json.dumps(config_data), encoding="utf-8"
        )

        healthcheck_called = []
        monkeypatch.setattr(
            "minilegion.cli.commands.run_provider_healthcheck",
            lambda cfg: healthcheck_called.append(True),
        )

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        assert len(healthcheck_called) == 0, (
            "run_provider_healthcheck must NOT be called when provider_healthcheck=False"
        )


class TestResearchContextCompaction:
    """Tests for context_auto_compact wired into research()."""

    def _setup(self, project_ai, monkeypatch):
        """Common mock setup — all external calls mocked."""
        _write_brief_state(project_ai)
        from minilegion.core.schemas import ResearchSchema

        mock_research = ResearchSchema(**VALID_RESEARCH)
        monkeypatch.setattr(
            "minilegion.cli.commands.check_preflight", lambda s, pd, **kw: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.run_provider_healthcheck", lambda cfg: None
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.load_prompt",
            lambda role: (
                "sys",
                "Research {{project_name}} {{brief_content}} {{codebase_context}}",
            ),
        )
        monkeypatch.setattr(
            "minilegion.cli.commands.validate_with_retry",
            lambda *a, **kw: mock_research,
        )
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )

    def test_compaction_truncates_oversized_context(self, tmp_path, monkeypatch):
        """Context exceeding threshold is truncated with explicit marker when auto_compact=True."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        # Produce oversized codebase context (> 50_000 chars)
        big_context = "x" * 60_000
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: big_context
        )

        # Write config with compaction enabled
        import json as _json

        config_data = {"context_auto_compact": True}
        (project_ai / "minilegion.config.json").write_text(
            _json.dumps(config_data), encoding="utf-8"
        )

        # Capture what user_message render_prompt received as codebase_context
        captured_contexts = []
        original_render = __import__(
            "minilegion.prompts.loader", fromlist=["render_prompt"]
        ).render_prompt

        def capturing_render(template, **kwargs):
            captured_contexts.append(kwargs.get("codebase_context", ""))
            return original_render(template, **kwargs)

        monkeypatch.setattr("minilegion.cli.commands.render_prompt", capturing_render)

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        assert len(captured_contexts) == 1
        ctx = captured_contexts[0]
        # Compacted context must be shorter than the original
        assert len(ctx) < len(big_context), "compacted context should be smaller"
        # Compacted context must include a truncation marker
        assert "[CONTEXT TRUNCATED" in ctx or "[truncated" in ctx.lower(), (
            f"Expected truncation marker in compacted context, got: {ctx[:200]}"
        )

    def test_compaction_not_applied_when_disabled(self, tmp_path, monkeypatch):
        """Context is passed through unchanged when context_auto_compact=False."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        big_context = "x" * 60_000
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: big_context
        )

        import json as _json

        config_data = {"context_auto_compact": False}
        (project_ai / "minilegion.config.json").write_text(
            _json.dumps(config_data), encoding="utf-8"
        )

        captured_contexts = []
        original_render = __import__(
            "minilegion.prompts.loader", fromlist=["render_prompt"]
        ).render_prompt

        def capturing_render(template, **kwargs):
            captured_contexts.append(kwargs.get("codebase_context", ""))
            return original_render(template, **kwargs)

        monkeypatch.setattr("minilegion.cli.commands.render_prompt", capturing_render)

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        assert len(captured_contexts) == 1
        # Context should be passed unchanged
        assert captured_contexts[0] == big_context, (
            "Context must not be modified when context_auto_compact=False"
        )

    def test_compaction_not_applied_when_context_within_threshold(
        self, tmp_path, monkeypatch
    ):
        """Small context is passed through even when context_auto_compact=True."""
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()
        self._setup(project_ai, monkeypatch)
        monkeypatch.chdir(tmp_path)

        small_context = "small codebase context"
        monkeypatch.setattr(
            "minilegion.cli.commands.scan_codebase", lambda pd, cfg: small_context
        )

        import json as _json

        config_data = {"context_auto_compact": True}
        (project_ai / "minilegion.config.json").write_text(
            _json.dumps(config_data), encoding="utf-8"
        )

        captured_contexts = []
        original_render = __import__(
            "minilegion.prompts.loader", fromlist=["render_prompt"]
        ).render_prompt

        def capturing_render(template, **kwargs):
            captured_contexts.append(kwargs.get("codebase_context", ""))
            return original_render(template, **kwargs)

        monkeypatch.setattr("minilegion.cli.commands.render_prompt", capturing_render)

        result = runner.invoke(app, ["research"])
        assert result.exit_code == 0, result.output
        assert len(captured_contexts) == 1
        assert captured_contexts[0] == small_context, (
            "Small context must not be compacted"
        )


class TestScanMaxFileSizeNormalization:
    """Tests for scan_max_file_size vs scan_max_file_size_kb config field normalization."""

    def test_read_source_files_respects_scan_max_file_size_kb(self, tmp_path):
        """_read_source_files uses scan_max_file_size_kb (not a missing scan_max_file_size)."""
        from minilegion.cli.commands import _read_source_files
        from minilegion.core.config import MiniLegionConfig

        # Create a small file and a large file
        small = tmp_path / "small.py"
        large = tmp_path / "large.py"
        small.write_text("print('hello')", encoding="utf-8")
        large.write_text("x" * 200_000, encoding="utf-8")  # 200 KB

        # Default config: scan_max_file_size_kb = 100 (100 KB)
        config = MiniLegionConfig(scan_max_file_size_kb=100)
        result = _read_source_files(["small.py", "large.py"], tmp_path, config)

        assert "print('hello')" in result, "Small file should be included"
        assert "File too large" in result, "Large file should be flagged as too large"
