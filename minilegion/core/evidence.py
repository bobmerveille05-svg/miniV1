"""Validation evidence read/write helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from minilegion.core.file_io import write_atomic


class ValidationEvidence(BaseModel):
    """Machine-readable evidence payload for a validation step."""

    step: str
    status: Literal["pass", "fail"]
    checks_passed: list[str]
    validator: str
    tool_used: str
    date: str
    notes: str = ""


def _evidence_path(project_dir: Path, step: str) -> Path:
    return Path(project_dir) / "evidence" / f"{step}.validation.json"


def write_evidence(project_dir: Path, evidence: ValidationEvidence) -> Path:
    """Write per-step validation evidence atomically."""
    target = _evidence_path(project_dir, evidence.step)
    write_atomic(target, evidence.model_dump_json())
    return target


def read_evidence(project_dir: Path, step: str) -> ValidationEvidence | None:
    """Read per-step validation evidence, returning None if missing."""
    target = _evidence_path(project_dir, step)
    if not target.exists():
        return None
    return ValidationEvidence.model_validate_json(target.read_text(encoding="utf-8"))
