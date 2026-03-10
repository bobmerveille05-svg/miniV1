"""Patch application module for MiniLegion.

Applies ChangedFile patches to the filesystem (BUILD-04).

Supports three actions:
- create: Write new file with content (atomic).
- modify: Overwrite existing file with content (atomic).
- delete: Remove file from disk.

Dry-run mode returns the same description without touching files.
"""

from __future__ import annotations

from pathlib import Path

from minilegion.core.file_io import write_atomic
from minilegion.core.schemas import ChangedFile


def apply_patch(
    changed_file: ChangedFile,
    project_root: Path,
    dry_run: bool = False,
) -> str:
    """Apply a single file patch to the filesystem.

    Args:
        changed_file: The patch to apply (path, action, content).
        project_root: Root directory for resolving relative paths.
        dry_run: If True, return description without modifying files.

    Returns:
        Human-readable description of the change (used for display/approval).
    """
    project_root = Path(project_root)
    target = project_root / changed_file.path

    if changed_file.action == "delete":
        description = f"DELETE {changed_file.path}"
        if not dry_run:
            if target.exists():
                target.unlink()
        return description

    # create or modify
    action_label = changed_file.action.upper()
    line_count = len(changed_file.content.splitlines())
    description = f"{action_label} {changed_file.path} ({line_count} lines)"

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, changed_file.content)

    return description
