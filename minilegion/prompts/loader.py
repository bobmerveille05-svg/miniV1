"""Prompt loader for MiniLegion role templates.

Loads role-specific prompt files from package data and supports
``{{placeholder}}`` variable injection.

Exports:
    load_prompt(role) -> tuple[str, str]
    render_prompt(template, **variables) -> str
"""

import re
from importlib import resources

from minilegion.core.exceptions import ConfigError

SYSTEM_MARKER = "<!-- SYSTEM -->"
USER_TEMPLATE_MARKER = "<!-- USER_TEMPLATE -->"


def load_prompt(role: str) -> tuple[str, str]:
    """Load a role prompt file and return (system_prompt, user_template).

    Args:
        role: One of 'researcher', 'designer', 'planner', 'builder', 'reviewer'.

    Returns:
        Tuple of (system_prompt, user_template) with leading/trailing whitespace stripped.

    Raises:
        ConfigError: If the prompt file is missing or lacks required section markers.
    """
    filename = f"{role}.md"
    try:
        content = (
            resources.files("minilegion.prompts").joinpath(filename).read_text("utf-8")
        )
    except (FileNotFoundError, TypeError, ModuleNotFoundError):
        raise ConfigError(f"Prompt file not found: {filename}")

    if SYSTEM_MARKER not in content:
        raise ConfigError(
            f"Prompt file {filename} is missing required marker: {SYSTEM_MARKER}"
        )
    if USER_TEMPLATE_MARKER not in content:
        raise ConfigError(
            f"Prompt file {filename} is missing required marker: {USER_TEMPLATE_MARKER}"
        )

    # Split on USER_TEMPLATE marker first to get two halves
    parts = content.split(USER_TEMPLATE_MARKER, 1)
    system_part = parts[0]
    user_template = parts[1].strip()

    # Remove the SYSTEM marker from the system part
    system_prompt = system_part.split(SYSTEM_MARKER, 1)[1].strip()

    return (system_prompt, user_template)


def render_prompt(template: str, **variables: str) -> str:
    """Replace ``{{placeholder}}`` variables in a template string.

    Args:
        template: Template string with ``{{key}}`` placeholders.
        **variables: Key-value pairs for substitution.

    Returns:
        The template with all placeholders replaced.

    Raises:
        ConfigError: If any ``{{placeholder}}`` remains unresolved after substitution.
    """

    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            raise ConfigError(
                f"Unresolved placeholder: {{{{{key}}}}} "
                f"— available variables: {sorted(variables.keys())}"
            )
        return variables[key]

    return re.sub(r"\{\{(\w+)\}\}", _replacer, template)
