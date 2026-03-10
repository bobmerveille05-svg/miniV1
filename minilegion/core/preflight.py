"""Pre-flight validation checks for MiniLegion pipeline stages.

Enforces two categories of prerequisites before any LLM call:
1. GUARD-01: Required files must exist in the project directory
2. GUARD-02: Required approvals must be True in STATE.json

Each stage has a declarative mapping of what files and approvals it
requires. check_preflight() fails fast on the first missing prerequisite.

Fast mode (FAST-01, FAST-02, FAST-03): pass skip_stages to bypass file
and approval requirements for stages that were explicitly skipped.
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
    Stage.ARCHIVE: ["REVIEW.json", "PLAN.json", "EXECUTION_LOG.json", "DESIGN.json"],
}

# GUARD-02: Declarative approval requirements per stage.
# Stages not listed (INIT, BRIEF) have no approval requirements.
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
    Stage.ARCHIVE: ["review_approved"],
}

# FAST-03: Artifacts and approvals produced by each skippable stage.
# Used to filter requirements when stages are explicitly bypassed.
STAGE_ARTIFACTS: dict[str, list[str]] = {
    "research": ["RESEARCH.json", "RESEARCH.md"],
    "design": ["DESIGN.json", "DESIGN.md"],
}

STAGE_APPROVALS: dict[str, list[str]] = {
    "research": ["research_approved"],
    "design": ["design_approved"],
}


def check_preflight(
    stage: Stage | str,
    project_dir: Path,
    skip_stages: set[str] | None = None,
) -> None:
    """Validate that all prerequisites are met before entering a stage.

    Checks required files and approvals in order, failing fast on the
    first missing prerequisite.

    Args:
        stage: The pipeline stage to validate prerequisites for.
            Accepts both Stage enum and string values.
        project_dir: Path to the project directory containing artifacts
            and STATE.json.
        skip_stages: Optional set of stage names (e.g. {"research", "design"})
            whose file and approval requirements should be bypassed. Used
            for fast mode (FAST-01, FAST-02, FAST-03).

    Raises:
        PreflightError: If a required file is missing or a required
            approval is False/missing.
    """
    # Coerce string to Stage enum
    if isinstance(stage, str):
        stage = Stage(stage)

    project_dir = Path(project_dir)

    # Build sets of skippable filenames and approval keys (FAST-03)
    skipped_files: set[str] = set()
    skipped_approvals: set[str] = set()
    if skip_stages:
        for s in skip_stages:
            skipped_files.update(STAGE_ARTIFACTS.get(s, []))
            skipped_approvals.update(STAGE_APPROVALS.get(s, []))

    # Check required files (GUARD-01)
    for filename in REQUIRED_FILES.get(stage, []):
        if filename in skipped_files:
            continue  # Stage was explicitly skipped — artifact not required
        if not (project_dir / filename).exists():
            raise PreflightError(f"Missing required file: {filename}")

    # Check required approvals (GUARD-02)
    required_approvals = REQUIRED_APPROVALS.get(stage, [])
    if required_approvals:
        state = load_state(project_dir / "STATE.json")
        for approval_key in required_approvals:
            if approval_key in skipped_approvals:
                continue  # Stage was explicitly skipped — approval not required
            if not state.approvals.get(approval_key, False):
                raise PreflightError(f"Missing required approval: {approval_key}")
