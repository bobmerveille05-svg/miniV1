"""Unit tests for scope lock and path normalization.

Tests GUARD-04 (scope lock) and GUARD-05 (path normalization).
"""

import sys

import pytest

from minilegion.core.exceptions import ValidationError
from minilegion.core.scope_lock import check_scope, normalize_path, validate_scope


class TestNormalizePath:
    """GUARD-05: Path normalization before scope comparison."""

    def test_resolves_dot_slash_prefix(self):
        """./src/foo.py normalizes to src/foo.py."""
        assert normalize_path("./src/foo.py") == "src/foo.py"

    def test_strips_trailing_slash(self):
        """src/foo.py/ normalizes to src/foo.py."""
        assert normalize_path("src/foo.py/") == "src/foo.py"

    def test_strips_trailing_backslash(self):
        r"""src/foo.py\ normalizes to src/foo.py."""
        assert normalize_path("src/foo.py\\") == "src/foo.py"

    def test_normalizes_backslashes(self):
        r"""src\foo\bar.py normalizes to src/foo/bar.py."""
        assert normalize_path("src\\foo\\bar.py") == "src/foo/bar.py"

    def test_no_change_clean_path(self):
        """Already-clean path is returned unchanged."""
        assert normalize_path("src/foo.py") == "src/foo.py"

    def test_empty_string(self):
        """Empty string normalizes to empty string."""
        assert normalize_path("") == ""

    def test_combined_issues(self):
        r"""./src\foo/bar/ handles multiple normalization issues."""
        result = normalize_path("./src\\foo/bar/")
        assert result == "src/foo/bar"

    def test_dot_backslash_prefix(self):
        r""".\src\foo.py normalizes correctly."""
        result = normalize_path(".\\src\\foo.py")
        # On Windows: src/foo.py (lowercased: src/foo.py)
        assert result == "src/foo.py"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_windows_lowercase(self):
        """On Windows, paths are lowercased for case-insensitive comparison."""
        assert normalize_path("SRC/Foo.py") == "src/foo.py"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_windows_mixed_case_backslash(self):
        r"""On Windows, SRC\Foo\Bar.py normalizes to src/foo/bar.py."""
        assert normalize_path("SRC\\Foo\\Bar.py") == "src/foo/bar.py"


class TestCheckScope:
    """GUARD-04: Scope lock enforcement."""

    def test_all_in_scope(self):
        """All changed files within allowed set returns empty list."""
        result = check_scope(["a.py", "b.py"], ["a.py", "b.py", "c.py"])
        assert result == []

    def test_out_of_scope_detected(self):
        """Out-of-scope file is returned in violations list."""
        result = check_scope(["a.py", "x.py"], ["a.py", "b.py"])
        assert result == ["x.py"]

    def test_empty_changed_files(self):
        """Empty changed files list returns empty violations."""
        result = check_scope([], ["a.py"])
        assert result == []

    def test_paths_normalized_before_comparison(self):
        """./src/a.py matches src/a.py after normalization."""
        result = check_scope(["./src/a.py"], ["src/a.py"])
        assert result == []

    def test_backslash_normalization_in_scope(self):
        r"""src\a.py matches src/a.py after normalization."""
        result = check_scope(["src\\a.py"], ["src/a.py"])
        assert result == []

    def test_validate_scope_raises_on_violation(self):
        """validate_scope raises ValidationError when files out of scope."""
        with pytest.raises(ValidationError, match="Out-of-scope"):
            validate_scope(["x.py"], ["a.py"])

    def test_validate_scope_passes_when_clean(self):
        """validate_scope does not raise when all files in scope."""
        # Should not raise
        validate_scope(["a.py"], ["a.py"])

    def test_returns_original_paths_not_normalized(self):
        """Out-of-scope results use original (un-normalized) path strings."""
        result = check_scope(["./x.py", "a.py"], ["a.py"])
        assert result == ["./x.py"]

    def test_multiple_out_of_scope(self):
        """Multiple out-of-scope files are all returned."""
        result = check_scope(["x.py", "y.py", "a.py"], ["a.py"])
        assert result == ["x.py", "y.py"]
