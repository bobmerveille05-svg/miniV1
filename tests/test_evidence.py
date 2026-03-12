"""Tests for evidence read/write helpers."""

from __future__ import annotations

from minilegion.core.evidence import ValidationEvidence, read_evidence, write_evidence


class TestEvidenceIO:
    def test_write_evidence_creates_step_file_with_required_fields(self, tmp_path):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()

        payload = ValidationEvidence(
            step="brief",
            status="pass",
            checks_passed=["brief_approved", "brief_exists"],
            validator="preflight",
            tool_used="minilegion",
            date="2026-03-12T00:00:00",
            notes="ok",
        )

        output_path = write_evidence(project_ai, payload)
        assert output_path.name == "brief.validation.json"

        raw = output_path.read_text(encoding="utf-8")
        assert '"step":"brief"' in raw
        assert '"status":"pass"' in raw
        assert '"checks_passed":["brief_approved","brief_exists"]' in raw
        assert '"validator":"preflight"' in raw
        assert '"tool_used":"minilegion"' in raw
        assert '"date":"2026-03-12T00:00:00"' in raw
        assert '"notes":"ok"' in raw

    def test_write_evidence_overwrites_same_step_file(self, tmp_path):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()

        first = ValidationEvidence(
            step="brief",
            status="fail",
            checks_passed=[],
            validator="preflight",
            tool_used="minilegion",
            date="2026-03-12T00:00:00",
            notes="first",
        )
        second = ValidationEvidence(
            step="brief",
            status="pass",
            checks_passed=["brief_approved"],
            validator="preflight",
            tool_used="minilegion",
            date="2026-03-12T00:01:00",
            notes="second",
        )

        first_path = write_evidence(project_ai, first)
        second_path = write_evidence(project_ai, second)
        assert first_path == second_path

        content = second_path.read_text(encoding="utf-8")
        assert '"status":"pass"' in content
        assert '"notes":"second"' in content
        assert '"notes":"first"' not in content

    def test_read_evidence_returns_typed_payload(self, tmp_path):
        project_ai = tmp_path / "project-ai"
        project_ai.mkdir()

        payload = ValidationEvidence(
            step="research",
            status="pass",
            checks_passed=["research_approved"],
            validator="preflight",
            tool_used="minilegion",
            date="2026-03-12T00:00:00",
            notes="good",
        )
        write_evidence(project_ai, payload)

        loaded = read_evidence(project_ai, "research")
        assert isinstance(loaded, ValidationEvidence)
        assert loaded is not None
        assert loaded.step == "research"
        assert loaded.status == "pass"
