"""Pre-flight validation checks for MiniLegion pipeline stages.

Enforces two categories of prerequisites before any LLM call:
1. GUARD-01: Required files must exist in the project directory
2. GUARD-02: Required approvals must be True in STATE.json

Each stage has a declarative mapping of what files and approvals it
requires. check_preflight() fails fast on the first missing prerequisite.
"""

from pathlib import Path

from minilegion.core.exceptions import PreflightError
from minilegion.core.state import Stage, load_state

# GUARD-01: Declarative file requirements per stage.
# Stages not listed (INIT, BRIEF, ARCHIVE) have no file requirements.
REQUIRED_FILES: dict[Stage, list[str]] = {
    Stage.RESEARCH: ["BRIEF.md"],
    Stage.DESIGN: ["BRIEF.md", "RESEARCH.json"],
    Stage.PLAN: ["BRIEF.md", "RESEARCH.json", "DESIGN.json"],
    Stage.EXECUTE: ["BRIEF.md", "RESEARCH.json", "DESIGN.json", "PLAN.json"],
    Stage.REVIEW: [
        "BRIEF.md",
        "RESEARCH.json",
        "DESIGN.json",
        "PLAN.json",
        "EXECUTION_LOG.json",
    ],
}

# GUARD-02: Declarative approval requirements per stage.
# Stages not listed (INIT, BRIEF, ARCHIVE) have no approval requirements.
REQUIRED_APPROVALS: dict[Stage, list[str]] = {
    Stage.RESEARCH: ["brief_approved"],
    Stage.DESIGN: ["brief_approved", "research_approved"],
    Stage.PLAN: ["brief_approved", "research_approved", "design_approved"],
    Stage.EXECUTE: [
        "brief_approved",
        "research_approved",
        "design_approved",
        "plan_approved",
    ],
    Stage.REVIEW: [
        "brief_approved",
        "research_approved",
        "design_approved",
        "plan_approved",
        "execute_approved",
    ],
}


def check_preflight(stage: Stage | str, project_dir: Path) -> None:
    """Validate that all prerequisites are met before entering a stage.

    Checks required files and approvals in order, failing fast on the
    first missing prerequisite.

    Args:
        stage: The pipeline stage to validate prerequisites for.
            Accepts both Stage enum and string values.
        project_dir: Path to the project directory containing artifacts
            and STATE.json.

    Raises:
        PreflightError: If a required file is missing or a required
            approval is False/missing.
    """
    # Coerce string to Stage enum
    if isinstance(stage, str):
        stage = Stage(stage)

    project_dir = Path(project_dir)

    # Check required files (GUARD-01)
    for filename in REQUIRED_FILES.get(stage, []):
        if not (project_dir / filename).exists():
            raise PreflightError(f"Missing required file: {filename}")

    # Check required approvals (GUARD-02)
    required_approvals = REQUIRED_APPROVALS.get(stage, [])
    if required_approvals:
        state = load_state(project_dir / "STATE.json")
        for approval_key in required_approvals:
            if not state.approvals.get(approval_key, False):
                raise PreflightError(f"Missing required approval: {approval_key}")
