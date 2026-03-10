"""Dual-output renderer: Pydantic models → human-readable Markdown.

Each LLM-produced artifact schema has a dedicated render function that
produces structured Markdown. The save_dual() convenience function
writes both JSON and Markdown atomically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from minilegion.core.file_io import write_atomic
from minilegion.core.schemas import (
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    ResearchSchema,
    ReviewSchema,
)


# ── Private helpers ───────────────────────────────────────────────────


def _bullets(items: list[str], heading: str) -> str:
    """Render a list as a Markdown section with bullet points.

    Returns empty string if *items* is empty — the section is omitted entirely.
    """
    if not items:
        return ""
    lines = [f"## {heading}\n"]
    for item in items:
        lines.append(f"- {item}")
    lines.append("")  # trailing newline
    return "\n".join(lines) + "\n"


def _kv(label: str, value: str) -> str:
    """Render a key-value pair as bold label + value."""
    return f"**{label}:** {value}\n\n"


# ── Per-schema render functions ───────────────────────────────────────


def render_research_md(data: ResearchSchema) -> str:
    """Render a ResearchSchema to structured Markdown."""
    parts: list[str] = ["# Research Report\n\n"]

    # Project Overview (always present — it's a required str field)
    parts.append("## Project Overview\n\n")
    parts.append(f"{data.project_overview}\n\n")

    parts.append(_bullets(data.tech_stack, "Tech Stack"))
    parts.append(_bullets(data.architecture_patterns, "Architecture Patterns"))
    parts.append(_bullets(data.relevant_files, "Relevant Files"))
    parts.append(_bullets(data.existing_conventions, "Existing Conventions"))

    # Dependencies map: nested sections
    if data.dependencies_map:
        parts.append("## Dependencies Map\n\n")
        for key, deps in data.dependencies_map.items():
            parts.append(f"### {key}\n\n")
            for dep in deps:
                parts.append(f"- {dep}\n")
            parts.append("\n")

    parts.append(_bullets(data.potential_impacts, "Potential Impacts"))
    parts.append(_bullets(data.constraints, "Constraints"))
    parts.append(_bullets(data.assumptions_verified, "Assumptions Verified"))
    parts.append(_bullets(data.open_questions, "Open Questions"))
    parts.append(_bullets(data.recommended_focus_files, "Recommended Focus Files"))

    return "".join(parts)


def render_design_md(data: DesignSchema) -> str:
    """Render a DesignSchema to structured Markdown."""
    parts: list[str] = ["# Design Document\n\n"]

    parts.append("## Design Approach\n\n")
    parts.append(f"{data.design_approach}\n\n")

    # Architecture decisions
    if data.architecture_decisions:
        parts.append("## Architecture Decisions\n\n")
        for ad in data.architecture_decisions:
            parts.append(f"### {ad.decision}\n\n")
            parts.append(f"{ad.rationale}\n\n")
            if ad.alternatives_rejected:
                parts.append("**Rejected alternatives:**\n\n")
                for alt in ad.alternatives_rejected:
                    parts.append(f"- {alt}\n")
                parts.append("\n")

    # Components
    if data.components:
        parts.append("## Components\n\n")
        for comp in data.components:
            parts.append(f"### {comp.name}\n\n")
            parts.append(f"{comp.description}\n\n")
            if comp.files:
                parts.append("**Files:**\n\n")
                for f in comp.files:
                    parts.append(f"- {f}\n")
                parts.append("\n")

    parts.append(_bullets(data.data_models, "Data Models"))
    parts.append(_bullets(data.api_contracts, "API Contracts"))
    parts.append(_bullets(data.integration_points, "Integration Points"))
    parts.append(_bullets(data.design_patterns_used, "Design Patterns Used"))
    parts.append(_bullets(data.conventions_to_follow, "Conventions to Follow"))
    parts.append(_bullets(data.technical_risks, "Technical Risks"))
    parts.append(_bullets(data.out_of_scope, "Out of Scope"))

    parts.append("## Test Strategy\n\n")
    parts.append(f"{data.test_strategy}\n\n")

    parts.append("## Estimated Complexity\n\n")
    parts.append(f"{data.estimated_complexity}\n\n")

    return "".join(parts)


def render_plan_md(data: PlanSchema) -> str:
    """Render a PlanSchema to structured Markdown."""
    parts: list[str] = ["# Implementation Plan\n\n"]

    parts.append("## Objective\n\n")
    parts.append(f"{data.objective}\n\n")

    parts.append("## Design Reference\n\n")
    parts.append(f"{data.design_ref}\n\n")

    parts.append(_bullets(data.assumptions, "Assumptions"))

    # Tasks
    if data.tasks:
        parts.append("## Tasks\n\n")
        for task in data.tasks:
            parts.append(f"### {task.id}: {task.name}\n\n")
            parts.append(f"{task.description}\n\n")
            if task.files:
                parts.append("**Files:**\n\n")
                for f in task.files:
                    parts.append(f"- {f}\n")
                parts.append("\n")
            if task.depends_on:
                parts.append(f"**Depends on:** {', '.join(task.depends_on)}\n\n")
            if task.component:
                parts.append(f"**Component:** {task.component}\n\n")

    parts.append(_bullets(data.touched_files, "Touched Files"))
    parts.append(_bullets(data.risks, "Risks"))
    parts.append(_bullets(data.success_criteria, "Success Criteria"))

    parts.append("## Test Plan\n\n")
    parts.append(f"{data.test_plan}\n\n")

    return "".join(parts)


def render_execution_log_md(data: ExecutionLogSchema) -> str:
    """Render an ExecutionLogSchema to structured Markdown."""
    parts: list[str] = ["# Execution Log\n\n"]

    if not data.tasks:
        parts.append("No tasks executed.\n\n")
        return "".join(parts)

    for task in data.tasks:
        parts.append(f"## Task: {task.task_id}\n\n")

        if task.changed_files:
            parts.append("### Changed Files\n\n")
            for cf in task.changed_files:
                parts.append(f"- `{cf.path}` ({cf.action})\n")
            parts.append("\n")

        if task.unchanged_files:
            parts.append("### Unchanged Files\n\n")
            for uf in task.unchanged_files:
                parts.append(f"- {uf}\n")
            parts.append("\n")

        if task.tests_run:
            parts.append("### Tests Run\n\n")
            for t in task.tests_run:
                parts.append(f"- {t}\n")
            parts.append("\n")

        if task.test_result:
            parts.append(_kv("Test Result", task.test_result))

        if task.blockers:
            parts.append("### Blockers\n\n")
            for b in task.blockers:
                parts.append(f"- {b}\n")
            parts.append("\n")

        if task.out_of_scope_needed:
            parts.append("### Out of Scope Needed\n\n")
            for o in task.out_of_scope_needed:
                parts.append(f"- {o}\n")
            parts.append("\n")

    return "".join(parts)


def render_decisions_md(design_data: DesignSchema) -> str:
    """Render architecture decisions from DesignSchema to DECISIONS.md content.

    Not registered in _RENDERERS — called directly from archive() via write_atomic().
    """
    parts: list[str] = ["# Architecture Decisions\n\n"]

    if not design_data.architecture_decisions:
        parts.append("_No architecture decisions recorded._\n")
        return "".join(parts)

    for ad in design_data.architecture_decisions:
        parts.append(f"### Decision: {ad.decision}\n\n")
        parts.append(f"**Rationale:** {ad.rationale}\n\n")
        if ad.alternatives_rejected:
            parts.append("**Alternatives Rejected:**\n\n")
            for alt in ad.alternatives_rejected:
                parts.append(f"- {alt}\n")
            parts.append("\n")

    return "".join(parts)


def render_review_md(data: ReviewSchema) -> str:
    """Render a ReviewSchema to structured Markdown."""
    parts: list[str] = ["# Review Report\n\n"]

    parts.append("## Verdict\n\n")
    parts.append(f"**{data.verdict.value.upper()}**\n\n")

    parts.append(_bullets(data.bugs, "Bugs"))
    parts.append(_bullets(data.scope_deviations, "Scope Deviations"))

    # Design conformity
    parts.append("## Design Conformity\n\n")
    conforms_str = "Yes" if data.design_conformity.conforms else "No"
    parts.append(f"**Conforms:** {conforms_str}\n\n")
    if data.design_conformity.deviations:
        parts.append("**Deviations:**\n\n")
        for d in data.design_conformity.deviations:
            parts.append(f"- {d}\n")
        parts.append("\n")

    parts.append(_bullets(data.convention_violations, "Convention Violations"))
    parts.append(_bullets(data.security_risks, "Security Risks"))
    parts.append(_bullets(data.performance_risks, "Performance Risks"))
    parts.append(_bullets(data.tech_debt, "Tech Debt"))
    parts.append(_bullets(data.out_of_scope_files, "Out of Scope Files"))
    parts.append(_bullets(data.success_criteria_met, "Success Criteria Met"))
    parts.append(_bullets(data.corrective_actions, "Corrective Actions"))

    return "".join(parts)


# ── Renderer registry ────────────────────────────────────────────────


_RENDERERS: dict[str, Callable] = {
    "ResearchSchema": render_research_md,
    "DesignSchema": render_design_md,
    "PlanSchema": render_plan_md,
    "ExecutionLogSchema": render_execution_log_md,
    "ReviewSchema": render_review_md,
}


# ── save_dual convenience function ───────────────────────────────────


def save_dual(data: BaseModel, json_path: Path, md_path: Path) -> None:
    """Write both JSON and Markdown representations of *data* atomically.

    Args:
        data: A Pydantic model instance (must be one of the 5 registered schemas).
        json_path: Destination path for the JSON file.
        md_path: Destination path for the Markdown file.

    Raises:
        ValueError: If *data*'s type is not in the renderer registry.
    """
    json_path = Path(json_path)
    md_path = Path(md_path)

    # JSON output
    json_str = data.model_dump_json(indent=2)
    write_atomic(json_path, json_str)

    # Markdown output
    type_name = type(data).__name__
    renderer = _RENDERERS.get(type_name)
    if renderer is None:
        raise ValueError(f"No renderer registered for {type_name}")
    md_str = renderer(data)
    write_atomic(md_path, md_str)
