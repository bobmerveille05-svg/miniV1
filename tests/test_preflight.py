"""Unit tests for pre-flight validation checks.

Tests GUARD-01 (file checks), GUARD-02 (approval checks),
and GUARD-03 (safe-mode guards).
"""

import pytest

from minilegion.core.exceptions import PreflightError
from minilegion.core.preflight import (
    REQUIRED_APPROVALS,
    REQUIRED_FILES,
    check_preflight,
)
from minilegion.core.state import ProjectState, Stage, save_state


def _make_state(project_dir, approvals=None):
    """Helper: write a STATE.json with given approvals into project_dir."""
    state = ProjectState()
    if approvals:
        state.approvals.update(approvals)
    save_state(state, project_dir / "STATE.json")
    return state


class TestPreflightFiles:
    """GUARD-01: Pre-flight file requirement checks."""

    def test_init_and_brief_have_no_file_requirements(self, tmp_project_dir):
        """INIT and BRIEF stages have no file requirements — always pass."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(project_dir)
        # Should not raise
        check_preflight(Stage.INIT, project_dir)
        check_preflight(Stage.BRIEF, project_dir)

    def test_research_requires_brief(self, tmp_project_dir):
        """RESEARCH requires BRIEF.md — raises PreflightError when missing."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(project_dir, {"brief_approved": True})
        with pytest.raises(PreflightError, match="BRIEF.md"):
            check_preflight(Stage.RESEARCH, project_dir)

    def test_design_requires_brief_and_research(self, tmp_project_dir):
        """DESIGN requires BRIEF.md and RESEARCH.json — fails on first missing."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
            },
        )
        # Missing BRIEF.md → error
        with pytest.raises(PreflightError, match="BRIEF.md"):
            check_preflight(Stage.DESIGN, project_dir)

        # Add BRIEF.md, still missing RESEARCH.json
        (project_dir / "BRIEF.md").touch()
        with pytest.raises(PreflightError, match="RESEARCH.json"):
            check_preflight(Stage.DESIGN, project_dir)

    def test_plan_requires_all_three(self, tmp_project_dir):
        """PLAN requires BRIEF.md, RESEARCH.json, DESIGN.json."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
            },
        )
        with pytest.raises(PreflightError, match="BRIEF.md"):
            check_preflight(Stage.PLAN, project_dir)

        (project_dir / "BRIEF.md").touch()
        with pytest.raises(PreflightError, match="RESEARCH.json"):
            check_preflight(Stage.PLAN, project_dir)

        (project_dir / "RESEARCH.json").touch()
        with pytest.raises(PreflightError, match="DESIGN.json"):
            check_preflight(Stage.PLAN, project_dir)

    def test_execute_requires_all_four(self, tmp_project_dir):
        """EXECUTE requires BRIEF.md, RESEARCH.json, DESIGN.json, PLAN.json."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
                "plan_approved": True,
            },
        )
        with pytest.raises(PreflightError, match="BRIEF.md"):
            check_preflight(Stage.EXECUTE, project_dir)

        (project_dir / "BRIEF.md").touch()
        (project_dir / "RESEARCH.json").touch()
        (project_dir / "DESIGN.json").touch()
        with pytest.raises(PreflightError, match="PLAN.json"):
            check_preflight(Stage.EXECUTE, project_dir)

    def test_review_requires_all_five(self, tmp_project_dir):
        """REVIEW requires all 5 files including EXECUTION_LOG.json."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
                "plan_approved": True,
                "execute_approved": True,
            },
        )
        with pytest.raises(PreflightError, match="BRIEF.md"):
            check_preflight(Stage.REVIEW, project_dir)

        (project_dir / "BRIEF.md").touch()
        (project_dir / "RESEARCH.json").touch()
        (project_dir / "DESIGN.json").touch()
        (project_dir / "PLAN.json").touch()
        with pytest.raises(PreflightError, match="EXECUTION_LOG.json"):
            check_preflight(Stage.REVIEW, project_dir)

    def test_all_files_present_passes(self, tmp_project_dir):
        """When all required files exist, no error is raised."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
                "plan_approved": True,
                "execute_approved": True,
            },
        )
        for f in [
            "BRIEF.md",
            "RESEARCH.json",
            "DESIGN.json",
            "PLAN.json",
            "EXECUTION_LOG.json",
        ]:
            (project_dir / f).touch()

        # Should not raise for any stage
        check_preflight(Stage.REVIEW, project_dir)


class TestPreflightApprovals:
    """GUARD-02: Pre-flight approval requirement checks."""

    def test_research_requires_brief_approved(self, tmp_project_dir):
        """RESEARCH requires brief_approved — raises PreflightError when False."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(project_dir)  # all approvals False
        (project_dir / "BRIEF.md").touch()
        with pytest.raises(PreflightError, match="brief_approved"):
            check_preflight(Stage.RESEARCH, project_dir)

    def test_design_requires_brief_and_research_approved(self, tmp_project_dir):
        """DESIGN requires brief_approved and research_approved."""
        project_dir = tmp_project_dir / "project-ai"
        # Create required files
        for f in ["BRIEF.md", "RESEARCH.json"]:
            (project_dir / f).touch()

        # Only brief_approved → fails on research_approved
        _make_state(project_dir, {"brief_approved": True})
        with pytest.raises(PreflightError, match="research_approved"):
            check_preflight(Stage.DESIGN, project_dir)

        # Neither approved → fails on first (brief_approved)
        _make_state(project_dir)
        with pytest.raises(PreflightError, match="brief_approved"):
            check_preflight(Stage.DESIGN, project_dir)

    def test_plan_requires_three_approvals(self, tmp_project_dir):
        """PLAN requires brief_approved, research_approved, design_approved."""
        project_dir = tmp_project_dir / "project-ai"
        for f in ["BRIEF.md", "RESEARCH.json", "DESIGN.json"]:
            (project_dir / f).touch()

        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
            },
        )
        with pytest.raises(PreflightError, match="design_approved"):
            check_preflight(Stage.PLAN, project_dir)

    def test_execute_requires_four_approvals(self, tmp_project_dir):
        """EXECUTE requires 4 approvals including plan_approved."""
        project_dir = tmp_project_dir / "project-ai"
        for f in ["BRIEF.md", "RESEARCH.json", "DESIGN.json", "PLAN.json"]:
            (project_dir / f).touch()

        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
            },
        )
        with pytest.raises(PreflightError, match="plan_approved"):
            check_preflight(Stage.EXECUTE, project_dir)

    def test_review_requires_five_approvals(self, tmp_project_dir):
        """REVIEW requires 5 approvals including execute_approved."""
        project_dir = tmp_project_dir / "project-ai"
        for f in [
            "BRIEF.md",
            "RESEARCH.json",
            "DESIGN.json",
            "PLAN.json",
            "EXECUTION_LOG.json",
        ]:
            (project_dir / f).touch()

        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
                "plan_approved": True,
            },
        )
        with pytest.raises(PreflightError, match="execute_approved"):
            check_preflight(Stage.REVIEW, project_dir)

    def test_all_approvals_present_passes(self, tmp_project_dir):
        """No error when all required approvals are True."""
        project_dir = tmp_project_dir / "project-ai"
        for f in [
            "BRIEF.md",
            "RESEARCH.json",
            "DESIGN.json",
            "PLAN.json",
            "EXECUTION_LOG.json",
        ]:
            (project_dir / f).touch()

        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
                "plan_approved": True,
                "execute_approved": True,
            },
        )
        # Should not raise
        check_preflight(Stage.REVIEW, project_dir)


