"""Git integration for MiniLegion — branch management, per-task commits, PR support.

All git operations use stdlib subprocess. No third-party git libraries required.
Raises GitError (a MiniLegionError subclass) on all failures.
"""

from __future__ import annotations

import subprocess
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
