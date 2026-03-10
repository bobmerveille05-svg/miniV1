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
from typing import Literal

from pydantic import BaseModel, Field


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
    alternatives_rejected: list[str] = Field(default_factory=list)


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
    """Research artifact: codebase analysis output."""

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


class DesignSchema(BaseModel):
    """Design artifact: architecture and component decisions."""

    design_approach: str
    architecture_decisions: list[ArchitectureDecision] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    data_models: list[str] = Field(default_factory=list)
    api_contracts: list[str] = Field(default_factory=list)
    integration_points: list[str] = Field(default_factory=list)
    design_patterns_used: list[str] = Field(default_factory=list)
    conventions_to_follow: list[str] = Field(default_factory=list)
    technical_risks: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
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
