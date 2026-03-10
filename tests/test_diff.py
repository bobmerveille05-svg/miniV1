"""Tests for the diff text generator."""

from __future__ import annotations

from minilegion.core.diff import generate_diff_text, _MAX_CONTENT_LINES
from minilegion.core.schemas import ChangedFile, ExecutionLogSchema, TaskResult


def _make_log(*changed_files_per_task: list[ChangedFile]) -> ExecutionLogSchema:
    tasks = [
        TaskResult(task_id=f"T{i + 1}", changed_files=cfs)
        for i, cfs in enumerate(changed_files_per_task)
    ]
    return ExecutionLogSchema(tasks=tasks)


class TestGenerateDiffText:
    def test_contains_file_paths(self):
        log = _make_log(
            [ChangedFile(path="src/foo.py", action="create", content="x = 1\n")]
        )
        result = generate_diff_text(log)
        assert "src/foo.py" in result

    def test_create_action_shows_content(self):
        log = _make_log(
            [
                ChangedFile(
                    path="src/bar.py", action="create", content="def bar(): pass\n"
                )
            ]
        )
        result = generate_diff_text(log)
        assert "def bar(): pass" in result

    def test_delete_action_shows_deleted_label(self):
        log = _make_log([ChangedFile(path="old.py", action="delete", content="")])
        result = generate_diff_text(log)
        assert "DELETE" in result
        assert "old.py" in result
        assert "[File deleted]" in result

    def test_empty_log_returns_placeholder(self):
        log = ExecutionLogSchema(tasks=[])
        result = generate_diff_text(log)
        assert result == "(no changes recorded)"

    def test_long_content_is_truncated(self):
        long_content = "\n".join(f"line {i}" for i in range(_MAX_CONTENT_LINES + 50))
        log = _make_log(
            [ChangedFile(path="big.py", action="modify", content=long_content)]
        )
        result = generate_diff_text(log)
        assert "truncated" in result
        assert f"{50} more lines truncated" in result