class TestSafeModeGuards:
    """GUARD-03: Safe-mode specific pre-flight cases."""

    def test_design_refuses_without_research_json(self, tmp_project_dir):
        """DESIGN stage refuses when RESEARCH.json is missing."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
            },
        )
        (project_dir / "BRIEF.md").touch()
        # RESEARCH.json missing
        with pytest.raises(PreflightError, match="RESEARCH.json"):
            check_preflight(Stage.DESIGN, project_dir)

    def test_plan_refuses_without_design_json(self, tmp_project_dir):
        """PLAN stage refuses when DESIGN.json is missing."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(
            project_dir,
            {
                "brief_approved": True,
                "research_approved": True,
                "design_approved": True,
            },
        )
        (project_dir / "BRIEF.md").touch()
        (project_dir / "RESEARCH.json").touch()
        # DESIGN.json missing
        with pytest.raises(PreflightError, match="DESIGN.json"):
            check_preflight(Stage.PLAN, project_dir)


class TestArchivePreflight:
    """Stage.ARCHIVE entries in REQUIRED_FILES and REQUIRED_APPROVALS."""

    def test_archive_in_required_files(self):
        assert Stage.ARCHIVE in REQUIRED_FILES

    def test_archive_required_files_content(self):
        assert REQUIRED_FILES[Stage.ARCHIVE] == [
            "REVIEW.json",
            "PLAN.json",
            "EXECUTION_LOG.json",
            "DESIGN.json",
        ]

    def test_archive_in_required_approvals(self):
        assert Stage.ARCHIVE in REQUIRED_APPROVALS

    def test_archive_required_approvals_content(self):
        assert REQUIRED_APPROVALS[Stage.ARCHIVE] == ["review_approved"]

    def test_archive_preflight_raises_on_missing_review_json(self, tmp_project_dir):
        """check_preflight(Stage.ARCHIVE) raises PreflightError when REVIEW.json is missing."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(project_dir, {"review_approved": True})
        # No files created
        with pytest.raises(PreflightError, match="REVIEW.json"):
            check_preflight(Stage.ARCHIVE, project_dir)

    def test_archive_preflight_raises_on_missing_review_approved(self, tmp_project_dir):
        """check_preflight(Stage.ARCHIVE) raises PreflightError when review_approved is False."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(project_dir)  # review_approved=False by default
        for f in ["REVIEW.json", "PLAN.json", "EXECUTION_LOG.json", "DESIGN.json"]:
            (project_dir / f).touch()
        with pytest.raises(PreflightError, match="review_approved"):
            check_preflight(Stage.ARCHIVE, project_dir)

    def test_archive_preflight_passes_when_all_satisfied(self, tmp_project_dir):
        """check_preflight(Stage.ARCHIVE) passes when all 4 files exist and review_approved=True."""
        project_dir = tmp_project_dir / "project-ai"
        _make_state(project_dir, {"review_approved": True})
        for f in ["REVIEW.json", "PLAN.json", "EXECUTION_LOG.json", "DESIGN.json"]:
            (project_dir / f).touch()
        # Should not raise
        check_preflight(Stage.ARCHIVE, project_dir)
