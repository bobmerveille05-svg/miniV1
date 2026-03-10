"""Tests for MiniLegion approval gates.

Covers all 5 approval gates (brief, research, design, plan, patch)
and byte-identical rejection guarantee (APRV-06).
"""

import pytest

from minilegion.core.approval import (
    approve,
    approve_brief,
    approve_design,
    approve_patch,
    approve_plan,
    approve_research,
)
from minilegion.core.exceptions import ApprovalError
from minilegion.core.state import ProjectState, load_state, save_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(tmp_path):
    """Create a fresh ProjectState, save it, return (state, path)."""
    state = ProjectState()
    state_path = tmp_path / "STATE.json"
    save_state(state, state_path)
    return state, state_path


# ---------------------------------------------------------------------------
# TestApproveBrief  (APRV-01)
# ---------------------------------------------------------------------------


class TestApproveBrief:
    """approve_brief() displays summary and prompts Y/N."""

    def test_approve_brief_accepted(self, tmp_path, monkeypatch):
        """Accepting brief sets brief_approved=True and persists."""
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)

        result = approve_brief(state, state_path, "Brief content here")

        assert result is True
        assert state.approvals["brief_approved"] is True
        # Verify persisted to disk
        reloaded = load_state(state_path)
        assert reloaded.approvals["brief_approved"] is True

    def test_approve_brief_rejected(self, tmp_path, monkeypatch):
        """Rejecting brief raises ApprovalError; STATE.json is byte-identical."""
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        bytes_before = state_path.read_bytes()

        with pytest.raises(ApprovalError):
            approve_brief(state, state_path, "Brief content here")

        bytes_after = state_path.read_bytes()
        assert bytes_before == bytes_after


# ---------------------------------------------------------------------------
# TestApproveResearch  (APRV-02)
# ---------------------------------------------------------------------------


class TestApproveResearch:
    """approve_research() displays summary and prompts Y/N."""

    def test_approve_research_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)

        result = approve_research(state, state_path, "Research summary")

        assert result is True
        assert state.approvals["research_approved"] is True
        reloaded = load_state(state_path)
        assert reloaded.approvals["research_approved"] is True

    def test_approve_research_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        bytes_before = state_path.read_bytes()

        with pytest.raises(ApprovalError):
            approve_research(state, state_path, "Research summary")

        bytes_after = state_path.read_bytes()
        assert bytes_before == bytes_after


# ---------------------------------------------------------------------------
# TestApproveDesign  (APRV-03)
# ---------------------------------------------------------------------------


class TestApproveDesign:
    """approve_design() displays summary and prompts Y/N."""

    def test_approve_design_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)

        result = approve_design(state, state_path, "Design summary")

        assert result is True
        assert state.approvals["design_approved"] is True
        reloaded = load_state(state_path)
        assert reloaded.approvals["design_approved"] is True

    def test_approve_design_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        bytes_before = state_path.read_bytes()

        with pytest.raises(ApprovalError):
            approve_design(state, state_path, "Design summary")

        bytes_after = state_path.read_bytes()
        assert bytes_before == bytes_after


# ---------------------------------------------------------------------------
# TestApprovePlan  (APRV-04)
# ---------------------------------------------------------------------------


class TestApprovePlan:
    """approve_plan() displays summary and prompts Y/N."""

    def test_approve_plan_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)

        result = approve_plan(state, state_path, "Plan summary")

        assert result is True
        assert state.approvals["plan_approved"] is True
        reloaded = load_state(state_path)
        assert reloaded.approvals["plan_approved"] is True

    def test_approve_plan_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        bytes_before = state_path.read_bytes()

        with pytest.raises(ApprovalError):
            approve_plan(state, state_path, "Plan summary")

        bytes_after = state_path.read_bytes()
        assert bytes_before == bytes_after


# ---------------------------------------------------------------------------
# TestApprovePatch  (APRV-05)
# ---------------------------------------------------------------------------


