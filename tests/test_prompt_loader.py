"""Tests for minilegion.prompts.loader — prompt loading and variable injection."""

import re
from unittest.mock import MagicMock, patch

import pytest

from minilegion.core.exceptions import ConfigError
from minilegion.prompts.loader import load_prompt, render_prompt


ALL_ROLES = ["researcher", "designer", "planner", "builder", "reviewer"]


# ── TestLoadPrompt ────────────────────────────────────────────────────


class TestLoadPrompt:
    """Test load_prompt() returns valid (system, user_template) tuples."""

    def test_load_researcher(self):
        """load_prompt('researcher') returns 2-tuple of non-empty strings."""
        system, user_template = load_prompt("researcher")
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user_template, str) and len(user_template) > 0

    def test_load_designer(self):
        """load_prompt('designer') returns 2-tuple of non-empty strings."""
        system, user_template = load_prompt("designer")
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user_template, str) and len(user_template) > 0

    def test_load_planner(self):
        """load_prompt('planner') returns 2-tuple of non-empty strings."""
        system, user_template = load_prompt("planner")
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user_template, str) and len(user_template) > 0

    def test_load_builder(self):
        """load_prompt('builder') returns 2-tuple of non-empty strings."""
        system, user_template = load_prompt("builder")
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user_template, str) and len(user_template) > 0

    def test_load_reviewer(self):
        """load_prompt('reviewer') returns 2-tuple of non-empty strings."""
        system, user_template = load_prompt("reviewer")
        assert isinstance(system, str) and len(system) > 0
        assert isinstance(user_template, str) and len(user_template) > 0

    def test_missing_file_raises_config_error(self):
        """load_prompt('nonexistent') raises ConfigError."""
        with pytest.raises(ConfigError, match="not found"):
            load_prompt("nonexistent")

    def test_missing_system_marker_raises_config_error(self):
        """Prompt file without <!-- SYSTEM --> marker raises ConfigError."""
        bad_content = "No markers here\n<!-- USER_TEMPLATE -->\ntemplate"
        mock_path = MagicMock()
        mock_path.read_text.return_value = bad_content
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_path

        with patch(
            "minilegion.prompts.loader.resources.files", return_value=mock_files
        ):
            with pytest.raises(ConfigError, match="SYSTEM"):
                load_prompt("fakefile")

    def test_missing_user_template_marker_raises_config_error(self):
        """Prompt file without <!-- USER_TEMPLATE --> marker raises ConfigError."""
        bad_content = "<!-- SYSTEM -->\nSystem text only"
        mock_path = MagicMock()
        mock_path.read_text.return_value = bad_content
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_path

        with patch(
            "minilegion.prompts.loader.resources.files", return_value=mock_files
        ):
            with pytest.raises(ConfigError, match="USER_TEMPLATE"):
                load_prompt("fakefile")


# ── TestJsonAnchoring ─────────────────────────────────────────────────


class TestJsonAnchoring:
    """Test that all system prompts have JSON enforcement at start and end."""

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_system_prompt_starts_with_json_enforcement(self, role):
        """System prompt contains JSON enforcement text near the start."""
        system, _ = load_prompt(role)
        first_200 = system[:200].lower()
        assert "json" in first_200, (
            f"{role} system prompt must mention JSON within first 200 chars"
        )

    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_system_prompt_ends_with_json_anchoring(self, role):
        """System prompt contains JSON anchoring text near the end."""
        system, _ = load_prompt(role)
        last_200 = system[-200:].lower()
        assert "json" in last_200, (
            f"{role} system prompt must mention JSON within last 200 chars"
        )


# ── TestRenderPrompt ──────────────────────────────────────────────────


class TestRenderPrompt:
    """Test render_prompt() placeholder substitution."""

    def test_simple_replacement(self):
        """Single placeholder replacement works."""
        result = render_prompt("Hello {{name}}", name="World")
        assert result == "Hello World"

    def test_multiple_replacements(self):
        """Multiple different placeholders are replaced."""
        result = render_prompt("{{a}} and {{b}}", a="X", b="Y")
        assert result == "X and Y"

    def test_same_placeholder_twice(self):
        """Same placeholder used multiple times is replaced everywhere."""
        result = render_prompt("{{x}} then {{x}}", x="V")
        assert result == "V then V"

    def test_no_placeholders(self):
        """Template without placeholders is returned unchanged."""
        result = render_prompt("plain text")
        assert result == "plain text"

    def test_missing_variable_raises_config_error(self):
        """Unresolved placeholder raises ConfigError."""
        with pytest.raises(ConfigError, match="Unresolved placeholder"):
            render_prompt("{{missing}}")

    def test_missing_variable_shows_available_keys(self):
        """ConfigError message includes available variable names."""
        with pytest.raises(ConfigError, match="present"):
            render_prompt("{{missing}}", present="val")

    def test_extra_variables_ignored(self):
        """Extra variables that aren't in the template are silently ignored."""
        result = render_prompt("{{a}}", a="X", b="Y")
        assert result == "X"


# ── TestPromptPlaceholders ────────────────────────────────────────────


class TestPromptPlaceholders:
    """Test that each role's USER_TEMPLATE contains the expected placeholders."""

    @pytest.mark.parametrize(
        "role, expected_placeholders",
        [
            (
                "researcher",
                ["{{brief_content}}", "{{codebase_context}}", "{{project_name}}"],
            ),
            (
                "designer",
                [
                    "{{brief_content}}",
                    "{{research_json}}",
                    "{{focus_files_content}}",
                    "{{project_name}}",
                ],
            ),
            (
                "planner",
                [
                    "{{brief_content}}",
                    "{{research_json}}",
                    "{{design_json}}",
                    "{{project_name}}",
                ],
            ),
            ("builder", ["{{plan_json}}", "{{source_files}}", "{{project_name}}"]),
            (
                "reviewer",
                [
                    "{{diff_text}}",
                    "{{plan_json}}",
                    "{{design_json}}",
                    "{{conventions}}",
                    "{{project_name}}",
                ],
            ),
        ],
    )
    def test_user_template_contains_expected_placeholders(
        self, role, expected_placeholders
    ):
        """Each role's USER_TEMPLATE contains the correct placeholders."""
        _, user_template = load_prompt(role)
        for placeholder in expected_placeholders:
            assert placeholder in user_template, (
                f"{role} USER_TEMPLATE missing placeholder: {placeholder}"
            )


# ── TestBehavioralConstraints ─────────────────────────────────────────


class TestBehavioralConstraints:
    """Test that each role's system prompt contains its behavioral constraint."""

    @pytest.mark.parametrize(
        "role, must_contain, must_not_verb",
        [
            ("researcher", "explore", "design"),
            ("designer", "design", "plan"),
            ("planner", "decompose", "design"),
            ("builder", "build", "redesign"),
            ("reviewer", "identify", "correct"),
        ],
    )
    def test_behavioral_constraint_present(self, role, must_contain, must_not_verb):
        """System prompt contains the behavioral DO and DON'T constraint."""
        system, _ = load_prompt(role)
        system_lower = system.lower()
        assert must_contain in system_lower, (
            f"{role} system prompt must contain '{must_contain}'"
        )
        # Check for "don't <verb>" or "do not <verb>" pattern
        dont_pattern = f"don't {must_not_verb}|do not {must_not_verb}"
        assert re.search(dont_pattern, system_lower), (
            f'{role} system prompt must contain "don\'t {must_not_verb}" or "do not {must_not_verb}"'
        )
