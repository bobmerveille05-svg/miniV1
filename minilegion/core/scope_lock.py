"""Scope lock and path normalization for MiniLegion.

Enforces GUARD-04 (scope lock) and GUARD-05 (path normalization):
- normalize_path(): Canonicalizes paths for cross-platform comparison
- check_scope(): Returns list of out-of-scope files
- validate_scope(): Raises ValidationError on scope violations

Path normalization handles:
- ./ and .\\ prefix removal
- Trailing slash/backslash stripping
- Backslash → forward slash conversion
- Windows case-insensitive lowering (sys.platform == "win32")

Does NOT use os.path.normpath() which converts to backslashes on Windows.
"""

import sys

from minilegion.core.exceptions import ValidationError


def normalize_path(path: str) -> str:
    """Normalize a file path for consistent scope comparison.

    Handles: ./ prefix, .\\ prefix, trailing slashes, backslashes,
    and Windows case-insensitive lowering.

    Args:
        path: Raw file path string.

    Returns:
        Normalized path with forward slashes only.
    """
    if not path:
        return path

    # Remove ./ prefix
    if path.startswith("./"):
        path = path[2:]
    # Remove .\\ prefix
    elif path.startswith(".\\"):
        path = path[2:]

    # Strip trailing slashes and backslashes
    path = path.rstrip("/\\")

    # Normalize backslashes to forward slashes
    path = path.replace("\\", "/")

    # Lowercase on Windows for case-insensitive comparison
    if sys.platform == "win32":
        path = path.lower()

    return path


def check_scope(changed_files: list[str], allowed_files: list[str]) -> list[str]:
    """Check which changed files are outside the allowed scope.

    Both changed_files and allowed_files are normalized before comparison.
    Returns original (un-normalized) paths for out-of-scope files.

    Args:
        changed_files: List of file paths that were changed.
        allowed_files: List of file paths that are allowed.

    Returns:
        List of original changed_files entries that are not in scope.
    """
    allowed_set = {normalize_path(f) for f in allowed_files}
    return [f for f in changed_files if normalize_path(f) not in allowed_set]


def validate_scope(changed_files: list[str], allowed_files: list[str]) -> None:
    """Validate that all changed files are within the allowed scope.

    Args:
        changed_files: List of file paths that were changed.
        allowed_files: List of file paths that are allowed.

    Raises:
        ValidationError: If any changed file is outside the allowed scope.
    """
    out_of_scope = check_scope(changed_files, allowed_files)
    if out_of_scope:
        raise ValidationError(f"Out-of-scope files: {out_of_scope}")
