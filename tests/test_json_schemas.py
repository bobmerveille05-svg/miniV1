"""Tests for pre-generated JSON Schema files in minilegion/schemas/."""

import json
from pathlib import Path

import pytest

from minilegion.core.registry import SCHEMA_REGISTRY, get_json_schema


SCHEMA_DIR = Path(__file__).parent.parent / "minilegion" / "schemas"

SCHEMA_FILES = [
    ("research", "research.schema.json"),
    ("design", "design.schema.json"),
    ("plan", "plan.schema.json"),
    ("execution_log", "execution_log.schema.json"),
    ("review", "review.schema.json"),
    ("state", "state.schema.json"),
]


class TestJsonSchemaFilesExist:
    """All 6 .schema.json files must exist."""

    @pytest.mark.parametrize("name,filename", SCHEMA_FILES)
    def test_schema_file_exists(self, name, filename):
        path = SCHEMA_DIR / filename
        assert path.exists(), f"Missing schema file: {path}"


class TestJsonSchemaFilesValid:
    """Each .schema.json file is valid JSON with expected structure."""

    @pytest.mark.parametrize("name,filename", SCHEMA_FILES)
    def test_file_is_valid_json(self, name, filename):
        path = SCHEMA_DIR / filename
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("name,filename", SCHEMA_FILES)
    def test_file_has_type_object(self, name, filename):
        path = SCHEMA_DIR / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("type") == "object"

    @pytest.mark.parametrize("name,filename", SCHEMA_FILES)
    def test_file_has_properties(self, name, filename):
        path = SCHEMA_DIR / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "properties" in data


class TestJsonSchemaMatchesModel:
    """Each .schema.json file matches model_json_schema() output."""

    @pytest.mark.parametrize("name,filename", SCHEMA_FILES)
    def test_schema_matches_model(self, name, filename):
        path = SCHEMA_DIR / filename
        file_data = json.loads(path.read_text(encoding="utf-8"))
        model_data = get_json_schema(name)
        assert file_data == model_data, (
            f"Schema file {filename} does not match model_json_schema() for '{name}'"
        )
