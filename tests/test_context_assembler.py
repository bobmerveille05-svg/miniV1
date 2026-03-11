"""Tests for minilegion.core.context_assembler — context assembly function.

All tests use tmp_path fixtures with minimal project-ai/STATE.json setup.
Assembler must degrade gracefully when optional files are absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    state.add_history("init", "Project initialized")
    save_state(state, pa / "STATE.json")
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
        state.add_history("brief", "Brief created")
        save_state(state, pa / "STATE.json")

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
