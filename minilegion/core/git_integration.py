"""Git integration for MiniLegion — branch management, per-task commits, PR support.

All git operations use stdlib subprocess. No third-party git libraries required.
Raises GitError (a MiniLegionError subclass) on all failures.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from minilegion.core.exceptions import MiniLegionError

if TYPE_CHECKING:
    pass


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
