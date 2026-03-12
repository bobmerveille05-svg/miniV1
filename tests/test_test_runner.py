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


from unittest.mock import patch, MagicMock
from minilegion.core.test_runner import run_tests, TestResult


def test_run_tests_returns_skipped_when_no_command(tmp_path):
    result = run_tests(tmp_path, timeout=30)
    assert result.skipped is True
    assert result.success is True  # skipped = not a failure


def test_run_tests_returns_success_on_zero_exit(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "5 passed"
    mock_result.stderr = ""
    with patch("minilegion.core.test_runner.subprocess.run", return_value=mock_result):
        result = run_tests(tmp_path, timeout=30)
    assert result.success is True
    assert result.exit_code == 0
    assert "5 passed" in result.output
    assert result.skipped is False


def test_run_tests_returns_failure_on_nonzero_exit(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = "1 failed"
    mock_result.stderr = "AssertionError"
    with patch("minilegion.core.test_runner.subprocess.run", return_value=mock_result):
        result = run_tests(tmp_path, timeout=30)
    assert result.success is False
    assert result.exit_code == 1
    assert "1 failed" in result.output


def test_run_tests_respects_custom_command(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "ok"
    mock_result.stderr = ""
    with patch(
        "minilegion.core.test_runner.subprocess.run", return_value=mock_result
    ) as mock_run:
        run_tests(tmp_path, timeout=30, command_override=["make", "test"])
    call_args = mock_run.call_args[0][0]
    assert call_args == ["make", "test"]


def test_run_tests_truncates_long_output(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    long_output = "x" * 20_000
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = long_output
    mock_result.stderr = ""
    with patch("minilegion.core.test_runner.subprocess.run", return_value=mock_result):
        result = run_tests(tmp_path, timeout=30)
    assert len(result.output) <= 10_100  # 10k chars + truncation notice
