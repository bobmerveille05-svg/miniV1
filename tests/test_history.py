"""Tests for minilegion.core.history and legacy migration behavior."""

from __future__ import annotations

import json

from minilegion.core.history import HistoryEvent, append_event, read_history
from minilegion.core.state import load_state


class TestAppendEvent:
    """append_event writes deterministic indexed history files."""

    def test_append_event_writes_indexed_file_and_payload(self, tmp_path):
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir()

        event = HistoryEvent(
            event_type="review",
            stage="review",
            timestamp="2026-01-01T00:00:00",
            actor="system",
            tool_used="minilegion",
            notes="Review approved",
        )

        path = append_event(project_dir, event)
        assert path.name == "001_review.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["event_type"] == "review"
        assert payload["stage"] == "review"
        assert payload["notes"] == "Review approved"

    def test_append_event_uses_monotonic_indexing(self, tmp_path):
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir()

        first = HistoryEvent(
            event_type="brief",
            stage="brief",
            timestamp="2026-01-01T00:00:00",
            actor="system",
            tool_used="minilegion",
            notes="Brief approved",
        )
        second = HistoryEvent(
            event_type="design done",
            stage="design",
            timestamp="2026-01-01T00:01:00",
            actor="system",
            tool_used="minilegion",
            notes="Design approved",
        )

        first_path = append_event(project_dir, first)
        second_path = append_event(project_dir, second)

        assert first_path.name == "001_brief.json"
        assert second_path.name == "002_design_done.json"


class TestReadHistory:
    """read_history returns events sorted by numeric prefix."""

    def test_read_history_sorts_by_numeric_prefix_not_filesystem_order(self, tmp_path):
        project_dir = tmp_path / "project-ai"
        history_dir = project_dir / "history"
        history_dir.mkdir(parents=True)

        (history_dir / "010_archive.json").write_text(
            json.dumps(
                {
                    "event_type": "archive",
                    "stage": "archive",
                    "timestamp": "2026-01-01T00:10:00",
                    "actor": "system",
                    "tool_used": "minilegion",
                    "notes": "Archived",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (history_dir / "002_brief.json").write_text(
            json.dumps(
                {
                    "event_type": "brief",
                    "stage": "brief",
                    "timestamp": "2026-01-01T00:02:00",
                    "actor": "system",
                    "tool_used": "minilegion",
                    "notes": "Brief",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        events = read_history(project_dir)
        assert [event.event_type for event in events] == ["brief", "archive"]


class TestMigration:
    """Legacy embedded STATE history migrates to project-ai/history."""

    def test_load_state_migrates_legacy_embedded_history_and_rewrites_state(
        self, tmp_path
    ):
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir()
        state_path = project_dir / "STATE.json"
        state_path.write_text(
            json.dumps(
                {
                    "current_stage": "research",
                    "approvals": {
                        "brief_approved": True,
                        "research_approved": False,
                        "design_approved": False,
                        "plan_approved": False,
                        "execute_approved": False,
                        "review_approved": False,
                    },
                    "completed_tasks": [],
                    "history": [
                        {
                            "timestamp": "2026-01-01T00:00:00",
                            "action": "init",
                            "details": "Project initialized",
                        },
                        {
                            "timestamp": "2026-01-01T00:01:00",
                            "action": "brief",
                            "details": "Brief approved",
                        },
                    ],
                    "metadata": {},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        load_state(state_path)

        events = read_history(project_dir)
        assert [event.event_type for event in events] == ["init", "brief"]

        rewritten = json.loads(state_path.read_text(encoding="utf-8"))
        assert "history" not in rewritten

    def test_load_state_migration_is_idempotent(self, tmp_path):
        project_dir = tmp_path / "project-ai"
        project_dir.mkdir()
        state_path = project_dir / "STATE.json"
        state_path.write_text(
            json.dumps(
                {
                    "current_stage": "brief",
                    "approvals": {
                        "brief_approved": False,
                        "research_approved": False,
                        "design_approved": False,
                        "plan_approved": False,
                        "execute_approved": False,
                        "review_approved": False,
                    },
                    "completed_tasks": [],
                    "history": [
                        {
                            "timestamp": "2026-01-01T00:00:00",
                            "action": "init",
                            "details": "Project initialized",
                        }
                    ],
                    "metadata": {},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        load_state(state_path)
        load_state(state_path)

        events = read_history(project_dir)
        assert len(events) == 1
        assert events[0].event_type == "init"
