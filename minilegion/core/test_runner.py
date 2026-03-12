"""Auto-test detection and execution for MiniLegion.

Detects test commands from project config files and runs them after execute.
Raises no exceptions on test failure — returns a TestResult with success=False.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestResult:
    """Result of a test run."""

    success: bool
    command: list[str]
    output: str  # combined stdout + stderr
    exit_code: int
    skipped: bool = False  # True when no test command was detected


def detect_test_command(project_root: Path) -> list[str] | None:
    """Return the test command to run, or None if none can be detected.

    Detection order (first match wins):
    1. pyproject.toml with [tool.pytest.ini_options] → python -m pytest
    2. pyproject.toml with [tool.hatch...] or any mention of pytest → python -m pytest
    3. package.json with scripts.test → npm test
    4. Makefile with a 'test:' target → make test
    """
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8", errors="replace")
        if "[tool.pytest" in content or "pytest" in content.lower():
            return ["python", "-m", "pytest"]

    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if data.get("scripts", {}).get("test"):
                return ["npm", "test"]
        except (json.JSONDecodeError, KeyError):
            pass

    makefile = project_root / "Makefile"
    if makefile.exists():
        content = makefile.read_text(encoding="utf-8", errors="replace")
        if "\ntest:" in content or content.startswith("test:"):
            return ["make", "test"]

    return None
