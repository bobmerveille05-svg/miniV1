import json
from pathlib import Path
import pytest
from minilegion.core.test_runner import detect_test_command


def test_detect_from_pyproject_pytest(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    cmd = detect_test_command(tmp_path)
    assert cmd == ["python", "-m", "pytest"]


def test_detect_from_pyproject_scripts(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\n\n[tool.hatch.envs.default.scripts]\ntest = "pytest tests/"\n'
    )
    cmd = detect_test_command(tmp_path)
    assert cmd == ["python", "-m", "pytest"]


def test_detect_from_package_json(tmp_path):
    pkg = {"scripts": {"test": "jest --coverage"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmd = detect_test_command(tmp_path)
    assert cmd == ["npm", "test"]


def test_detect_returns_none_when_nothing_found(tmp_path):
    cmd = detect_test_command(tmp_path)
    assert cmd is None


def test_detect_from_makefile(tmp_path):
    (tmp_path / "Makefile").write_text("test:\n\tpytest tests/\n")
    cmd = detect_test_command(tmp_path)
    assert cmd == ["make", "test"]


def test_detect_prefers_pyproject_over_package_json(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    pkg = {"scripts": {"test": "jest"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmd = detect_test_command(tmp_path)
    assert cmd == ["python", "-m", "pytest"]


def test_detect_from_pyproject_with_pytest_in_deps(tmp_path):
    """Even if pytest only appears in dependencies, detect it as python -m pytest."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\n[project.optional-dependencies]\ntest = ["pytest>=7.0"]\n'
    )
    cmd = detect_test_command(tmp_path)
    assert cmd == ["python", "-m", "pytest"]


def test_detect_from_malformed_package_json_returns_none(tmp_path):
    (tmp_path / "package.json").write_text("not valid json {{{")
    cmd = detect_test_command(tmp_path)
    assert cmd is None


def test_detect_from_makefile_with_crlf(tmp_path):
    """Makefile with Windows-style CRLF line endings should still be detected."""
    (tmp_path / "Makefile").write_bytes(b"test:\r\n\tpytest tests/\r\n")
    cmd = detect_test_command(tmp_path)
    assert cmd == ["make", "test"]
