"""Schema registry for MiniLegion artifact validation.

Central mapping of artifact name → Pydantic model class, with convenience
functions for schema access and data validation.

Usage::

    from minilegion.core.registry import validate, get_schema, get_json_schema

    model = validate("research", raw_json_string)
    cls = get_schema("design")
    json_schema = get_json_schema("plan")
"""

from typing import Any, Type

from pydantic import BaseModel

from minilegion.core.schemas import (
    DesignSchema,
    ExecutionLogSchema,
    PlanSchema,
    ResearchSchema,
    ReviewSchema,
)
from minilegion.core.state import ProjectState

SCHEMA_REGISTRY: dict[str, Type[BaseModel]] = {
    "research": ResearchSchema,
    "design": DesignSchema,
    "plan": PlanSchema,
    "execution_log": ExecutionLogSchema,
    "review": ReviewSchema,
    "state": ProjectState,
}


def get_schema(artifact_name: str) -> Type[BaseModel]:
    """Return the Pydantic model class for the given artifact name.

    Args:
        artifact_name: One of the 6 registered artifact names.

    Returns:
        The Pydantic model class.

    Raises:
        KeyError: If artifact_name is not registered, with valid names listed.
    """
    try:
        return SCHEMA_REGISTRY[artifact_name]
    except KeyError:
        valid = sorted(SCHEMA_REGISTRY.keys())
        raise KeyError(
            f"Unknown artifact '{artifact_name}'. Valid names: {', '.join(valid)}"
        ) from None


def get_json_schema(artifact_name: str) -> dict:
    """Return the JSON Schema dict for the given artifact name.

    Args:
        artifact_name: One of the 6 registered artifact names.

    Returns:
        JSON Schema as a Python dict.

    Raises:
        KeyError: If artifact_name is not registered.
    """
    cls = get_schema(artifact_name)
    return cls.model_json_schema()


def validate(artifact_name: str, data: str | dict | Any) -> BaseModel:
    """Validate data against the named schema and return a model instance.

    Accepts both JSON strings and dicts. Pydantic ValidationError is NOT
    caught — it propagates to the caller (retry module handles it).

    Args:
        artifact_name: One of the 6 registered artifact names.
        data: JSON string or dict to validate.

    Returns:
        Validated Pydantic model instance.

    Raises:
        KeyError: If artifact_name is not registered.
        pydantic.ValidationError: If data fails validation.
    """
    cls = get_schema(artifact_name)
    if isinstance(data, str):
        return cls.model_validate_json(data)
    return cls.model_validate(data)
