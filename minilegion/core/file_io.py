"""Atomic file I/O utilities for MiniLegion.

All file writes use the atomic write pattern: write to a temp file in the
same directory, fsync, then os.replace() to atomically swap. This guarantees
that interrupted writes never corrupt existing files.
"""

import os
import tempfile
from pathlib import Path


def write_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to path atomically using temp file + os.replace().

    Guarantees: if the write is interrupted, the original file is untouched.
    The temp file is created in the same directory to ensure same-filesystem rename.

    Args:
        path: Target file path.
        content: String content to write.
        encoding: File encoding (default: utf-8).
    """
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (required for os.replace on same filesystem)
    fd, tmp_path = tempfile.mkstemp(dir=str(parent), prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data hits disk
        os.replace(tmp_path, str(path))  # Atomic on POSIX; near-atomic on Windows
    except BaseException:
        # Clean up temp file on any error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
