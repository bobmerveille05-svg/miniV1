import os
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest
from minilegion.core.git_integration import (
    is_git_repo,
    get_current_branch,
    ensure_feature_branch,
    GitError,
    commit_task,
)


def test_get_current_branch(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )
    branch = get_current_branch(tmp_path)
    assert isinstance(branch, str)
    assert len(branch) > 0


def test_ensure_feature_branch_creates_new_branch(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    env = {
        **__import__("os").environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env=env,
    )
    branch = ensure_feature_branch(tmp_path, project_name="myproject")
    assert branch.startswith("minilegion/myproject-")
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == branch


def test_ensure_feature_branch_reuses_existing_minilegion_branch(tmp_path):
    """If already on a minilegion/* branch, should not create a new one."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    env = {
        **__import__("os").environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "checkout", "-b", "minilegion/myproject-20250101_120000"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    branch = ensure_feature_branch(tmp_path, project_name="myproject")
    assert branch == "minilegion/myproject-20250101_120000"


def test_ensure_feature_branch_skips_when_not_git_repo(tmp_path):
    """Returns None silently when not in a git repo."""
    with patch("minilegion.core.git_integration.is_git_repo", return_value=False):
        result = ensure_feature_branch(tmp_path, project_name="myproject")
    assert result is None


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


def _init_repo_with_commit(tmp_path: Path) -> None:
    """Helper: init a git repo with an empty initial commit."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "t"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env=env,
    )


def test_commit_task_creates_commit(tmp_path):
    _init_repo_with_commit(tmp_path)
    (tmp_path / "foo.py").write_text("x = 1")
    commit_task(
        repo_root=tmp_path,
        task_id="task-1",
        task_name="Add foo module",
        changed_files=["foo.py"],
        artifact_files=[],
    )
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert "task-1" in result.stdout
    assert "Add foo module" in result.stdout


def test_commit_task_includes_artifact_files(tmp_path):
    _init_repo_with_commit(tmp_path)
    (tmp_path / "foo.py").write_text("x = 1")
    (tmp_path / "project-ai").mkdir()
    (tmp_path / "project-ai" / "EXECUTION_LOG.json").write_text("{}")
    commit_task(
        repo_root=tmp_path,
        task_id="task-1",
        task_name="Add foo",
        changed_files=["foo.py"],
        artifact_files=["project-ai/EXECUTION_LOG.json"],
    )
    result = subprocess.run(
        ["git", "show", "--stat", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert "foo.py" in result.stdout
    assert "EXECUTION_LOG.json" in result.stdout


def test_commit_task_skips_when_nothing_to_commit(tmp_path):
    """commit_task should not raise if there are no staged changes."""
    _init_repo_with_commit(tmp_path)
    commit_task(
        repo_root=tmp_path,
        task_id="task-1",
        task_name="No-op",
        changed_files=[],
        artifact_files=[],
    )


def test_commit_task_skips_when_not_git_repo(tmp_path):
    """Should be a no-op when not in a git repo."""
    (tmp_path / "foo.py").write_text("x = 1")
    commit_task(
        repo_root=tmp_path,
        task_id="task-1",
        task_name="Add foo",
        changed_files=["foo.py"],
        artifact_files=[],
    )


def test_commit_task_skips_when_files_do_not_exist(tmp_path):
    """commit_task should be a no-op when listed files don't exist on disk."""
    _init_repo_with_commit(tmp_path)
    commit_task(
        repo_root=tmp_path,
        task_id="task-1",
        task_name="No-op",
        changed_files=["nonexistent.py"],
        artifact_files=["also_missing.json"],
    )
    # Should complete without raising or creating a commit beyond the initial one
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.stdout.count("\n") == 1  # only the initial empty commit
