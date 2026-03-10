"""Tests for minilegion.core.fixups — pre-parse fixup pipeline.

Tests cover:
- strip_markdown_fences: removes ```json and plain ``` wrappers
- fix_trailing_commas: removes trailing commas before } and ]
- strip_bom_and_control: removes BOM and control chars, preserves \\n \\r \\t
- apply_fixups: chains all three in correct order
"""

import json


from minilegion.core.fixups import (
    apply_fixups,
    fix_trailing_commas,
    strip_bom_and_control,
    strip_markdown_fences,
)


# ---------------------------------------------------------------------------
# strip_markdown_fences
# ---------------------------------------------------------------------------


class TestStripMarkdownFences:
    """Tests for strip_markdown_fences."""

    def test_removes_json_fences(self):
        text = '```json\n{"key": "value"}\n```'
        result = strip_markdown_fences(text)
        assert result.strip() == '{"key": "value"}'

    def test_removes_plain_fences(self):
        text = '```\n{"key": "value"}\n```'
        result = strip_markdown_fences(text)
        assert result.strip() == '{"key": "value"}'

    def test_no_fences_unchanged(self):
        text = '{"key": "value"}'
        result = strip_markdown_fences(text)
        assert result == '{"key": "value"}'

    def test_handles_leading_trailing_whitespace(self):
        text = '  \n```json\n{"a": 1}\n```\n  '
        result = strip_markdown_fences(text)
        assert result.strip() == '{"a": 1}'

    def test_handles_multiline_json(self):
        text = '```json\n{\n  "a": 1,\n  "b": 2\n}\n```'
        result = strip_markdown_fences(text)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    def test_handles_jsonl_tag(self):
        """Some LLMs use ```jsonl instead of ```json."""
        text = '```jsonl\n{"key": "value"}\n```'
        # Should strip any fence, even uncommon language tags
        result = strip_markdown_fences(text)
        # At minimum shouldn't crash; fences with other tags may or may not be stripped
        assert isinstance(result, str)

    def test_empty_string(self):
        assert strip_markdown_fences("") == ""

    def test_whitespace_only(self):
        result = strip_markdown_fences("   \n\n  ")
        assert result.strip() == ""


# ---------------------------------------------------------------------------
# fix_trailing_commas
# ---------------------------------------------------------------------------


class TestFixTrailingCommas:
    """Tests for fix_trailing_commas."""

    def test_removes_comma_before_closing_brace(self):
        text = '{"a": 1,}'
        result = fix_trailing_commas(text)
        assert result == '{"a": 1}'

    def test_removes_comma_before_closing_bracket(self):
        text = "[1, 2,]"
        result = fix_trailing_commas(text)
        assert result == "[1, 2]"

    def test_handles_nested_trailing_commas(self):
        text = '{"a": [1, 2,], "b": {"c": 3,},}'
        result = fix_trailing_commas(text)
        parsed = json.loads(result)
        assert parsed == {"a": [1, 2], "b": {"c": 3}}

    def test_no_trailing_commas_unchanged(self):
        text = '{"a": 1, "b": 2}'
        result = fix_trailing_commas(text)
        assert result == '{"a": 1, "b": 2}'

    def test_comma_with_whitespace_before_brace(self):
        text = '{"a": 1 , }'
        result = fix_trailing_commas(text)
        assert json.loads(result) == {"a": 1}

    def test_comma_with_newline_before_brace(self):
        text = '{\n  "a": 1,\n}'
        result = fix_trailing_commas(text)
        assert json.loads(result) == {"a": 1}

    def test_empty_string(self):
        assert fix_trailing_commas("") == ""

    def test_comma_inside_string_value_edge_case(self):
        """Simple regex may affect commas inside strings — acknowledged edge case."""
        text = '{"msg": "hello,}"}'
        # This is a known limitation: the regex may incorrectly strip the comma
        # inside the string. We document this but don't try to solve it.
        result = fix_trailing_commas(text)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# strip_bom_and_control
# ---------------------------------------------------------------------------


class TestStripBomAndControl:
    """Tests for strip_bom_and_control."""

    def test_removes_bom(self):
        text = "\ufeff" + '{"a": 1}'
        result = strip_bom_and_control(text)
        assert result == '{"a": 1}'

    def test_removes_control_chars(self):
        text = '{"a"\x00: \x01"val\x7fue"}'
        result = strip_bom_and_control(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x7f" not in result

    def test_preserves_newline(self):
        text = '{\n  "a": 1\n}'
        result = strip_bom_and_control(text)
        assert result == text

    def test_preserves_tab(self):
        text = '{\t"a": 1}'
        result = strip_bom_and_control(text)
        assert result == text

    def test_preserves_carriage_return(self):
        text = '{"a": 1}\r\n'
        result = strip_bom_and_control(text)
        assert "\r" in result

    def test_removes_mixed_control_chars(self):
        text = "\x02hello\x0eworld\x1f"
        result = strip_bom_and_control(text)
        assert result == "helloworld"

    def test_empty_string(self):
        assert strip_bom_and_control("") == ""

    def test_bom_only(self):
        result = strip_bom_and_control("\ufeff")
        assert result == ""


# ---------------------------------------------------------------------------
# apply_fixups
# ---------------------------------------------------------------------------


class TestApplyFixups:
    """Tests for apply_fixups — full pipeline."""

    def test_chains_all_fixups(self):
        """BOM + fences + trailing commas → valid JSON."""
        raw = '\ufeff```json\n{"a": 1,}\n```'
        result = apply_fixups(raw)
        parsed = json.loads(result)
        assert parsed == {"a": 1}

    def test_clean_json_unchanged(self):
        clean = '{"a": 1, "b": [2, 3]}'
        result = apply_fixups(clean)
        assert result == clean

    def test_order_bom_then_fences_then_commas(self):
        """BOM must be removed before fence detection works properly."""
        raw = '\ufeff```json\n{"items": [1, 2,],}\n```'
        result = apply_fixups(raw)
        parsed = json.loads(result)
        assert parsed == {"items": [1, 2]}

    def test_only_bom(self):
        raw = "\ufeff" + '{"a": 1}'
        result = apply_fixups(raw)
        assert json.loads(result) == {"a": 1}

    def test_only_fences(self):
        raw = '```json\n{"a": 1}\n```'
        result = apply_fixups(raw)
        assert json.loads(result) == {"a": 1}

    def test_only_trailing_commas(self):
        raw = '{"a": 1,}'
        result = apply_fixups(raw)
        assert json.loads(result) == {"a": 1}

    def test_empty_string(self):
        assert apply_fixups("") == ""

    def test_whitespace_only(self):
        result = apply_fixups("   \n\n  ")
        assert isinstance(result, str)

    def test_complex_nested_structure(self):
        raw = '```json\n{"list": [{"a": 1,}, {"b": 2,},], "c": 3,}\n```'
        result = apply_fixups(raw)
        parsed = json.loads(result)
        assert parsed == {"list": [{"a": 1}, {"b": 2}], "c": 3}
