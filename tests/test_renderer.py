"""Tests for minilegion.core.renderer — dual-output Markdown rendering.

Covers: render_*_md() for all 5 schema types + save_dual() convenience function.
"""

import json

import pytest
from unittest.mock import patch

from minilegion.core.schemas import (
    ResearchSchema,
    DesignSchema,
    PlanSchema,
    ExecutionLogSchema,
    ReviewSchema,
    ArchitectureDecision,
    Component,
    PlanTask,
    TaskResult,
    ChangedFile,
    DesignConformity,
    Verdict,
)
from minilegion.core.renderer import (
    render_research_md,
    render_design_md,
    render_plan_md,
    render_execution_log_md,
    render_review_md,
    save_dual,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _full_research() -> ResearchSchema:
    return ResearchSchema(
        project_overview="A test project for unit testing.",
        tech_stack=["Python", "Pydantic"],
        architecture_patterns=["MVC", "Event-driven"],
        relevant_files=["src/main.py", "src/utils.py"],
        existing_conventions=["PEP 8", "type hints everywhere"],
        dependencies_map={"core": ["utils", "config"], "cli": ["core"]},
        potential_impacts=["Performance regression on large inputs"],
        constraints=["Must run on Python 3.11+"],
        assumptions_verified=["Pydantic v2 available"],
        open_questions=["Should we support async?"],
        recommended_focus_files=["src/main.py"],
    )


def _full_design() -> DesignSchema:
    return DesignSchema(
        design_approach="Layered architecture with clean boundaries.",
        architecture_decisions=[
            ArchitectureDecision(
                decision="Use Pydantic for validation",
                rationale="Built-in JSON support",
                alternatives_rejected=["dataclasses", "attrs"],
            ),
        ],
        components=[
            Component(
                name="Renderer",
                description="Converts models to Markdown",
                files=["renderer.py", "templates.py"],
            ),
        ],
        data_models=["ResearchSchema", "DesignSchema"],
        api_contracts=["POST /api/render"],
        integration_points=["File system via write_atomic"],
        design_patterns_used=["Strategy pattern"],
        conventions_to_follow=["Use _private helpers"],
        technical_risks=["Markdown injection"],
        out_of_scope=["PDF rendering"],
        test_strategy="Unit tests for each render function.",
        estimated_complexity="medium",
    )


def _full_plan() -> PlanSchema:
    return PlanSchema(
        objective="Implement the renderer module.",
        design_ref="design-v1.json",
        assumptions=["Schemas are stable"],
        tasks=[
            PlanTask(
                id="T1",
                name="Create renderer",
                description="Build the render functions",
                files=["renderer.py"],
                depends_on=[],
                component="core",
            ),
            PlanTask(
                id="T2",
                name="Add tests",
                description="Write comprehensive tests",
                files=["test_renderer.py"],
                depends_on=["T1"],
                component="tests",
            ),
        ],
        touched_files=["renderer.py", "test_renderer.py"],
        risks=["Schema changes mid-flight"],
        success_criteria=["All tests pass", "100% field coverage"],
        test_plan="pytest with -x flag for fail-fast.",
    )


def _full_execution_log() -> ExecutionLogSchema:
    return ExecutionLogSchema(
        tasks=[
            TaskResult(
                task_id="T1",
                changed_files=[
                    ChangedFile(path="renderer.py", action="create", content="..."),
                ],
                unchanged_files=["schemas.py"],
                tests_run=["test_render_research"],
                test_result="passed",
                blockers=["None"],
                out_of_scope_needed=["PDF support"],
            ),
        ],
    )


def _full_review_pass() -> ReviewSchema:
    return ReviewSchema(
        bugs=["Off-by-one in bullet list"],
        scope_deviations=["Added PDF stub"],
        design_conformity=DesignConformity(conforms=True, deviations=[]),
        convention_violations=["Missing docstring on helper"],
        security_risks=["Markdown injection possible"],
        performance_risks=["Large models slow to render"],
        tech_debt=["Duplicate heading logic"],
        out_of_scope_files=["pdf_renderer.py"],
        success_criteria_met=["All tests pass"],
        verdict=Verdict.PASS,
        corrective_actions=[],
    )


def _full_review_revise() -> ReviewSchema:
    return ReviewSchema(
        bugs=[],
        scope_deviations=[],
        design_conformity=DesignConformity(
            conforms=False, deviations=["Missing error handling"]
        ),
        convention_violations=[],
        security_risks=[],
        performance_risks=[],
        tech_debt=[],
        out_of_scope_files=[],
        success_criteria_met=[],
        verdict=Verdict.REVISE,
        corrective_actions=["Add try/except in save_dual", "Fix missing heading"],
    )


# ── TestRenderResearchMd ─────────────────────────────────────────────


class TestRenderResearchMd:
    def test_full_research(self):
        data = _full_research()
        md = render_research_md(data)
        assert "# Research Report" in md
        assert "## Project Overview" in md
        assert "## Tech Stack" in md
        assert "Python" in md
        assert "Pydantic" in md

    def test_empty_lists_omitted(self):
        data = ResearchSchema(project_overview="Just an overview.")
        md = render_research_md(data)
        assert "# Research Report" in md
        assert "## Project Overview" in md
        assert "Just an overview." in md
        # Empty list sections should not appear
        assert "## Tech Stack" not in md

    def test_dependencies_map_rendered(self):
        data = ResearchSchema(
            project_overview="Test",
            dependencies_map={"core": ["utils", "config"]},
        )
        md = render_research_md(data)
        assert "core" in md
        assert "utils" in md
        assert "config" in md


# ── TestRenderDesignMd ────────────────────────────────────────────────


class TestRenderDesignMd:
    def test_full_design(self):
        data = _full_design()
        md = render_design_md(data)
        assert "# Design Document" in md
        assert "Use Pydantic for validation" in md
        assert "dataclasses" in md
        assert "attrs" in md

    def test_components_with_files(self):
        data = _full_design()
        md = render_design_md(data)
        assert "Renderer" in md
        assert "renderer.py" in md
        assert "templates.py" in md

    def test_empty_design(self):
        data = DesignSchema(
            design_approach="Minimal",
            test_strategy="None",
            estimated_complexity="low",
        )
        md = render_design_md(data)
        assert "# Design Document" in md
        assert "Minimal" in md


# ── TestRenderPlanMd ──────────────────────────────────────────────────


class TestRenderPlanMd:
    def test_full_plan(self):
        data = _full_plan()
        md = render_plan_md(data)
        assert "# Implementation Plan" in md
        assert "T1" in md
        assert "Create renderer" in md
        assert "T2" in md
        assert "Add tests" in md

    def test_task_details(self):
        data = _full_plan()
        md = render_plan_md(data)
        assert "Build the render functions" in md
        assert "renderer.py" in md
        assert "T1" in md
        assert "core" in md


# ── TestRenderExecutionLogMd ──────────────────────────────────────────


class TestRenderExecutionLogMd:
    def test_full_log(self):
        data = _full_execution_log()
        md = render_execution_log_md(data)
        assert "# Execution Log" in md
        assert "T1" in md
        assert "renderer.py" in md
        assert "create" in md

    def test_empty_log(self):
        data = ExecutionLogSchema(tasks=[])
        md = render_execution_log_md(data)
        assert "# Execution Log" in md


# ── TestRenderReviewMd ────────────────────────────────────────────────


class TestRenderReviewMd:
    def test_pass_verdict(self):
        data = _full_review_pass()
        md = render_review_md(data)
        assert "pass" in md.lower()

    def test_revise_verdict_with_actions(self):
        data = _full_review_revise()
        md = render_review_md(data)
        assert "revise" in md.lower()
        assert "Add try/except in save_dual" in md
        assert "Fix missing heading" in md

    def test_design_conformity_conforms(self):
        data = _full_review_pass()
        md = render_review_md(data)
        assert "Yes" in md or "yes" in md.lower()

    def test_design_conformity_deviations(self):
        data = _full_review_revise()
        md = render_review_md(data)
        assert "Missing error handling" in md


# ── TestSaveDual ──────────────────────────────────────────────────────


class TestSaveDual:
    def test_saves_both_files(self, tmp_path):
        data = _full_research()
        json_path = tmp_path / "research.json"
        md_path = tmp_path / "research.md"
        save_dual(data, json_path, md_path)
        assert json_path.exists()
        assert md_path.exists()

    def test_json_is_valid(self, tmp_path):
        data = _full_research()
        json_path = tmp_path / "research.json"
        md_path = tmp_path / "research.md"
        save_dual(data, json_path, md_path)
        content = json_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "project_overview" in parsed
        assert parsed["project_overview"] == "A test project for unit testing."

    def test_md_starts_with_heading(self, tmp_path):
        data = _full_research()
        json_path = tmp_path / "research.json"
        md_path = tmp_path / "research.md"
        save_dual(data, json_path, md_path)
        content = md_path.read_text(encoding="utf-8")
        assert content.startswith("#")

    def test_unknown_type_raises_value_error(self, tmp_path):
        from pydantic import BaseModel

        class UnknownModel(BaseModel):
            x: int = 1

        data = UnknownModel()
        json_path = tmp_path / "unknown.json"
        md_path = tmp_path / "unknown.md"
        with pytest.raises(ValueError, match="No renderer registered"):
            save_dual(data, json_path, md_path)

    def test_uses_write_atomic(self, tmp_path):
        data = _full_research()
        json_path = tmp_path / "research.json"
        md_path = tmp_path / "research.md"
        with patch("minilegion.core.renderer.write_atomic") as mock_wa:
            save_dual(data, json_path, md_path)
            assert mock_wa.call_count == 2
