"""Context scanner — produces a human-readable codebase summary for LLM prompt injection."""

from __future__ import annotations

import os
import re
from pathlib import Path

from minilegion.core.config import MiniLegionConfig

IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}

TECH_STACK_FILES = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
]

# Import extraction regexes (RSCH-03)
PYTHON_IMPORT_RE = re.compile(
    r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))",
    re.MULTILINE,
)
JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)
GO_IMPORT_RE = re.compile(
    r'import\s+(?:"([^"]+)"|(?:\(\s*((?:[^)]*"[^"]*"[^)]*)*)\s*\)))',
    re.MULTILINE | re.DOTALL,
)

# Naming convention regexes (RSCH-04)
SNAKE_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
CAMEL_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b")
PASCAL_CASE_RE = re.compile(r"\b[A-Z][a-zA-Z0-9]+\b")

SOURCE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
}


def _scan_tech_stack(project_dir: Path) -> str:
    """Detect tech stack from root-level config files."""
    found = []
    for filename in TECH_STACK_FILES:
        fpath = project_dir / filename
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                found.append((filename, content))
            except OSError:
                found.append((filename, "(unreadable)"))
    if not found:
        return "## Tech Stack\n\nNo tech stack config files found."
    sections = "\n\n".join(
        f"### {fn}\n\n```\n{content[:500]}\n```" for fn, content in found
    )
    return "## Tech Stack\n\n" + sections


def _scan_directory_structure(project_dir: Path, max_depth: int) -> str:
    """Build directory tree (max 2 levels, filtered)."""
    lines = [f"{project_dir.name}/"]
    display_depth = min(2, max_depth)  # Never show more than 2 levels for structure

    for dirpath, dirs, files in os.walk(project_dir):
        depth = len(Path(dirpath).relative_to(project_dir).parts)
        dirs[:] = [d for d in sorted(dirs) if d not in IGNORED_DIRS]
        if depth >= display_depth:
            dirs[:] = []
        indent = "  " * (depth + 1)
        for d in dirs:
            lines.append(f"{indent}{d}/")
        for f in sorted(files)[:10]:  # Limit files listed per dir
            lines.append(f"{indent}{f}")

    return "## Directory Structure\n\n```\n" + "\n".join(lines) + "\n```"


def _collect_files(
    project_dir: Path, config: MiniLegionConfig
) -> list[tuple[Path, str]]:
    """Collect source files respecting depth/count/size limits."""
    collected: list[tuple[Path, str]] = []
    size_limit = config.scan_max_file_size_kb * 1024

    for dirpath, dirs, files in os.walk(project_dir):
        depth = len(Path(dirpath).relative_to(project_dir).parts)
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        if depth >= config.scan_max_depth:
            dirs[:] = []

        for fname in sorted(files):
            # Check count BEFORE reading (Pitfall 7)
            if len(collected) >= config.scan_max_files:
                break
            fpath = Path(dirpath) / fname
            try:
                if fpath.stat().st_size > size_limit:
                    continue
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            collected.append((fpath, content))

    return collected


def _scan_imports(files: list[tuple[Path, str]]) -> str:
    """Extract imports from collected source files, grouped by language."""
    imports_by_lang: dict[str, set[str]] = {
        "Python": set(),
        "JavaScript/TypeScript": set(),
        "Go": set(),
    }

    for fpath, content in files:
        suffix = fpath.suffix.lower()
        lang = SOURCE_EXTENSIONS.get(suffix)
        if lang is None:
            continue

        if lang == "python":
            for m in PYTHON_IMPORT_RE.finditer(content):
                # Group 1: from X import  /  Group 2: import X
                val = m.group(1) or m.group(2)
                if val:
                    # Split comma-separated multi-imports: "import os, sys"
                    for part in val.split(","):
                        part = part.strip()
                        if part:
                            imports_by_lang["Python"].add(part)
        elif lang in ("javascript", "typescript"):
            for m in JS_IMPORT_RE.finditer(content):
                val = m.group(1) or m.group(2)
                if val:
                    imports_by_lang["JavaScript/TypeScript"].add(val)
        elif lang == "go":
            for m in GO_IMPORT_RE.finditer(content):
                single = m.group(1)
                block = m.group(2)
                if single:
                    imports_by_lang["Go"].add(single)
                elif block:
                    # Extract individual quoted strings from the block
                    for pkg in re.findall(r'"([^"]+)"', block):
                        imports_by_lang["Go"].add(pkg)

    sections = []
    for lang_label, pkgs in imports_by_lang.items():
        if pkgs:
            items = "\n".join(f"- {p}" for p in sorted(pkgs))
            sections.append(f"### {lang_label}\n\n{items}")

    if not sections:
        return "## Import Patterns\n\nNo imports detected."
    return "## Import Patterns\n\n" + "\n\n".join(sections)


def _scan_naming_conventions(files: list[tuple[Path, str]]) -> str:
    """Detect dominant naming convention across source files."""
    counts = {"snake_case": 0, "camelCase": 0, "PascalCase": 0}

    for fpath, content in files:
        if fpath.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        counts["snake_case"] += len(SNAKE_CASE_RE.findall(content))
        counts["camelCase"] += len(CAMEL_CASE_RE.findall(content))
        counts["PascalCase"] += len(PASCAL_CASE_RE.findall(content))

    if all(v == 0 for v in counts.values()):
        return "## Naming Conventions\n\nNo naming patterns detected."

    dominant = max(counts, key=lambda k: counts[k])
    return (
        f"## Naming Conventions\n\n"
        f"Dominant style: {dominant}\n"
        f"(snake_case: {counts['snake_case']}, "
        f"camelCase: {counts['camelCase']}, "
        f"PascalCase: {counts['PascalCase']})"
    )


def scan_codebase(project_dir: Path, config: MiniLegionConfig) -> str:
    """Scan codebase and return formatted text blob for LLM prompt injection.

    Args:
        project_dir: Root directory of the project to scan.
        config: MiniLegionConfig with scanner limit settings.

    Returns:
        Non-empty string with structured sections for LLM consumption.
    """
    parts = []
    parts.append(_scan_tech_stack(project_dir))
    parts.append(_scan_directory_structure(project_dir, config.scan_max_depth))
    files = _collect_files(project_dir, config)
    parts.append(_scan_imports(files))
    parts.append(_scan_naming_conventions(files))
    return "\n\n".join(p for p in parts if p)
