"""Tests for minilegion.core.registry — schema registry with validation."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from minilegion.core.registry import (
    SCHEMA_REGISTRY,
    get_json_schema,
    get_schema,
    validate,
)
from minilegion.core.schemas import (
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    ResearchSchema,
    ReviewSchema,
    Verdict,
)
from minilegion.core.schemas import DesignConformity
from minilegion.core.state import ProjectState


# All 6 artifact names
ARTIFACT_NAMES = ["research", "design", "plan", "execution_log", "review", "state"]

EXPECTED_CLASSES = {
    "research": ResearchSchema,
    "design": DesignSchema,
    "plan": PlanSchema,
    "execution_log": ExecutionLogSchema,
    "review": ReviewSchema,
    "state": ProjectState,
}


class TestSchemaRegistry:
    """SCHEMA_REGISTRY maps all 6 artifact names to model classes."""

    def test_registry_has_six_entries(self):
        assert len(SCHEMA_REGISTRY) == 6

    @pytest.mark.parametrize("name", ARTIFACT_NAMES)
    def test_registry_contains_all_artifacts(self, name):
        assert name in SCHEMA_REGISTRY

    @pytest.mark.parametrize("name", ARTIFACT_NAMES)
    def test_registry_maps_to_correct_class(self, name):
        assert SCHEMA_REGISTRY[name] is EXPECTED_CLASSES[name]


class TestGetSchema:
    """get_schema() returns model class or raises KeyError."""

    @pytest.mark.parametrize("name", ARTIFACT_NAMES)
    def test_returns_correct_class(self, name):
        assert get_schema(name) is EXPECTED_CLASSES[name]

    def test_unknown_name_raises_key_error(self):
        with pytest.raises(KeyError) as exc_info:
            get_schema("unknown")
        # Error message should list valid names
        error_msg = str(exc_info.value)
        assert "research" in error_msg
        assert "design" in error_msg


class TestGetJsonSchema:
    """get_json_schema() returns valid JSON Schema dict."""

    @pytest.mark.parametrize("name", ARTIFACT_NAMES)
    def test_returns_dict_with_type_object(self, name):
        schema = get_json_schema(name)
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"

    @pytest.mark.parametrize("name", ARTIFACT_NAMES)
    def test_returns_dict_with_properties(self, name):
        schema = get_json_schema(name)
        assert "properties" in schema


class TestValidate:
    """validate() accepts str and dict input, returns model instance."""

    def test_validate_dict_input(self):
        result = validate("research", {"project_overview": "test"})
        assert isinstance(result, ResearchSchema)
        assert result.project_overview == "test"

    def test_validate_str_input(self):
        import json

        data = json.dumps({"project_overview": "test from json"})
        result = validate("research", data)
        assert isinstance(result, ResearchSchema)
        assert result.project_overview == "test from json"

    def test_validate_invalid_data_raises(self):
        """Missing required field raises pydantic ValidationError."""
        with pytest.raises(PydanticValidationError):
            validate("research", {"bad_field": True})

    def test_validate_unknown_schema_raises_key_error(self):
        with pytest.raises(KeyError):
            validate("unknown", {"data": True})

    def test_validate_state_dict(self):
        result = validate("state", {"current_stage": "init"})
        assert isinstance(result, ProjectState)

    def test_validate_state_str(self):
        import json

        data = json.dumps({"current_stage": "brief"})
        result = validate("state", data)
        assert isinstance(result, ProjectState)
        assert result.current_stage == "brief"

    def test_validate_design_dict(self):
        result = validate(
            "design",
            {
                "design_approach": "Modular",
                "test_strategy": "pytest",
            },
        )
        assert isinstance(result, DesignSchema)

    def test_validate_plan_dict(self):
        result = validate(
            "plan",
            {
                "objective": "Build it",
                "design_ref": "ref",
                "test_plan": "pytest",
            },
        )
        assert isinstance(result, PlanSchema)

    def test_validate_execution_log_dict(self):
        result = validate("execution_log", {})
        assert isinstance(result, ExecutionLogSchema)

    def test_validate_review_dict(self):
        result = validate(
            "review",
            {
                "verdict": "pass",
                "design_conformity": {"conforms": True},
            },
        )
        assert isinstance(result, ReviewSchema)
