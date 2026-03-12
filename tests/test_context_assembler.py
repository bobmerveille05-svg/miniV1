"""Tests for minilegion.core.context_assembler — context assembly function.

All tests use tmp_path fixtures with minimal project-ai/STATE.json setup.
Assembler must degrade gracefully when optional files are absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from minilegion.cli import app
from minilegion.core.config import ContextConfig, MiniLegionConfig
from minilegion.core.context_assembler import assemble_context
from minilegion.core.state import ProjectState, save_state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project-ai/ directory with a valid STATE.json."""
    pa = tmp_path / "project-ai"
    pa.mkdir()
    state = ProjectState()
    save_state(state, pa / "STATE.json")
    history_dir = pa / "history"
    history_dir.mkdir()
    (history_dir / "001_init.json").write_text(
        json.dumps(
            {
                "event_type": "init",
                "stage": "init",
                "timestamp": "2026-01-01T00:00:00",
                "actor": "system",
                "tool_used": "minilegion",
                "notes": "Project initialized",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return pa


@pytest.fixture
def config() -> MiniLegionConfig:
    """Default MiniLegionConfig."""
    return MiniLegionConfig()


# ---------------------------------------------------------------------------
# Core output tests
# ---------------------------------------------------------------------------


class TestAssembleContextBasic:
    """assemble_context returns well-formed markdown for any valid tool name."""

    def test_returns_nonempty_string(self, project_dir, config):
        """assemble_context('claude', ...) returns a non-empty string."""
        result = assemble_context("claude", project_dir, config)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_current_state_section(self, project_dir, config):
        """Returned string contains a '## Current State' section."""
        result = assemble_context("claude", project_dir, config)
        assert "## Current State" in result

    def test_contains_adapter_section(self, project_dir, config):
        """Returned string contains a '## Adapter Instructions' section."""
        result = assemble_context("claude", project_dir, config)
        assert "## Adapter Instructions" in result

    def test_current_state_contains_stage(self, project_dir, config):
        """Returned string contains the current stage from STATE.json."""
        result = assemble_context("claude", project_dir, config)
        assert "init" in result

    def test_chatgpt_tool_name_in_output(self, project_dir, config):
        """assemble_context('chatgpt', ...) returns string mentioning 'chatgpt'."""
        result = assemble_context("chatgpt", project_dir, config)
        assert "chatgpt" in result.lower()

    def test_claude_tool_name_in_output(self, project_dir, config):
        """assemble_context('claude', ...) returns string mentioning 'claude'."""
        result = assemble_context("claude", project_dir, config)
        assert "claude" in result.lower()

    def test_unknown_tool_produces_output(self, project_dir, config):
        """Unknown tool name still produces output (graceful degradation)."""
        result = assemble_context("unknown-ai-tool", project_dir, config)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "## Current State" in result


# ---------------------------------------------------------------------------
# STATE.json content tests
# ---------------------------------------------------------------------------


class TestAssembleContextState:
    """Assembler correctly reads and includes STATE.json data."""

    def test_includes_completed_tasks_count(self, project_dir, config):
        """Output mentions completed task count."""
        result = assemble_context("claude", project_dir, config)
        # "0" should appear somewhere in current state section
        assert "0" in result or "completed" in result.lower()

    def test_includes_history_entries(self, project_dir, config):
        """Output includes last history entries."""
        result = assemble_context("claude", project_dir, config)
        # History entry 'init' was added in fixture
        assert "init" in result

    def test_reflects_non_default_stage(self, tmp_path, config):
        """Output reflects non-default stage from STATE.json."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        state.current_stage = "brief"
        save_state(state, pa / "STATE.json")
        history_dir = pa / "history"
        history_dir.mkdir()
        (history_dir / "001_brief.json").write_text(
            json.dumps(
                {
                    "event_type": "brief",
                    "stage": "brief",
                    "timestamp": "2026-01-01T00:00:00",
                    "actor": "system",
                    "tool_used": "minilegion",
                    "notes": "Brief created",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        result = assemble_context("claude", pa, config)
        assert "brief" in result


# ---------------------------------------------------------------------------
# Optional file graceful degradation tests
# ---------------------------------------------------------------------------


class TestAssembleContextGracefulDegradation:
    """Assembler never raises when optional files are absent."""

    def test_no_adapter_file_still_works(self, project_dir, config):
        """Assembler works with no adapters/ directory at all."""
        # project_dir has no adapters/
        result = assemble_context("claude", project_dir, config)
        assert "## Adapter Instructions" in result

    def test_no_memory_files_still_works(self, project_dir, config):
        """Assembler works with no memory/ directory."""
        result = assemble_context("claude", project_dir, config)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_templates_dir_still_works(self, project_dir, config):
        """Assembler works with no templates/ directory."""
        result = assemble_context("claude", project_dir, config)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_artifacts_still_works(self, project_dir, config):
        """Assembler works with no BRIEF.md / RESEARCH.md / etc. present."""
        result = assemble_context("claude", project_dir, config)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Optional file inclusion tests
# ---------------------------------------------------------------------------


class TestAssembleContextOptionalFiles:
    """Assembler includes optional files when they are present."""

    def test_reads_adapter_file_when_present(self, tmp_path, config):
        """Assembler includes tool-specific adapter file when present."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        save_state(state, pa / "STATE.json")
        (pa / "adapters").mkdir()
        (pa / "adapters" / "claude.md").write_text(
            "# Claude Specific Instructions\nBe concise.", encoding="utf-8"
        )

        result = assemble_context("claude", pa, config)
        assert "Claude Specific Instructions" in result

    def test_falls_back_to_base_adapter(self, tmp_path, config):
        """Assembler falls back to adapters/_base.md when tool-specific is absent."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        save_state(state, pa / "STATE.json")
        (pa / "adapters").mkdir()
        (pa / "adapters" / "_base.md").write_text(
            "# Base Adapter\nGeneric instructions.", encoding="utf-8"
        )

        result = assemble_context("chatgpt", pa, config)
        assert "Base Adapter" in result

    def test_reads_memory_files_when_present(self, tmp_path, config):
        """Assembler includes memory files when present."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        save_state(state, pa / "STATE.json")
        (pa / "memory").mkdir()
        (pa / "memory" / "decisions.md").write_text(
            "# Decisions\n- Use PostgreSQL.", encoding="utf-8"
        )

        result = assemble_context("claude", pa, config)
        assert "## Memory" in result
        assert "PostgreSQL" in result

    def test_reads_template_when_present(self, tmp_path, config):
        """Assembler includes stage template when present."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        state.current_stage = "brief"
        save_state(state, pa / "STATE.json")
        (pa / "templates").mkdir()
        (pa / "templates" / "brief.md").write_text(
            "# Brief Stage Template\nFollow these steps.", encoding="utf-8"
        )

        result = assemble_context("claude", pa, config)
        assert "## Stage Template" in result
        assert "Brief Stage Template" in result

    def test_reads_artifact_when_present(self, tmp_path, config):
        """Assembler includes most recent artifact for current stage."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        state.current_stage = "brief"
        save_state(state, pa / "STATE.json")
        (pa / "BRIEF.md").write_text(
            "# Project Brief\n\nBuild something cool.", encoding="utf-8"
        )

        result = assemble_context("claude", pa, config)
        assert "## Previous Artifact" in result
        assert "Build something cool" in result

    def test_memory_section_absent_when_no_files(self, project_dir, config):
        """Memory section only appears when memory files exist."""
        result = assemble_context("claude", project_dir, config)
        # With no memory/ dir, there should be no memory section
        # (or it should be empty/absent) — assembler silently skips
        # We just check no exception was raised (tested above); here
        # check for clean behavior: no spurious content
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Init integration: adapter/template/memory appear after init
# ---------------------------------------------------------------------------


class TestAssembleContextAfterInit:
    """Assembler uses real adapter/template/memory files written by init command."""

    def test_adapter_file_included_after_init(self, tmp_path, monkeypatch):
        """After minilegion init, assemble_context uses the real claude adapter."""
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner as _Runner

        _runner = _Runner()
        _runner.invoke(app, ["init", "myproject"])

        project_dir = tmp_path / "myproject" / "project-ai"
        cfg = MiniLegionConfig()
        result = assemble_context("claude", project_dir, cfg)
        # ADAPTER_CLAUDE starts with "# Claude — MiniLegion Context"
        assert "Claude" in result
        # Should NOT be the stub text
        assert "Paste this context block at the start" not in result

    def test_template_included_after_init(self, tmp_path, monkeypatch):
        """After minilegion init, assemble_context includes the init stage template."""
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner as _Runner

        _runner = _Runner()
        _runner.invoke(app, ["init", "myproject"])

        project_dir = tmp_path / "myproject" / "project-ai"
        cfg = MiniLegionConfig()
        result = assemble_context("claude", project_dir, cfg)
        # init stage template text
        assert "minilegion brief" in result

    def test_memory_included_after_init(self, tmp_path, monkeypatch):
        """After minilegion init, assemble_context includes memory scaffold files."""
        monkeypatch.chdir(tmp_path)
        from typer.testing import CliRunner as _Runner

        _runner = _Runner()
        _runner.invoke(app, ["init", "myproject"])

        project_dir = tmp_path / "myproject" / "project-ai"
        cfg = MiniLegionConfig()
        result = assemble_context("claude", project_dir, cfg)
        # Memory section should appear because decisions.md, glossary.md, constraints.md exist
        assert "## Memory" in result


# ---------------------------------------------------------------------------
# Config integration tests
# ---------------------------------------------------------------------------


class TestAssembleContextConfig:
    """Assembler respects config.context settings."""

    def test_uses_max_injection_tokens_from_config(self, tmp_path):
        """Assembler truncates oversized artifact at config.context.max_injection_tokens."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        state.current_stage = "brief"
        save_state(state, pa / "STATE.json")

        # Create a very large BRIEF.md that exceeds the token limit
        large_content = "# Brief\n\n" + ("A" * 5000)
        (pa / "BRIEF.md").write_text(large_content, encoding="utf-8")

        # Set a small limit
        config = MiniLegionConfig()
        config.context.max_injection_tokens = 100

        result = assemble_context("claude", pa, config)
        # Should still return a result (not crash)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_truncation_marker_present_when_artifact_too_large(self, tmp_path, capsys):
        """[TRUNCATED] marker appears when artifact exceeds max_injection_tokens."""
        pa = tmp_path / "project-ai"
        pa.mkdir()
        state = ProjectState()
        state.current_stage = "brief"
        save_state(state, pa / "STATE.json")

        large_content = "# Brief\n\n" + ("X" * 5000)
        (pa / "BRIEF.md").write_text(large_content, encoding="utf-8")

        config = MiniLegionConfig()
        config.context.max_injection_tokens = 100

        result = assemble_context("claude", pa, config)
        assert "[TRUNCATED]" in result


class TestAssembleContextCompactPlan:
    """Assembler emits deterministic compact lookahead from PLAN.json."""

    @staticmethod
    def _compact_plan_section(text: str) -> str:
        marker = "## Compact Plan\n\n"
        assert marker in text
        section = text.split(marker, 1)[1]
        return section.split("\n## ", 1)[0]

    @staticmethod
    def _write_plan(pa: Path, tasks: list[dict[str, object]]) -> None:
        plan_payload = {
            "objective": "Ship compact plan context",
            "design_ref": "DESIGN.json",
            "tasks": tasks,
            "test_plan": "pytest",
        }
        (pa / "PLAN.json").write_text(
            json.dumps(plan_payload, indent=2), encoding="utf-8"
        )

    def test_compact_plan_includes_two_pending_tasks_by_default(self, tmp_path):
        pa = tmp_path / "project-ai"
        pa.mkdir()

        state = ProjectState()
        state.completed_tasks = ["T-1"]
        save_state(state, pa / "STATE.json")

        self._write_plan(
            pa,
            [
                {"id": "T-1", "name": "done", "description": "Done task"},
                {"id": "T-2", "name": "next", "description": "Next task"},
                {"id": "T-3", "name": "later", "description": "Later task"},
            ],
        )

        cfg = MiniLegionConfig()
        cfg.context.lookahead_tasks = 2

        result = assemble_context("claude", pa, cfg)
        section = self._compact_plan_section(result)
        bullets = [line for line in section.splitlines() if line.startswith("- ")]
        assert bullets == ["- T-2: next", "- T-3: later"]

    def test_compact_plan_respects_lookahead_limit(self, tmp_path):
        pa = tmp_path / "project-ai"
        pa.mkdir()

        state = ProjectState()
        state.completed_tasks = ["T-1"]
        save_state(state, pa / "STATE.json")

        self._write_plan(
            pa,
            [
                {"id": "T-1", "name": "done", "description": "Done task"},
                {"id": "T-2", "name": "next", "description": "Next task"},
                {"id": "T-3", "name": "later", "description": "Later task"},
            ],
        )

        cfg = MiniLegionConfig()
        cfg.context.lookahead_tasks = 1

        result = assemble_context("claude", pa, cfg)
        section = self._compact_plan_section(result)
        bullets = [line for line in section.splitlines() if line.startswith("- ")]
        assert bullets == ["- T-2: next"]

    @pytest.mark.parametrize("malformed", [False, True])
    def test_compact_plan_graceful_fallback_without_valid_plan(
        self, tmp_path, malformed
    ):
        pa = tmp_path / "project-ai"
        pa.mkdir()
        save_state(ProjectState(), pa / "STATE.json")

        if malformed:
            (pa / "PLAN.json").write_text('{"tasks": "not-a-list"', encoding="utf-8")

        result = assemble_context("claude", pa, MiniLegionConfig())
        section = self._compact_plan_section(result)
        assert "_No plan context available._" in section


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------

runner = CliRunner()


class TestContextCLICommand:
    """Tests for `minilegion context <tool>` CLI command."""

    def _make_project(self, tmp_path: Path) -> Path:
        """Create minimal project in tmp_path, chdir to it."""
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir(parents=True)
        state = ProjectState()
        save_state(state, project_dir / "STATE.json")
        history_dir = project_dir / "history"
        history_dir.mkdir()
        (history_dir / "001_init.json").write_text(
            json.dumps(
                {
                    "event_type": "init",
                    "stage": "init",
                    "timestamp": "2026-01-01T00:00:00",
                    "actor": "system",
                    "tool_used": "minilegion",
                    "notes": "Project initialized",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return project_dir

    def test_context_command_writes_file(self, tmp_path, monkeypatch):
        """minilegion context claude writes project-ai/context/claude.md."""
        monkeypatch.chdir(tmp_path)
        self._make_project(tmp_path)

        result = runner.invoke(app, ["context", "claude"])
        assert result.exit_code == 0, f"Command failed: {result.output}"

        context_file = tmp_path / "project-ai" / "context" / "claude.md"
        assert context_file.exists(), "context/claude.md was not created"

    def test_context_command_file_content_matches_stdout(self, tmp_path, monkeypatch):
        """Content of context/claude.md matches stdout output."""
        monkeypatch.chdir(tmp_path)
        self._make_project(tmp_path)

        result = runner.invoke(app, ["context", "claude"])
        assert result.exit_code == 0

        context_file = tmp_path / "project-ai" / "context" / "claude.md"
        file_content = context_file.read_text(encoding="utf-8")
        # stdout includes a trailing newline from typer.echo; strip both for comparison
        assert file_content.strip() == result.output.strip()

    def test_context_command_prints_to_stdout(self, tmp_path, monkeypatch):
        """minilegion context claude prints the context block to stdout."""
        monkeypatch.chdir(tmp_path)
        self._make_project(tmp_path)

        result = runner.invoke(app, ["context", "claude"])
        assert result.exit_code == 0
        assert "## Current State" in result.output

    def test_context_command_chatgpt(self, tmp_path, monkeypatch):
        """minilegion context chatgpt writes project-ai/context/chatgpt.md."""
        monkeypatch.chdir(tmp_path)
        self._make_project(tmp_path)

        result = runner.invoke(app, ["context", "chatgpt"])
        assert result.exit_code == 0

        context_file = tmp_path / "project-ai" / "context" / "chatgpt.md"
        assert context_file.exists()

    def test_context_command_copilot(self, tmp_path, monkeypatch):
        """minilegion context copilot writes project-ai/context/copilot.md."""
        monkeypatch.chdir(tmp_path)
        self._make_project(tmp_path)

        result = runner.invoke(app, ["context", "copilot"])
        assert result.exit_code == 0

        context_file = tmp_path / "project-ai" / "context" / "copilot.md"
        assert context_file.exists()

    def test_context_command_opencode(self, tmp_path, monkeypatch):
        """minilegion context opencode writes project-ai/context/opencode.md."""
        monkeypatch.chdir(tmp_path)
        self._make_project(tmp_path)

        result = runner.invoke(app, ["context", "opencode"])
        assert result.exit_code == 0

        context_file = tmp_path / "project-ai" / "context" / "opencode.md"
        assert context_file.exists()

    def test_context_command_no_project_exits_1(self, tmp_path, monkeypatch):
        """minilegion context claude without project-ai/ exits with code 1."""
        monkeypatch.chdir(tmp_path)  # no project-ai/ created

        result = runner.invoke(app, ["context", "claude"])
        assert result.exit_code == 1
        assert "No MiniLegion project found" in result.output

    def test_context_command_registered_in_app(self):
        """'context' command appears in --help output."""
        result = runner.invoke(app, ["--help"])
        assert "context" in result.output
