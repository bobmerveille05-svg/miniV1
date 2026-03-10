"""Tests for minilegion.core.schemas — Pydantic models for all artifact types."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from minilegion.core.schemas import (
    ArchitectureDecision,
    ChangedFile,
    Component,
    DesignConformity,
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    PlanTask,
    ReviewSchema,
    ResearchSchema,
    TaskResult,
    Verdict,
)


# ── Verdict Enum ──────────────────────────────────────────────────────


class TestVerdictEnum:
    """Verdict enum uses str+Enum pattern for JSON serialization."""

    def test_pass_value(self):
        assert Verdict.PASS == "pass"
        assert Verdict.PASS.value == "pass"

    def test_revise_value(self):
        assert Verdict.REVISE == "revise"
        assert Verdict.REVISE.value == "revise"

    def test_string_comparison(self):
        assert Verdict.PASS == "pass"
        assert Verdict.REVISE == "revise"


# ── Nested Sub-Models ─────────────────────────────────────────────────


class TestArchitectureDecision:
    """ArchitectureDecision nested model validation."""

    def test_valid_architecture_decision(self):
        ad = ArchitectureDecision(
            decision="Use REST API",
            rationale="Simple and well-understood",
            alternatives_rejected=["GraphQL", "gRPC"],
        )
        assert ad.decision == "Use REST API"
        assert ad.rationale == "Simple and well-understood"
        assert ad.alternatives_rejected == ["GraphQL", "gRPC"]

    def test_missing_decision_field_rejected(self):
        with pytest.raises(PydanticValidationError):
            ArchitectureDecision(
                rationale="reason",
                alternatives_rejected=[],
            )

    def test_missing_rationale_field_rejected(self):
        with pytest.raises(PydanticValidationError):
            ArchitectureDecision(
                decision="Use REST",
                alternatives_rejected=[],
            )


class TestChangedFile:
    """ChangedFile with Literal action constraint."""

    def test_valid_create_action(self):
        cf = ChangedFile(path="src/main.py", action="create", content="# new file")
        assert cf.action == "create"

    def test_valid_modify_action(self):
        cf = ChangedFile(path="src/main.py", action="modify", content="# modified")
        assert cf.action == "modify"

    def test_valid_delete_action(self):
        cf = ChangedFile(path="src/main.py", action="delete", content="")
        assert cf.action == "delete"

    def test_invalid_action_rejected(self):
        with pytest.raises(PydanticValidationError):
            ChangedFile(path="src/main.py", action="rename", content="")


# ── ResearchSchema ────────────────────────────────────────────────────


class TestResearchSchema:
    """ResearchSchema accepts valid data and rejects missing required fields."""

    def test_valid_minimal_research(self):
        """Required string fields provided, list fields default to empty."""
        r = ResearchSchema(project_overview="An overview of the project")
        assert r.project_overview == "An overview of the project"
        assert r.tech_stack == []
        assert r.architecture_patterns == []
        assert r.relevant_files == []
        assert r.existing_conventions == []
        assert r.dependencies_map == {}
        assert r.potential_impacts == []
        assert r.constraints == []
        assert r.assumptions_verified == []
        assert r.open_questions == []
        assert r.recommended_focus_files == []

    def test_missing_project_overview_rejected(self):
        with pytest.raises(PydanticValidationError):
            ResearchSchema()

    def test_roundtrip_json(self):
        r = ResearchSchema(
            project_overview="test",
            tech_stack=["python"],
            constraints=["must be fast"],
        )
        json_str = r.model_dump_json()
        r2 = ResearchSchema.model_validate_json(json_str)
        assert r2.project_overview == "test"
        assert r2.tech_stack == ["python"]
        assert r2.constraints == ["must be fast"]


# ── DesignSchema ──────────────────────────────────────────────────────


class TestDesignSchema:
    """DesignSchema with nested ArchitectureDecision and Component."""

    def test_valid_minimal_design(self):
        d = DesignSchema(
            design_approach="Layered architecture",
            test_strategy="Unit tests for all modules",
        )
        assert d.design_approach == "Layered architecture"
        assert d.test_strategy == "Unit tests for all modules"
        assert d.estimated_complexity == "medium"
        assert d.architecture_decisions == []
        assert d.components == []

    def test_missing_design_approach_rejected(self):
        with pytest.raises(PydanticValidationError):
            DesignSchema(test_strategy="Unit tests")

    def test_missing_test_strategy_rejected(self):
        with pytest.raises(PydanticValidationError):
            DesignSchema(design_approach="Layered")

    def test_with_nested_models(self):
        d = DesignSchema(
            design_approach="Modular",
            test_strategy="Integration tests",
            architecture_decisions=[
                ArchitectureDecision(
                    decision="Use REST",
                    rationale="Simple",
                    alternatives_rejected=["GraphQL"],
                )
            ],
            components=[
                Component(name="API", description="REST API layer", files=["api.py"])
            ],
        )
        assert len(d.architecture_decisions) == 1
        assert d.architecture_decisions[0].decision == "Use REST"
        assert len(d.components) == 1
        assert d.components[0].name == "API"

    def test_roundtrip_json(self):
        d = DesignSchema(
            design_approach="test",
            test_strategy="test",
            estimated_complexity="high",
        )
        json_str = d.model_dump_json()
        d2 = DesignSchema.model_validate_json(json_str)
        assert d2.estimated_complexity == "high"


# ── PlanSchema ────────────────────────────────────────────────────────


class TestPlanSchema:
    """PlanSchema with nested PlanTask."""

    def test_valid_minimal_plan(self):
        p = PlanSchema(
            objective="Build the API",
            design_ref="DESIGN-001",
            test_plan="Run pytest",
        )
        assert p.objective == "Build the API"
        assert p.design_ref == "DESIGN-001"
        assert p.test_plan == "Run pytest"
        assert p.tasks == []
        assert p.assumptions == []
        assert p.touched_files == []
        assert p.risks == []
        assert p.success_criteria == []

    def test_missing_objective_rejected(self):
        with pytest.raises(PydanticValidationError):
            PlanSchema(design_ref="ref", test_plan="plan")

    def test_missing_design_ref_rejected(self):
        with pytest.raises(PydanticValidationError):
            PlanSchema(objective="obj", test_plan="plan")

    def test_missing_test_plan_rejected(self):
        with pytest.raises(PydanticValidationError):
            PlanSchema(objective="obj", design_ref="ref")

    def test_with_tasks(self):
        p = PlanSchema(
            objective="Build API",
            design_ref="ref",
            test_plan="pytest",
            tasks=[
                PlanTask(
                    id="T1",
                    name="Create endpoints",
                    description="REST endpoints",
                    files=["api.py"],
                    depends_on=[],
                    component="API",
                )
            ],
        )
        assert len(p.tasks) == 1
        assert p.tasks[0].id == "T1"

    def test_roundtrip_json(self):
        p = PlanSchema(objective="test", design_ref="ref", test_plan="plan")
        json_str = p.model_dump_json()
        p2 = PlanSchema.model_validate_json(json_str)
        assert p2.objective == "test"


# ── ExecutionLogSchema ────────────────────────────────────────────────


class TestExecutionLogSchema:
    """ExecutionLogSchema with nested TaskResult and ChangedFile."""

    def test_valid_minimal_execution_log(self):
        e = ExecutionLogSchema()
        assert e.tasks == []

    def test_with_task_results(self):
        e = ExecutionLogSchema(
            tasks=[
                TaskResult(
                    task_id="T1",
                    changed_files=[
                        ChangedFile(
                            path="src/main.py",
                            action="create",
                            content="print('hello')",
                        )
                    ],
                    test_result="passed",
                )
            ]
        )
        assert len(e.tasks) == 1
        assert e.tasks[0].task_id == "T1"
        assert e.tasks[0].changed_files[0].action == "create"

    def test_roundtrip_json(self):
        e = ExecutionLogSchema(
            tasks=[
                TaskResult(
                    task_id="T1",
                    changed_files=[],
                    test_result="passed",
                )
            ]
        )
        json_str = e.model_dump_json()
        e2 = ExecutionLogSchema.model_validate_json(json_str)
        assert e2.tasks[0].task_id == "T1"


# ── ReviewSchema ──────────────────────────────────────────────────────


class TestReviewSchema:
    """ReviewSchema with Verdict enum and DesignConformity."""

    def test_valid_minimal_review(self):
        r = ReviewSchema(
            verdict=Verdict.PASS,
            design_conformity=DesignConformity(conforms=True),
        )
        assert r.verdict == Verdict.PASS
        assert r.design_conformity.conforms is True
        assert r.design_conformity.deviations == []
        assert r.bugs == []
        assert r.corrective_actions == []

    def test_verdict_revise(self):
        r = ReviewSchema(
            verdict=Verdict.REVISE,
            design_conformity=DesignConformity(conforms=False, deviations=["missed X"]),
            corrective_actions=["Fix X"],
        )
        assert r.verdict == Verdict.REVISE
        assert r.design_conformity.deviations == ["missed X"]

    def test_missing_verdict_rejected(self):
        with pytest.raises(PydanticValidationError):
            ReviewSchema(
                design_conformity=DesignConformity(conforms=True),
            )

    def test_missing_design_conformity_rejected(self):
        with pytest.raises(PydanticValidationError):
            ReviewSchema(verdict=Verdict.PASS)

    def test_roundtrip_json(self):
        r = ReviewSchema(
            verdict=Verdict.PASS,
            design_conformity=DesignConformity(conforms=True),
            bugs=["minor typo"],
        )
        json_str = r.model_dump_json()
        r2 = ReviewSchema.model_validate_json(json_str)
        assert r2.verdict == Verdict.PASS
        assert r2.bugs == ["minor typo"]

    def test_verdict_serializes_as_string(self):
        r = ReviewSchema(
            verdict=Verdict.PASS,
            design_conformity=DesignConformity(conforms=True),
        )
        data = r.model_dump()
        assert data["verdict"] == "pass"
