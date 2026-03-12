"""Append-only history event storage for MiniLegion projects."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from minilegion.core.file_io import write_atomic


_INDEX_PATTERN = re.compile(r"^(\d+)_")
_SAFE_EVENT_PATTERN = re.compile(r"[^a-z0-9]+")


class HistoryEvent(BaseModel):
    """Canonical history event payload persisted under project-ai/history/."""

    event_type: str
    stage: str
    timestamp: str
    actor: str = "system"
    tool_used: str = "minilegion"
    notes: str = ""


def _history_dir(project_dir: Path) -> Path:
    return project_dir / "history"


def _safe_event_suffix(event_type: str) -> str:
    normalized = _SAFE_EVENT_PATTERN.sub("_", event_type.lower()).strip("_")
    return normalized or "event"


def _next_index(history_dir: Path) -> int:
    max_index = 0
    for path in history_dir.glob("*.json"):
        match = _INDEX_PATTERN.match(path.stem)
        if not match:
            continue
        value = int(match.group(1))
        if value > max_index:
            max_index = value
    return max_index + 1


def append_event(project_dir: Path, event: HistoryEvent) -> Path:
    """Append a history event file with a monotonic numeric prefix."""
    history_dir = _history_dir(Path(project_dir))
    history_dir.mkdir(parents=True, exist_ok=True)

    index = _next_index(history_dir)
    suffix = _safe_event_suffix(event.event_type)
    event_path = history_dir / f"{index:03d}_{suffix}.json"
    write_atomic(event_path, event.model_dump_json(indent=2))
    return event_path


def read_history(project_dir: Path) -> list[HistoryEvent]:
    """Read and return history events sorted by numeric filename prefix."""
    history_dir = _history_dir(Path(project_dir))
    if not history_dir.exists():
        return []

    ordered_paths: list[tuple[int, Path]] = []
    for path in history_dir.glob("*.json"):
        match = _INDEX_PATTERN.match(path.stem)
        if not match:
            continue
        ordered_paths.append((int(match.group(1)), path))

    events: list[HistoryEvent] = []
    for _, path in sorted(ordered_paths, key=lambda item: item[0]):
        try:
            payload = path.read_text(encoding="utf-8")
            events.append(HistoryEvent.model_validate_json(payload))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
    return events
