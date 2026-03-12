"""Pydantic models for all MiniLegion artifact schemas.

Defines the 5 machine-readable artifact types produced by LLM pipeline stages:
- ResearchSchema: codebase research output
- DesignSchema: architecture and design decisions
- PlanSchema: implementation plan with tasks
- ExecutionLogSchema: build execution log
- ReviewSchema: code review with verdict

The 6th artifact type (ProjectState) lives in core/state.py and is
registered in the schema registry without duplication.
"""

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field


def _coerce_str_or_obj(v: Any) -> str:
    """Coerce a value to string.

    LLMs sometimes emit objects like ``{"name": "X", "reason": "Y"}`` for
    fields that should be plain strings.  We flatten those to a readable
    string so validation never fails on well-intentioned LLM output.
    """
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        # Try common key patterns the LLM uses
        name = v.get("name") or v.get("pattern") or v.get("risk") or v.get("type") or ""
        extra = (
            v.get("reason")
            or v.get("description")
            or v.get("mitigation")
            or v.get("rationale")
            or ""
        )
        parts = [str(p) for p in (name, extra) if p]
        return ": ".join(parts) if parts else str(v)
    return str(v)


CoercedStr = Annotated[str, BeforeValidator(_coerce_str_or_obj)]


# ── Enums ─────────────────────────────────────────────────────────────


class Verdict(str, Enum):
    """Review verdict: pass or revise."""

    PASS = "pass"
    REVISE = "revise"


# ── Nested Sub-Models ─────────────────────────────────────────────────


class ArchitectureDecision(BaseModel):
    """A single architecture decision with rationale."""

    decision: str
    rationale: str
    alternatives_rejected: list[CoercedStr] = Field(default_factory=list, min_length=1)


class Component(BaseModel):
    """A design component with its associated files."""

    name: str
    description: str
    files: list[str] = Field(default_factory=list)


class PlanTask(BaseModel):
    """A single task within an implementation plan."""

    id: str
    name: str
    description: str
    files: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    component: str = ""


class ChangedFile(BaseModel):
    """A file changed during execution."""

    path: str
    action: Literal["create", "modify", "delete"]
    content: str = ""


class TaskResult(BaseModel):
    """Result of executing a single plan task."""

    task_id: str
    changed_files: list[ChangedFile] = Field(default_factory=list)
    unchanged_files: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    test_result: str = ""
    blockers: list[str] = Field(default_factory=list)
    out_of_scope_needed: list[str] = Field(default_factory=list)


class DesignConformity(BaseModel):
    """Design conformity assessment within a review."""

    conforms: bool
    deviations: list[str] = Field(default_factory=list)


# ── Top-Level Artifact Schemas ────────────────────────────────────────


class ResearchSchema(BaseModel):
    """Research artifact: codebase analysis output — supports fact mode (default) and brainstorm mode (structured directions)."""

    project_overview: str
    tech_stack: list[str] = Field(default_factory=list)
    architecture_patterns: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    existing_conventions: list[str] = Field(default_factory=list)
    dependencies_map: dict[str, list[str]] = Field(default_factory=dict)
    potential_impacts: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions_verified: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recommended_focus_files: list[str] = Field(default_factory=list)

    # Brainstorm-mode fields (optional — absent in fact mode, populated in brainstorm mode)
    problem_framing: str | None = None
    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    candidate_directions: list[dict] | None = None
    tradeoffs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: str | None = None


class DesignSchema(BaseModel):
    """Design artifact: architecture and component decisions."""

    design_approach: str
    architecture_decisions: list[ArchitectureDecision] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    data_models: list[CoercedStr] = Field(default_factory=list)
    api_contracts: list[CoercedStr] = Field(default_factory=list)
    integration_points: list[CoercedStr] = Field(default_factory=list)
    design_patterns_used: list[CoercedStr] = Field(default_factory=list)
    conventions_to_follow: list[CoercedStr] = Field(default_factory=list)
    technical_risks: list[CoercedStr] = Field(default_factory=list)
    out_of_scope: list[CoercedStr] = Field(default_factory=list)
    test_strategy: str
    estimated_complexity: str = "medium"


class PlanSchema(BaseModel):
    """Plan artifact: implementation plan with task breakdown."""

    objective: str
    design_ref: str
    assumptions: list[str] = Field(default_factory=list)
    tasks: list[PlanTask] = Field(default_factory=list)
    touched_files: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    test_plan: str


class ExecutionLogSchema(BaseModel):
    """Execution log artifact: build results and changed files."""

    tasks: list[TaskResult] = Field(default_factory=list)


class ReviewSchema(BaseModel):
    """Review artifact: code review with verdict and findings."""

    bugs: list[str] = Field(default_factory=list)
    scope_deviations: list[str] = Field(default_factory=list)
    design_conformity: DesignConformity
    convention_violations: list[str] = Field(default_factory=list)
    security_risks: list[str] = Field(default_factory=list)
    performance_risks: list[str] = Field(default_factory=list)
    tech_debt: list[str] = Field(default_factory=list)
    out_of_scope_files: list[str] = Field(default_factory=list)
    success_criteria_met: list[str] = Field(default_factory=list)
    verdict: Verdict
    corrective_actions: list[str] = Field(default_factory=list)
