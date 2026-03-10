"""Tests for minilegion.core.coherence — inter-phase coherence checks.

Covers: CoherenceIssue dataclass, all 5 private sub-check functions,
and check_coherence() integration with real file I/O.
"""

from __future__ import annotations

import json
from pathlib import Path


from minilegion.core.coherence import (
    _check_design_plan,
    _check_design_review,
    _check_plan_execute,
    _check_research_design,
    _check_research_review,
    check_coherence,
)
from minilegion.core.schemas import (
    ArchitectureDecision,
    ChangedFile,
    Component,
    DesignConformity,
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    PlanTask,
    ResearchSchema,
    ReviewSchema,
    TaskResult,
    Verdict,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _research(focus_files=None, conventions=None) -> ResearchSchema:
    return ResearchSchema(
        project_overview="Test project",
        recommended_focus_files=focus_files or [],
        existing_conventions=conventions or [],
    )


def _design(components=None) -> DesignSchema:
    comps = components or [
        Component(
            name="Core",
            description="Core logic",
            files=["minilegion/core/new_module.py"],
        )
    ]
    return DesignSchema(
        design_approach="Layered",
        components=comps,
        architecture_decisions=[
            ArchitectureDecision(
                decision="Use Pydantic",
                rationale="Type safety",
                alternatives_rejected=["dataclasses"],
            )
        ],
        test_strategy="pytest",
        estimated_complexity="medium",
    )


def _plan(tasks=None, touched_files=None) -> PlanSchema:
    t = tasks or [
        PlanTask(
            id="T1",
            name="Create module",
            description="...",
            files=["minilegion/core/new_module.py"],
            depends_on=[],
            component="Core",
        )
    ]
    return PlanSchema(
        objective="Implement module",
        design_ref="DESIGN.json v1",
        tasks=t,
        touched_files=touched_files or ["minilegion/core/new_module.py"],
        test_plan="pytest",
    )


def _execution_log(changed_paths=None) -> ExecutionLogSchema:
    paths = changed_paths or ["minilegion/core/new_module.py"]
    return ExecutionLogSchema(
        tasks=[
            TaskResult(
                task_id="T1",
                changed_files=[ChangedFile(path=p, action="create") for p in paths],
            )
        ]
    )


def _review(conforms=True, deviations=None, violations=None) -> ReviewSchema:
    return ReviewSchema(
        design_conformity=DesignConformity(
            conforms=conforms,
            deviations=deviations or [],
        ),
        convention_violations=violations or [],
        verdict=Verdict.PASS,
    )


# ── TestCheckResearchDesign (COHR-01) ────────────────────────────────


class TestCheckResearchDesign:
    def test_focus_file_not_in_component_files_returns_issue(self):
        research = _research(focus_files=["minilegion/core/state.py"])
        design = _design(
            components=[
                Component(
                    name="Core",
                    description="Core",
                    files=["minilegion/core/new_module.py"],
                )
            ]
        )
        issues = _check_research_design(research, design)
        assert len(issues) == 1
        assert issues[0].check_name == "research_design"
        assert issues[0].severity == "warning"
        assert "state.py" in issues[0].message

    def test_focus_file_substring_of_component_file_returns_empty(self):
        # focus_file is substring of cf
        research = _research(focus_files=["new_module"])
        design = _design(
            components=[
                Component(
                    name="Core",
                    description="Core",
                    files=["minilegion/core/new_module.py"],
                )
            ]
        )
        issues = _check_research_design(research, design)
        assert issues == []

    def test_component_file_substring_of_focus_file_returns_empty(self):
        # cf is substring of focus_file
        research = _research(focus_files=["minilegion/core/new_module.py"])
        design = _design(
            components=[
                Component(
                    name="Core",
                    description="Core",
                    files=["minilegion/core/"],
                )
            ]
        )
        issues = _check_research_design(research, design)
        assert issues == []

    def test_all_focus_files_covered_returns_empty(self):
        research = _research(focus_files=["minilegion/core/new_module.py"])
        design = _design()
        issues = _check_research_design(research, design)
        assert issues == []

    def test_empty_focus_files_returns_empty(self):
        research = _research(focus_files=[])
        design = _design()
        issues = _check_research_design(research, design)
        assert issues == []


# ── TestCheckDesignPlan (COHR-02) ────────────────────────────────────


class TestCheckDesignPlan:
    def test_component_not_in_any_task_returns_issue(self):
        design = _design(
            components=[
                Component(name="Orphan", description="No task covers me", files=[])
            ]
        )
        plan = _plan(
            tasks=[
                PlanTask(
                    id="T1",
                    name="Task for Core",
                    description="...",
                    component="Core",
                )
            ]
        )
        issues = _check_design_plan(design, plan)
        assert len(issues) >= 1
        assert any(i.check_name == "design_plan" for i in issues)
        assert any(i.severity == "warning" for i in issues)

    def test_all_components_covered_returns_empty(self):
        design = _design()
        plan = _plan()
        issues = _check_design_plan(design, plan)
        assert issues == []

    def test_case_insensitive_match_returns_empty(self):
        design = _design(
            components=[Component(name="Core", description="Core logic", files=[])]
        )
        plan = _plan(
            tasks=[
                PlanTask(
                    id="T1",
                    name="Lowercase component",
                    description="...",
                    component="core",  # lowercase
                )
            ]
        )
        issues = _check_design_plan(design, plan)
        assert issues == []


# ── TestCheckPlanExecute (COHR-03) ───────────────────────────────────


class TestCheckPlanExecute:
    def test_changed_file_not_in_touched_files_returns_issue(self):
        plan = _plan(touched_files=["minilegion/core/new_module.py"])
        log = _execution_log(changed_paths=["minilegion/core/surprise.py"])
        issues = _check_plan_execute(plan, log)
        assert len(issues) >= 1
        assert issues[0].check_name == "plan_execute"
        assert issues[0].severity == "error"
        assert "surprise.py" in issues[0].message

    def test_all_changed_files_in_touched_returns_empty(self):
        plan = _plan(touched_files=["minilegion/core/new_module.py"])
        log = _execution_log(changed_paths=["minilegion/core/new_module.py"])
        issues = _check_plan_execute(plan, log)
        assert issues == []

    def test_empty_execution_log_tasks_returns_empty(self):
        plan = _plan()
        log = ExecutionLogSchema(tasks=[])
        issues = _check_plan_execute(plan, log)
        assert issues == []


# ── TestCheckDesignReview (COHR-04) ──────────────────────────────────


class TestCheckDesignReview:
    def test_design_not_conforming_returns_issue(self):
        review = _review(conforms=False, deviations=["Missing error handling"])
        issues = _check_design_review(review)
        assert len(issues) == 1
        assert issues[0].check_name == "design_review"
        assert issues[0].severity == "error"

    def test_design_conforming_returns_empty(self):
        review = _review(conforms=True)
        issues = _check_design_review(review)
        assert issues == []


# ── TestCheckResearchReview (COHR-05) ────────────────────────────────


class TestCheckResearchReview:
    def test_convention_violations_nonempty_returns_issue(self):
        research = _research()
        review = _review(violations=["Missing docstrings", "No type hints"])
        issues = _check_research_review(research, review)
        assert len(issues) == 1
        assert issues[0].check_name == "research_review"
        assert issues[0].severity == "warning"

    def test_no_convention_violations_returns_empty(self):
        research = _research()
        review = _review(violations=[])
        issues = _check_research_review(research, review)
        assert issues == []


# ── TestCheckCoherence (integration) ────────────────────────────────


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


VALID_RESEARCH = {
    "project_overview": "Test project",
    "tech_stack": [],
    "architecture_patterns": [],
    "relevant_files": [],
    "existing_conventions": [],
    "dependencies_map": {},
    "potential_impacts": [],
    "constraints": [],
    "assumptions_verified": [],
    "open_questions": [],
    "recommended_focus_files": ["minilegion/core/new_module.py"],
}

VALID_DESIGN = {
    "design_approach": "Modular",
    "architecture_decisions": [
        {
            "decision": "Use Pydantic",
            "rationale": "Type safety",
            "alternatives_rejected": ["dataclasses"],
        }
    ],
    "components": [
        {
            "name": "Core",
            "description": "Core logic",
            "files": ["minilegion/core/new_module.py"],
        }
    ],
    "data_models": [],
    "api_contracts": [],
    "integration_points": [],
    "design_patterns_used": [],
    "conventions_to_follow": [],
    "technical_risks": [],
    "out_of_scope": [],
    "test_strategy": "pytest",
    "estimated_complexity": "medium",
}

VALID_PLAN = {
    "objective": "Implement core module",
    "design_ref": "DESIGN.json v1",
    "assumptions": [],
    "tasks": [
        {
            "id": "T1",
            "name": "Create core module",
            "description": "...",
            "files": ["minilegion/core/new_module.py"],
            "depends_on": [],
            "component": "Core",
        }
    ],
    "touched_files": ["minilegion/core/new_module.py"],
    "risks": [],
    "success_criteria": [],
    "test_plan": "pytest",
}

VALID_EXECUTION_LOG = {
    "tasks": [
        {
            "task_id": "T1",
            "changed_files": [
                {
                    "path": "minilegion/core/new_module.py",
                    "action": "create",
                    "content": "",
                }
            ],
            "unchanged_files": [],
            "tests_run": [],
            "test_result": "",
            "blockers": [],
            "out_of_scope_needed": [],
        }
    ]
}

VALID_REVIEW = {
    "bugs": [],
    "scope_deviations": [],
    "design_conformity": {"conforms": True, "deviations": []},
    "convention_violations": [],
    "security_risks": [],
    "performance_risks": [],
    "tech_debt": [],
    "out_of_scope_files": [],
    "success_criteria_met": [],
    "verdict": "pass",
    "corrective_actions": [],
}


class TestCheckCoherence:
    def test_all_artifacts_missing_returns_empty(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        result = check_coherence(project_dir)
        assert result == []

    def test_only_research_present_returns_empty(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        _write_json(project_dir / "RESEARCH.json", VALID_RESEARCH)
        result = check_coherence(project_dir)
        assert result == []

    def test_coherent_pipeline_returns_empty(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        _write_json(project_dir / "RESEARCH.json", VALID_RESEARCH)
        _write_json(project_dir / "DESIGN.json", VALID_DESIGN)
        _write_json(project_dir / "PLAN.json", VALID_PLAN)
        _write_json(project_dir / "EXECUTION_LOG.json", VALID_EXECUTION_LOG)
        _write_json(project_dir / "REVIEW.json", VALID_REVIEW)
        result = check_coherence(project_dir)
        assert result == []

    def test_focus_file_not_in_design_returns_research_design_issue(
        self, tmp_project_dir
    ):
        project_dir = tmp_project_dir / "project-ai"
        research = dict(VALID_RESEARCH)
        research["recommended_focus_files"] = ["minilegion/core/state.py"]
        _write_json(project_dir / "RESEARCH.json", research)
        _write_json(project_dir / "DESIGN.json", VALID_DESIGN)
        result = check_coherence(project_dir)
        check_names = [i.check_name for i in result]
        assert "research_design" in check_names

    def test_component_not_in_plan_returns_design_plan_issue(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        design = dict(VALID_DESIGN)
        design["components"] = [
            {"name": "Orphan", "description": "No tasks cover this", "files": []}
        ]
        _write_json(project_dir / "DESIGN.json", design)
        _write_json(project_dir / "PLAN.json", VALID_PLAN)
        result = check_coherence(project_dir)
        check_names = [i.check_name for i in result]
        assert "design_plan" in check_names

    def test_changed_file_not_in_touched_returns_plan_execute_issue(
        self, tmp_project_dir
    ):
        project_dir = tmp_project_dir / "project-ai"
        log = {
            "tasks": [
                {
                    "task_id": "T1",
                    "changed_files": [
                        {
                            "path": "minilegion/core/surprise.py",
                            "action": "create",
                            "content": "",
                        }
                    ],
                    "unchanged_files": [],
                    "tests_run": [],
                    "test_result": "",
                    "blockers": [],
                    "out_of_scope_needed": [],
                }
            ]
        }
        _write_json(project_dir / "PLAN.json", VALID_PLAN)
        _write_json(project_dir / "EXECUTION_LOG.json", log)
        result = check_coherence(project_dir)
        check_names = [i.check_name for i in result]
        assert "plan_execute" in check_names

    def test_nonconforming_review_returns_design_review_issue(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        review = dict(VALID_REVIEW)
        review["design_conformity"] = {
            "conforms": False,
            "deviations": ["Missing tests"],
        }
        _write_json(project_dir / "REVIEW.json", review)
        result = check_coherence(project_dir)
        check_names = [i.check_name for i in result]
        assert "design_review" in check_names

    def test_convention_violations_returns_research_review_issue(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        _write_json(project_dir / "RESEARCH.json", VALID_RESEARCH)
        review = dict(VALID_REVIEW)
        review["convention_violations"] = ["No docstrings"]
        _write_json(project_dir / "REVIEW.json", review)
        result = check_coherence(project_dir)
        check_names = [i.check_name for i in result]
        assert "research_review" in check_names

    def test_corrupted_json_does_not_raise(self, tmp_project_dir):
        project_dir = tmp_project_dir / "project-ai"
        (project_dir / "RESEARCH.json").write_text("NOT VALID JSON", encoding="utf-8")
        (project_dir / "DESIGN.json").write_text("{bad json", encoding="utf-8")
        # Should not raise
        result = check_coherence(project_dir)
        assert isinstance(result, list)
