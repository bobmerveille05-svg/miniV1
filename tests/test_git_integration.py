import subprocess
from unittest.mock import patch
import pytest
from minilegion.core.git_integration import is_git_repo, GitError


def test_is_git_repo_true_when_git_dir_exists(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    assert is_git_repo(tmp_path) is True


@patch("minilegion.core.git_integration.subprocess.run")
def test_is_git_repo_false_when_not_a_repo(mock_run):
    mock_run.return_value = type(
        "MockResult",
        (),
        {"returncode": 128, "stdout": "", "stderr": "not a git repository"},
    )()
    from pathlib import Path

    assert is_git_repo(Path("/some/nonexistent/path")) is False


def test_git_error_is_exception():
    with pytest.raises(GitError):
        raise GitError("something went wrong")
