"""Shared test fixtures for MiniLegion tests."""

import json

import pytest

from minilegion.core.state import APPROVAL_KEYS


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create a temp directory simulating a project root with project-ai/ subdirectory."""
    project_ai = tmp_path / "project-ai"
    project_ai.mkdir()
    return tmp_path


@pytest.fixture
def sample_config_json():
    """Return a valid minilegion.config.json string with custom values."""
    return json.dumps(
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
            "timeout": 60,
            "max_retries": 3,
            "engines": {"researcher": "gpt-4o"},
        }
    )


@pytest.fixture
def default_approvals():
    """Return dict with all approval keys set to False."""
    return {key: False for key in APPROVAL_KEYS}


@pytest.fixture
def all_approved():
    """Return dict with all approval keys set to True."""
    return {key: True for key in APPROVAL_KEYS}
