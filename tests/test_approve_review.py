"""Tests for approve_review approval gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from minilegion.core.approval import approve_review
from minilegion.core.exceptions import ApprovalError
from minilegion.core.state import ProjectState, load_state


def _make_execute_state(tmp_path: Path) -> tuple[ProjectState, Path]:
    """Create a ProjectState at execute stage (all 5 approvals True) and STATE.json."""
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
    state_path = tmp_path / "STATE.json"
    state_path.write_text(json.dumps(state_data), encoding="utf-8")
    return ProjectState(**state_data), state_path


class TestApproveReview:
    def test_approve_review_sets_review_approved(self, monkeypatch, tmp_path):
        """Accepting the gate sets review_approved=True in STATE.json."""
        state, state_path = _make_execute_state(tmp_path)
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )

        approve_review(state, state_path, "Review summary")

        saved = load_state(state_path)
        assert saved.approvals["review_approved"] is True

    def test_approve_review_raises_on_rejection(self, monkeypatch, tmp_path):
        """Rejecting the gate raises ApprovalError."""
        state, state_path = _make_execute_state(tmp_path)
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )

        with pytest.raises(ApprovalError):
            approve_review(state, state_path, "Review summary")

    def test_approve_review_leaves_state_unchanged_on_rejection(
        self, monkeypatch, tmp_path
    ):
        """Rejecting the gate does NOT modify STATE.json."""
        state, state_path = _make_execute_state(tmp_path)
        original_content = state_path.read_text(encoding="utf-8")
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )

        try:
            approve_review(state, state_path, "Review summary")
        except ApprovalError:
            pass

        assert state_path.read_text(encoding="utf-8") == original_content