class TestApprovePatch:
    """approve_patch() displays diff and prompts Y/N."""

    def test_approve_patch_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)

        result = approve_patch(state, state_path, "diff --git a/f.py")

        assert result is True
        assert state.approvals["execute_approved"] is True
        reloaded = load_state(state_path)
        assert reloaded.approvals["execute_approved"] is True

    def test_approve_patch_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        bytes_before = state_path.read_bytes()

        with pytest.raises(ApprovalError):
            approve_patch(state, state_path, "diff --git a/f.py")

        bytes_after = state_path.read_bytes()
        assert bytes_before == bytes_after


# ---------------------------------------------------------------------------
# TestRejectionByteIdentical  (APRV-06 — cross-cutting)
# ---------------------------------------------------------------------------


class TestRejectionByteIdentical:
    """Rejection across ALL gates must leave STATE.json byte-identical."""

    @pytest.mark.parametrize(
        "gate_fn,content",
        [
            (approve_brief, "brief text"),
            (approve_research, "research text"),
            (approve_design, "design text"),
            (approve_plan, "plan text"),
            (approve_patch, "patch text"),
        ],
    )
    def test_rejection_state_file_byte_identical(
        self, tmp_path, monkeypatch, gate_fn, content
    ):
        """STATE.json bytes are identical before and after rejection."""
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        bytes_before = state_path.read_bytes()

        with pytest.raises(ApprovalError):
            gate_fn(state, state_path, content)

        bytes_after = state_path.read_bytes()
        assert bytes_before == bytes_after

    @pytest.mark.parametrize(
        "gate_fn,content,key",
        [
            (approve_brief, "brief text", "brief_approved"),
            (approve_research, "research text", "research_approved"),
            (approve_design, "design text", "design_approved"),
            (approve_plan, "plan text", "plan_approved"),
            (approve_patch, "patch text", "execute_approved"),
        ],
    )
    def test_rejection_does_not_modify_state_object(
        self, tmp_path, monkeypatch, gate_fn, content, key
    ):
        """After rejection, state.approvals dict is unchanged from initial values."""
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)
        approvals_before = dict(state.approvals)

        with pytest.raises(ApprovalError):
            gate_fn(state, state_path, content)

        assert state.approvals == approvals_before
        assert state.approvals[key] is False


# ---------------------------------------------------------------------------
# TestApprovalHistory  (history tracking)
# ---------------------------------------------------------------------------


class TestApprovalHistory:
    """Approved gates add a history entry."""

    @pytest.mark.parametrize(
        "gate_fn,content,gate_name",
        [
            (approve_brief, "brief text", "brief_approved"),
            (approve_research, "research text", "research_approved"),
            (approve_design, "design text", "design_approved"),
            (approve_plan, "plan text", "plan_approved"),
            (approve_patch, "patch text", "execute_approved"),
        ],
    )
    def test_approval_adds_history_entry(
        self, tmp_path, monkeypatch, gate_fn, content, gate_name
    ):
        """After approval, state.history has new entry with action='approval'."""
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)
        history_len_before = len(state.history)

        gate_fn(state, state_path, content)

        assert len(state.history) == history_len_before + 1
        latest = state.history[-1]
        assert latest.action == "approval"
        assert gate_name in latest.details


# ---------------------------------------------------------------------------
# TestCoreApproveFunction  (direct approve() tests)
# ---------------------------------------------------------------------------


class TestCoreApproveFunction:
    """Direct tests for the core approve() function."""

    def test_approve_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: True
        )
        state, state_path = _make_state(tmp_path)

        result = approve("brief_approved", "Summary text", state, state_path)

        assert result is True
        assert state.approvals["brief_approved"] is True

    def test_approve_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)

        with pytest.raises(ApprovalError, match="Rejected: brief_approved"):
            approve("brief_approved", "Summary text", state, state_path)

    def test_approve_rejection_message_contains_gate_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "minilegion.core.approval.typer.confirm", lambda *a, **kw: False
        )
        state, state_path = _make_state(tmp_path)

        with pytest.raises(ApprovalError, match="design_approved"):
            approve("design_approved", "Summary text", state, state_path)
