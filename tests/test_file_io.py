"""Tests for minilegion.core.file_io — atomic write utility."""

from unittest.mock import patch

import pytest

from minilegion.core.file_io import write_atomic


class TestWriteAtomic:
    """Test the atomic write utility."""

    def test_write_atomic_creates_file(self, tmp_path):
        """write_atomic creates a new file with correct content."""
        target = tmp_path / "test.txt"
        write_atomic(target, "hello world")
        assert target.read_text() == "hello world"

    def test_write_atomic_creates_parent_dirs(self, tmp_path):
        """write_atomic creates parent directories if they don't exist."""
        target = tmp_path / "nested" / "deep" / "test.txt"
        write_atomic(target, "nested content")
        assert target.exists()
        assert target.read_text() == "nested content"

    def test_write_atomic_overwrites_existing(self, tmp_path):
        """write_atomic replaces content of existing file."""
        target = tmp_path / "test.txt"
        write_atomic(target, "first content")
        write_atomic(target, "second content")
        assert target.read_text() == "second content"

    def test_write_atomic_no_partial_on_error(self, tmp_path):
        """If write fails mid-operation, original file is unchanged and temp is cleaned up."""
        target = tmp_path / "test.txt"
        original_content = "original content"
        target.write_text(original_content)

        # Patch os.replace to raise an error, simulating a failure
        with patch(
            "minilegion.core.file_io.os.replace", side_effect=OSError("disk full")
        ):
            with pytest.raises(OSError, match="disk full"):
                write_atomic(target, "new content that should not appear")

        # Original file should be unchanged
        assert target.read_text() == original_content

        # Temp file should be cleaned up (no .tmp files in directory)
        tmp_files = list(tmp_path.glob(".tmp_*"))
        assert len(tmp_files) == 0

    def test_write_atomic_handles_unicode(self, tmp_path):
        """write_atomic handles unicode content correctly."""
        target = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍 ñ ü ö"
        write_atomic(target, content)
        assert target.read_text(encoding="utf-8") == content
