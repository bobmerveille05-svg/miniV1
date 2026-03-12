"""State machine and project state management for MiniLegion.

Manages the 8-stage pipeline: init -> brief -> research -> design ->
plan -> execute -> review -> archive.

Transitions are linear-with-backtrack: forward by one step only, but
backward to any previous stage is always allowed. Backtracking clears
downstream approvals.
"""

from datetime import datetime
from enum import Enum
import json
from pathlib import Path

from pydantic import BaseModel, Field

from minilegion.core.exceptions import InvalidTransitionError
from minilegion.core.file_io import write_atomic
from minilegion.core.history import HistoryEvent, append_event


class Stage(str, Enum):
    """Pipeline stages in order."""

    INIT = "init"
    BRIEF = "brief"
    RESEARCH = "research"
    DESIGN = "design"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    ARCHIVE = "archive"


STAGE_ORDER: list[Stage] = list(Stage)

# Valid forward transitions: each stage can only advance to the next one
FORWARD_TRANSITIONS: dict[Stage, Stage] = {
    Stage.INIT: Stage.BRIEF,
    Stage.BRIEF: Stage.RESEARCH,
    Stage.RESEARCH: Stage.DESIGN,
    Stage.DESIGN: Stage.PLAN,
    Stage.PLAN: Stage.EXECUTE,
    Stage.EXECUTE: Stage.REVIEW,
    Stage.REVIEW: Stage.ARCHIVE,
}

APPROVAL_KEYS: list[str] = [
    "brief_approved",
    "research_approved",
    "design_approved",
    "plan_approved",
    "execute_approved",
    "review_approved",
]


class HistoryEntry(BaseModel):
    """A single history log entry."""

    timestamp: str
    action: str
    details: str = ""


class ProjectState(BaseModel):
    """STATE.json schema — the single source of truth for project state."""

    current_stage: str = "init"
    approvals: dict[str, bool] = Field(
        default_factory=lambda: {
            "brief_approved": False,
            "research_approved": False,
            "design_approved": False,
            "plan_approved": False,
            "execute_approved": False,
            "review_approved": False,
        }
    )
    completed_tasks: list[str] = Field(default_factory=list)
    history: list[HistoryEntry] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    def add_history(self, action: str, details: str = "") -> None:
        """Add a history entry with the current timestamp."""
        self.history.append(
            HistoryEntry(
                timestamp=datetime.now().isoformat(),
                action=action,
                details=details,
            )
        )


class StateMachine:
    """Manages stage transitions with validation and approval clearing.

    Supports:
    - Forward by one step (init -> brief, brief -> research, etc.)
    - Backward to any previous stage
    - Rejects forward skips (init -> design) and same-stage transitions
    - Clears downstream approvals on backtrack
    """

    def __init__(self, current_stage: Stage, approvals: dict[str, bool] | None = None):
        if isinstance(current_stage, str):
            current_stage = Stage(current_stage)
        self.current_stage = current_stage
        self.approvals = (
            approvals
            if approvals is not None
            else {key: False for key in APPROVAL_KEYS}
        )

    def can_transition(self, target: Stage) -> bool:
        """Check if transition is valid (forward by one, or backward).

        Does NOT modify any state — purely a check.
        """
        if isinstance(target, str):
            target = Stage(target)

        current_idx = STAGE_ORDER.index(self.current_stage)
        target_idx = STAGE_ORDER.index(target)

        if target_idx == current_idx + 1:
            return True  # Forward by one step
        if target_idx < current_idx:
            return True  # Backward (any previous stage)
        return False

    def transition(self, target: Stage) -> None:
        """Transition to target stage.

        On backtrack, clears downstream approvals (target stage and beyond).

        Raises:
            InvalidTransitionError: If the transition is not valid.
        """
        if isinstance(target, str):
            target = Stage(target)

        if not self.can_transition(target):
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_stage.value} to {target.value}"
            )

        target_idx = STAGE_ORDER.index(target)
        current_idx = STAGE_ORDER.index(self.current_stage)

        # Clear downstream approvals on backtrack
        if target_idx < current_idx:
            for key in APPROVAL_KEYS:
                stage_name = key.replace("_approved", "")
                try:
                    stage = Stage(stage_name)
                except ValueError:
                    continue
                if STAGE_ORDER.index(stage) >= target_idx:
                    self.approvals[key] = False

        self.current_stage = target


def save_state(state: ProjectState, path: Path) -> None:
    """Save project state to a JSON file atomically.

    Args:
        state: The ProjectState to serialize.
        path: File path to write to.
    """
    payload = state.model_dump(exclude={"history"})
    write_atomic(path, json.dumps(payload, indent=2))


def load_state(path: Path) -> ProjectState:
    """Load project state from a JSON file.

    Args:
        path: File path to read from.

    Returns:
        Validated ProjectState.
    """
    state_path = Path(path)
    raw = state_path.read_text(encoding="utf-8")
    raw_data = json.loads(raw)

    if isinstance(raw_data, dict) and isinstance(raw_data.get("history"), list):
        project_dir = state_path.parent
        stage = str(raw_data.get("current_stage", "init"))
        for entry in raw_data["history"]:
            if not isinstance(entry, dict):
                continue
            append_event(
                project_dir,
                HistoryEvent(
                    event_type=str(entry.get("action", "legacy")),
                    stage=stage,
                    timestamp=str(entry.get("timestamp", datetime.now().isoformat())),
                    actor="system",
                    tool_used="minilegion",
                    notes=str(entry.get("details", "")),
                ),
            )
        raw_data.pop("history", None)
        write_atomic(state_path, json.dumps(raw_data, indent=2))

    return ProjectState.model_validate(raw_data)
