"""Tests for minilegion/core/patcher.py — apply_patch()."""

from __future__ import annotations

from pathlib import Path

import pytest

from minilegion.core.patcher import apply_patch
from minilegion.core.schemas import ChangedFile


class TestApplyPatch:
    def test_apply_patch_create_writes_file(self, tmp_path):
        cf = ChangedFile(
            path="src/new_file.py", action="create", content="print('hello')\n"
        )
        apply_patch(cf, tmp_path)
        assert (tmp_path / "src" / "new_file.py").read_text() == "print('hello')\n"

    def test_apply_patch_modify_overwrites_file(self, tmp_path):
        target = tmp_path / "src" / "existing.py"
        target.parent.mkdir(parents=True)
        target.write_text("old content\n")
        cf = ChangedFile(
            path="src/existing.py", action="modify", content="new content\n"
        )
        apply_patch(cf, tmp_path)
        assert target.read_text() == "new content\n"

    def test_apply_patch_delete_removes_file(self, tmp_path):
        target = tmp_path / "src" / "to_delete.py"
        target.parent.mkdir(parents=True)
        target.write_text("doomed\n")
        cf = ChangedFile(path="src/to_delete.py", action="delete", content="")
        apply_patch(cf, tmp_path)
        assert not target.exists()

    def test_apply_patch_delete_missing_file_noop(self, tmp_path):
        """Deleting a non-existent file must not raise."""
        cf = ChangedFile(path="src/ghost.py", action="delete", content="")
        apply_patch(cf, tmp_path)  # should not raise

    def test_apply_patch_dry_run_create_no_file_written(self, tmp_path):
        cf = ChangedFile(path="src/new.py", action="create", content="x = 1\n")
        apply_patch(cf, tmp_path, dry_run=True)
        assert not (tmp_path / "src" / "new.py").exists()

    def test_apply_patch_dry_run_delete_no_file_removed(self, tmp_path):
        target = tmp_path / "keep.py"
        target.write_text("keep me\n")
        cf = ChangedFile(path="keep.py", action="delete", content="")
        apply_patch(cf, tmp_path, dry_run=True)
        assert target.exists()

    def test_apply_patch_returns_description(self, tmp_path):
        cf = ChangedFile(path="foo.py", action="create", content="line1\nline2\n")
        desc = apply_patch(cf, tmp_path)
        assert "foo.py" in desc
        assert "CREATE" in desc

    def test_apply_patch_creates_parent_dirs(self, tmp_path):
        cf = ChangedFile(
            path="a/b/c/deep.py", action="create", content="deep content\n"
        )
        apply_patch(cf, tmp_path)
        assert (tmp_path / "a" / "b" / "c" / "deep.py").exists()
