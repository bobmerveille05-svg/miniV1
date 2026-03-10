"""Diff text generator for MiniLegion review stage.

Converts an ExecutionLogSchema into a human-readable diff summary
suitable for the reviewer LLM prompt {{diff_text}} placeholder.
"""

from __future__ import annotations

from pathlib import Path

from minilegion.core.schemas import ExecutionLogSchema

_MAX_CONTENT_LINES = 200


def generate_diff_text(
    execution_log: ExecutionLogSchema,
    project_dir: Path | None = None,
) -> str:
    """Generate a human-readable diff summary from an execution log.

    For each changed file across all tasks, produces a labelled block
    showing the action (CREATE / MODIFY / DELETE) and file content
    (truncated at _MAX_CONTENT_LINES lines for large files).

    Args:
        execution_log: The parsed execution log from the execute stage.
        project_dir: Unused — reserved for future on-disk diff generation.

    Returns:
        Formatted multi-line string for the reviewer prompt. Returns a
        ``"(no changes recorded)"`` placeholder when the log is empty.
    """
    if not execution_log.tasks:
        return "(no changes recorded)"

    parts: list[str] = []

    for task_result in execution_log.tasks:
        parts.append(f"### Task: {task_result.task_id}\n")

        if not task_result.changed_files:
            parts.append("  (no files changed)\n")
            continue

        for cf in task_result.changed_files:
            action_label = cf.action.upper()
            parts.append(f"\n#### {action_label}: {cf.path}\n")

            if cf.action == "delete":
                parts.append("  [File deleted]\n")
                continue

            # create or modify — show content, capped at _MAX_CONTENT_LINES
            lines = cf.content.splitlines()
            total = len(lines)
            truncated = lines[:_MAX_CONTENT_LINES]
            parts.append("```\n")
            parts.append("\n".join(truncated))
            if total > _MAX_CONTENT_LINES:
                parts.append(
                    f"\n... [{total - _MAX_CONTENT_LINES} more lines truncated]\n"
                )
            parts.append("\n```\n")

    return "".join(parts)
