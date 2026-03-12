"""Git integration for MiniLegion — branch management, per-task commits, PR support.

All git operations use stdlib subprocess. No third-party git libraries required.
Raises GitError (a MiniLegionError subclass) on all failures.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from minilegion.core.exceptions import MiniLegionError


class GitError(MiniLegionError):
    """Raised when a git operation fails."""


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`. Raises GitError on non-zero exit if check=True."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )
    return result


def is_git_repo(path: Path) -> bool:
    """Return True if `path` is inside a git working tree."""
    path = path.resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def get_current_branch(repo_root: Path) -> str:
    """Return the name of the currently checked-out branch."""
    result = _git(["branch", "--show-current"], cwd=repo_root)
    return result.stdout.strip()


def ensure_feature_branch(repo_root: Path, project_name: str) -> str | None:
    """Ensure we are on a minilegion feature branch.

    - If not in a git repo: returns None silently.
    - If already on a minilegion/* branch: stay, return current branch name.
    - Otherwise: create and checkout minilegion/<project_name>-<timestamp>.

    Returns the branch name (or None if not a git repo).
    """
    if not is_git_repo(repo_root):
        return None

    current = get_current_branch(repo_root)
    if current.startswith("minilegion/"):
        return current

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    branch_name = f"minilegion/{project_name}-{timestamp}"
    _git(["checkout", "-b", branch_name], cwd=repo_root)
    return branch_name


def commit_task(
    repo_root: Path,
    task_id: str,
    task_name: str,
    changed_files: list[str],
    artifact_files: list[str],
) -> None:
    """Stage and commit files for a completed task.

    - `changed_files`: source files touched by the task (paths relative to repo_root).
    - `artifact_files`: project-ai/* artifacts to include as audit trail.
    - If not in a git repo: no-op.
    - If nothing to stage: no-op (avoids 'nothing to commit' error).
    """
    if not is_git_repo(repo_root):
        return

    files_to_stage = [f for f in changed_files + artifact_files if f]
    if not files_to_stage:
        return

    existing = [f for f in files_to_stage if (repo_root / f).exists()]
    if not existing:
        return

    _git(["add", *existing], cwd=repo_root)

    status = _git(["diff", "--cached", "--name-only"], cwd=repo_root)
    if not status.stdout.strip():
        return

    message = f"feat(execute): {task_id} — {task_name}"
    _git(["commit", "-m", message], cwd=repo_root)
