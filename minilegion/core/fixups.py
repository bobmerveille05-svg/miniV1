"""Pre-parse fixup pipeline for raw LLM output.

LLM responses often contain artifacts that break JSON parsing:
- Markdown code fences (```json ... ```)
- Trailing commas ({\"a\": 1,})
- BOM characters and control characters

The pipeline chains fixups in the correct order:
1. BOM/control char removal (affects fence detection)
2. Markdown fence stripping (reveals the JSON body)
3. Trailing comma removal (cleans up the JSON)

Usage::

    from minilegion.core.fixups import apply_fixups

    cleaned = apply_fixups(raw_llm_output)
"""

import re


def strip_bom_and_control(text: str) -> str:
    """Remove UTF-8 BOM and control characters, preserving \\n, \\r, \\t.

    Args:
        text: Raw text that may contain BOM or control characters.

    Returns:
        Cleaned text with BOM and control characters removed.
    """
    # Remove BOM prefix
    if text.startswith("\ufeff"):
        text = text[1:]

    # Remove control chars (\x00-\x08, \x0b, \x0c, \x0e-\x1f, \x7f)
    # Preserve: \t (\x09), \n (\x0a), \r (\x0d)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json...``` or plain ```...```).

    Handles fences with optional language tags and leading/trailing whitespace.

    Args:
        text: Text that may be wrapped in markdown code fences.

    Returns:
        Inner content without fences, or original text if no fences found.
    """
    if not text.strip():
        return text

    # Match: optional whitespace, ```, optional language tag, newline,
    # captured content, newline, ```, optional whitespace
    pattern = r"^\s*```\w*\s*\n(.*?)\n\s*```\s*$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1)

    return text


def fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } and ] in JSON-like text.

    Uses a simple regex approach. Known limitation: may affect commas
    inside string values in edge cases. This is acceptable — structural
    JSON errors should fail validation and trigger retry.

    Args:
        text: JSON-like text that may contain trailing commas.

    Returns:
        Text with trailing commas removed.
    """
    return re.sub(r",\s*([}\]])", r"\1", text)


def apply_fixups(raw_text: str) -> str:
    """Apply all fixups in the correct order.

    Order matters:
    1. BOM/control removal — BOM can interfere with fence detection
    2. Fence stripping — reveals the JSON body
    3. Trailing comma removal — cleans up the JSON

    Args:
        raw_text: Raw LLM output text.

    Returns:
        Cleaned text ready for JSON parsing/validation.
    """
    text = strip_bom_and_control(raw_text)
    text = strip_markdown_fences(text)
    text = fix_trailing_commas(text)
    return text
