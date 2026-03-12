"""Prompt loader for MiniLegion role templates.

Loads role-specific prompt files from package data and supports
``{{placeholder}}`` variable injection and ``{{#if}}...{{else}}...{{/if}}``
conditional blocks.

Exports:
    load_prompt(role) -> tuple[str, str]
    render_prompt(template, **variables) -> str
"""

import re
from importlib import resources

from minilegion.core.exceptions import ConfigError

SYSTEM_MARKER = "<!-- SYSTEM -->"
USER_TEMPLATE_MARKER = "<!-- USER_TEMPLATE -->"

# Matches {{#if <expr>}} ... {{else}} ... {{/if}} (else branch optional)
# Uses DOTALL so .* spans newlines.
_IF_BLOCK_RE = re.compile(
    r"\{\{#if\s+([^}]+?)\}\}(.*?)(?:\{\{else\}\}(.*?))?\{\{/if\}\}",
    re.DOTALL,
)


def _eval_condition(expr: str, variables: dict[str, str]) -> bool:
    """Evaluate a simple ``key == "value"`` or ``key != "value"`` expression.

    Only supports equality/inequality comparisons against string literals.
    Returns False for anything it cannot parse so the if-branch is skipped
    gracefully rather than raising.
    """
    expr = expr.strip()
    for op, comparator in (("==", True), ("!=", False)):
        if op in expr:
            lhs, _, rhs = expr.partition(op)
            key = lhs.strip()
            val = rhs.strip().strip("\"'")
            var_val = variables.get(key, "")
            match = var_val == val
            return match if comparator else not match
    return False


def _resolve_if_blocks(template: str, variables: dict[str, str]) -> str:
    """Replace all ``{{#if}}...{{else}}...{{/if}}`` blocks with the correct branch."""

    def _replace(m: re.Match) -> str:
        condition = m.group(1)
        if_branch = m.group(2) or ""
        else_branch = m.group(3) or ""
        return if_branch if _eval_condition(condition, variables) else else_branch

    return _IF_BLOCK_RE.sub(_replace, template)


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

    Supports:
    - ``{{key}}`` — simple variable substitution
    - ``{{#if key == "value"}}...{{else}}...{{/if}}`` — conditional blocks
      (``{{else}}`` branch is optional)

    Args:
        template: Template string with ``{{key}}`` placeholders and/or
            ``{{#if}}`` conditional blocks.
        **variables: Key-value pairs for substitution.

    Returns:
        The template with all placeholders replaced and conditionals resolved.

    Raises:
        ConfigError: If any ``{{placeholder}}`` remains unresolved after substitution.
    """
    # Step 1: resolve {{#if}}...{{else}}...{{/if}} blocks first
    text = _resolve_if_blocks(template, variables)

    # Step 2: substitute simple {{key}} placeholders
    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            raise ConfigError(
                f"Unresolved placeholder: {{{{{key}}}}} "
                f"— available variables: {sorted(variables.keys())}"
            )
        return variables[key]

    return re.sub(r"\{\{(\w+)\}\}", _replacer, text)
