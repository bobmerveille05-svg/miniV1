"""Tests for minilegion.core.state — state machine and project state."""

import pytest

from minilegion.core.exceptions import InvalidTransitionError
from minilegion.core.state import (
    APPROVAL_KEYS,
    FORWARD_TRANSITIONS,
    STAGE_ORDER,
    ProjectState,
    Stage,
    StateMachine,
    load_state,
    save_state,
)


# All 7 valid forward transitions
FORWARD_PAIRS = [
    (Stage.INIT, Stage.BRIEF),
    (Stage.BRIEF, Stage.RESEARCH),
    (Stage.RESEARCH, Stage.DESIGN),
    (Stage.DESIGN, Stage.PLAN),
    (Stage.PLAN, Stage.EXECUTE),
    (Stage.EXECUTE, Stage.REVIEW),
    (Stage.REVIEW, Stage.ARCHIVE),
]


class TestStateMachineTransitions:
    """Test state machine transition validation."""

    @pytest.mark.parametrize("source,target", FORWARD_PAIRS)
    def test_all_forward_transitions_valid(self, source, target, default_approvals):
        """All 7 forward-by-one transitions are valid."""
        sm = StateMachine(source, default_approvals.copy())
        assert sm.can_transition(target) is True

    def test_forward_skip_init_to_design_rejected(self, default_approvals):
        """Forward skip (init -> design) is rejected."""
        sm = StateMachine(Stage.INIT, default_approvals.copy())
        assert sm.can_transition(Stage.DESIGN) is False

    def test_forward_skip_init_to_archive_rejected(self, default_approvals):
        """Forward skip (init -> archive) is rejected."""
        sm = StateMachine(Stage.INIT, default_approvals.copy())
        assert sm.can_transition(Stage.ARCHIVE) is False

    def test_same_stage_rejected(self, default_approvals):
        """Same-stage transition (init -> init) is invalid."""
        sm = StateMachine(Stage.INIT, default_approvals.copy())
        assert sm.can_transition(Stage.INIT) is False

    def test_backward_transition_valid(self, default_approvals):
        """Backward transition (design -> research) is allowed."""
        sm = StateMachine(Stage.DESIGN, default_approvals.copy())
        assert sm.can_transition(Stage.RESEARCH) is True

    def test_backward_transition_archive_to_init(self, default_approvals):
        """Backward transition (archive -> init) is valid."""
        sm = StateMachine(Stage.ARCHIVE, default_approvals.copy())
        assert sm.can_transition(Stage.INIT) is True

    def test_invalid_transition_raises_error(self, default_approvals):
        """Invalid transition raises InvalidTransitionError."""
        sm = StateMachine(Stage.INIT, default_approvals.copy())
        with pytest.raises(InvalidTransitionError, match="Cannot transition"):
            sm.transition(Stage.DESIGN)


class TestStateMachineApprovals:
    """Test approval clearing on backtrack."""

    def test_backtrack_clears_downstream_approvals(self, all_approved):
        """Backtracking from design to research clears research_approved through review_approved."""
        sm = StateMachine(Stage.DESIGN, all_approved.copy())
        sm.transition(Stage.RESEARCH)

        # research_approved and everything downstream should be False
        assert sm.approvals["research_approved"] is False
        assert sm.approvals["design_approved"] is False
        assert sm.approvals["plan_approved"] is False
        assert sm.approvals["execute_approved"] is False
        assert sm.approvals["review_approved"] is False

        # brief_approved should remain True (upstream of target)
        assert sm.approvals["brief_approved"] is True

    def test_forward_does_not_clear_approvals(self, all_approved):
        """Forward transition does not clear approvals."""
        sm = StateMachine(Stage.INIT, all_approved.copy())
        sm.transition(Stage.BRIEF)

        # All approvals should remain True
        for key in APPROVAL_KEYS:
            assert sm.approvals[key] is True

    def test_can_transition_no_side_effects(self, all_approved):
        """can_transition does not modify state."""
        sm = StateMachine(Stage.DESIGN, all_approved.copy())
        original_stage = sm.current_stage
        original_approvals = sm.approvals.copy()

        # Call can_transition multiple times
        sm.can_transition(Stage.RESEARCH)
        sm.can_transition(Stage.ARCHIVE)
        sm.can_transition(Stage.INIT)

        assert sm.current_stage == original_stage
        assert sm.approvals == original_approvals


class TestProjectState:
    """Test ProjectState model serialization and history."""

    def test_project_state_serialization_roundtrip(self):
        """model_dump_json + model_validate_json preserves data."""
        state = ProjectState(
            current_stage="design",
            approvals={
                "brief_approved": True,
                "research_approved": True,
                "design_approved": False,
                "plan_approved": False,
                "execute_approved": False,
                "review_approved": False,
            },
            completed_tasks=["task-1", "task-2"],
            metadata={"project_name": "test"},
        )

        json_str = state.model_dump_json(indent=2)
        restored = ProjectState.model_validate_json(json_str)

        assert restored.current_stage == state.current_stage
        assert restored.approvals == state.approvals
        assert restored.completed_tasks == state.completed_tasks
        assert restored.metadata == state.metadata

    def test_add_history(self):
        """ProjectState.add_history adds entry with timestamp."""
        state = ProjectState()
        state.add_history("init", "Project initialized")

        assert len(state.history) == 1
        assert state.history[0].action == "init"
        assert state.history[0].details == "Project initialized"
        assert state.history[0].timestamp  # Should have a timestamp

    def test_save_load_state_roundtrip(self, tmp_path):
        """save_state then load_state returns equivalent ProjectState."""
        state = ProjectState(
            current_stage="research",
            approvals={
                "brief_approved": True,
                "research_approved": False,
                "design_approved": False,
                "plan_approved": False,
                "execute_approved": False,
                "review_approved": False,
            },
            completed_tasks=["task-1"],
        )
        state.add_history("transition", "Moved to research")

        state_path = tmp_path / "STATE.json"
        save_state(state, state_path)
        loaded = load_state(state_path)

        assert loaded.current_stage == state.current_stage
        assert loaded.approvals == state.approvals
        assert loaded.completed_tasks == state.completed_tasks
        assert len(loaded.history) == len(state.history)
        assert loaded.history[0].action == "transition"
