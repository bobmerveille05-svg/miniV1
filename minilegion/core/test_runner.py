"""Auto-test detection and execution for MiniLegion.

Detects test commands from project config files and runs them after execute.
Raises no exceptions on test failure — returns a TestResult with success=False.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
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
        # Any mention of pytest in pyproject.toml (incl. dependencies) signals python test runner
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
        normalized = content.replace("\r\n", "\n")
        if "\ntest:" in normalized or normalized.startswith("test:"):
            return ["make", "test"]

    return None


_MAX_OUTPUT_CHARS = 10_000


def run_tests(
    project_root: Path,
    timeout: int = 120,
    command_override: list[str] | None = None,
) -> TestResult:
    """Run the detected (or overridden) test command.

    Returns a TestResult. Never raises on test failure — callers decide what to do.
    Output is truncated to _MAX_OUTPUT_CHARS to avoid flooding prompts.
    """
    command = command_override or detect_test_command(project_root)

    if command is None:
        return TestResult(
            success=True,
            command=[],
            output="",
            exit_code=0,
            skipped=True,
        )

    try:
        proc = subprocess.run(
            command,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            success=False,
            command=command,
            output=f"Test command timed out after {timeout}s.",
            exit_code=-1,
        )
    except FileNotFoundError as exc:
        return TestResult(
            success=False,
            command=command,
            output=f"Test command not found: {exc}",
            exit_code=-1,
        )

    raw_output = (proc.stdout or "") + (proc.stderr or "")
    if len(raw_output) > _MAX_OUTPUT_CHARS:
        raw_output = raw_output[:_MAX_OUTPUT_CHARS] + "\n[...output truncated...]"

    return TestResult(
        success=(proc.returncode == 0),
        command=command,
        output=raw_output,
        exit_code=proc.returncode,
        skipped=False,
    )
