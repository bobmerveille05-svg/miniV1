"""Tests for brief and research CLI commands (Phase 6)."""

import json

import pytest
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


class TestBriefCommand:
    def test_brief_creates_brief_md_with_text_arg(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_content_contains_overview_heading(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_writes_atomically_before_approval(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_stdin_input(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_stdin_empty_creates_empty_overview(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_approval_accepted_transitions_state(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_rejection_leaves_state_json_unchanged(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_rejection_exits_0(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_without_project_dir_exits_1(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")

    def test_brief_from_wrong_stage_exits_1(self, tmp_path, monkeypatch):
        pytest.fail("not implemented")
