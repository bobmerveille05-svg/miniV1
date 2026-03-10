"""Inter-phase coherence checks for MiniLegion pipeline artifacts.

Performs 5 read-only checks across artifact boundaries, returning issues
as CoherenceIssue instances. Never raises, never mutates state.

Checks:
- COHR-01 (research_design): research recommended_focus_files vs design component files
- COHR-02 (design_plan): design component names vs plan task components
- COHR-03 (plan_execute): plan touched_files vs execution_log changed_file paths
- COHR-04 (design_review): design_conformity.conforms in review
- COHR-05 (research_review): convention_violations in review
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minilegion.core.schemas import (
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    ResearchSchema,
    ReviewSchema,
)


@dataclass
class CoherenceIssue:
    """A single coherence issue found between pipeline stage artifacts."""

    check_name: str
    severity: str  # "warning" | "error"
    message: str


def _load_json(path: Path, schema_cls):
    """Load and validate a JSON artifact. Returns None on any error."""
    try:
        return schema_cls.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_research_design(
    research: ResearchSchema, design: DesignSchema
) -> list[CoherenceIssue]:
    """COHR-01: focus files from research should be present in design component files.

    Uses substring match in either direction (focus_file in cf OR cf in focus_file).
    Severity: warning.
    """
    issues: list[CoherenceIssue] = []
    all_component_files = [f for c in design.components for f in c.files]

    for focus_file in research.recommended_focus_files:
        covered = any(
            focus_file in cf or cf in focus_file for cf in all_component_files
        )
        if not covered:
            issues.append(
                CoherenceIssue(
                    check_name="research_design",
                    severity="warning",
                    message=(
                        f"Focus file '{focus_file}' from research not found in any "
                        "design component files."
                    ),
                )
            )
    return issues


def _check_design_plan(design: DesignSchema, plan: PlanSchema) -> list[CoherenceIssue]:
    """COHR-02: every design component should be referenced by at least one plan task.

    Case-insensitive component name matching.
    Severity: warning.
    """
    issues: list[CoherenceIssue] = []
    component_names = {c.name.lower() for c in design.components}
    covered = {t.component.lower() for t in plan.tasks if t.component}

    for comp_name in component_names - covered:
        issues.append(
            CoherenceIssue(
                check_name="design_plan",
                severity="warning",
                message=(
                    f"Design component '{comp_name}' has no corresponding task in plan."
                ),
            )
        )
    return issues


def _check_plan_execute(
    plan: PlanSchema, execution_log: ExecutionLogSchema
) -> list[CoherenceIssue]:
    """COHR-03: all changed files in execution log should be in plan's touched_files.

    Severity: error (out-of-scope execution is a hard problem).
    """
    issues: list[CoherenceIssue] = []
    touched = set(plan.touched_files)

    for task in execution_log.tasks:
        for cf in task.changed_files:
            if cf.path not in touched:
                issues.append(
                    CoherenceIssue(
                        check_name="plan_execute",
                        severity="error",
                        message=(
                            f"Changed file '{cf.path}' in execution log was not in "
                            "plan's touched_files."
                        ),
                    )
                )
    return issues


def _check_design_review(review: ReviewSchema) -> list[CoherenceIssue]:
    """COHR-04: design conformity check — if not conforming, raise coherence error.

    Severity: error.
    """
    issues: list[CoherenceIssue] = []
    if not review.design_conformity.conforms:
        deviations = "; ".join(review.design_conformity.deviations)
        message = "Design conformity failed in review."
        if deviations:
            message += f" Deviations: {deviations}"
        issues.append(
            CoherenceIssue(
                check_name="design_review",
                severity="error",
                message=message,
            )
        )
    return issues


def _check_research_review(
    research: ResearchSchema, review: ReviewSchema
) -> list[CoherenceIssue]:
    """COHR-05: convention violations in review indicate research drift.

    Note: research parameter kept for API consistency.
    Severity: warning.
    """
    issues: list[CoherenceIssue] = []
    if review.convention_violations:
        violations = "; ".join(review.convention_violations)
        issues.append(
            CoherenceIssue(
                check_name="research_review",
                severity="warning",
                message=f"Convention violations found in review: {violations}",
            )
        )
    return issues


def check_coherence(project_dir: Path) -> list[CoherenceIssue]:
    """Run all 5 inter-phase coherence checks. Never raises. Never mutates state.

    Missing artifact files cause that check to be skipped gracefully.

    Args:
        project_dir: Path to the project-ai/ directory containing JSON artifacts.

    Returns:
        List of CoherenceIssue instances. Empty list means fully coherent.
    """
    issues: list[CoherenceIssue] = []
    project_dir = Path(project_dir)

    research = _load_json(project_dir / "RESEARCH.json", ResearchSchema)
    design = _load_json(project_dir / "DESIGN.json", DesignSchema)
    plan = _load_json(project_dir / "PLAN.json", PlanSchema)
    execution_log = _load_json(project_dir / "EXECUTION_LOG.json", ExecutionLogSchema)
    review = _load_json(project_dir / "REVIEW.json", ReviewSchema)

    if research and design:
        issues.extend(_check_research_design(research, design))
    if design and plan:
        issues.extend(_check_design_plan(design, plan))
    if plan and execution_log:
        issues.extend(_check_plan_execute(plan, execution_log))
    if review:
        issues.extend(_check_design_review(review))
    if research and review:
        issues.extend(_check_research_review(research, review))

    return issues
