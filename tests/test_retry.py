"""Tests for minilegion.core.retry — retry logic with error feedback and RAW_DEBUG capture.

Tests cover:
- summarize_errors: converts PydanticValidationError to human-readable summary
- save_raw_debug: writes timestamped debug files via write_atomic
- validate_with_retry: full retry loop with fixups, validation, error feedback
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ValidationError as MiniLegionValidationError
from minilegion.core.retry import save_raw_debug, summarize_errors, validate_with_retry


# ---------------------------------------------------------------------------
# Helpers — test models for triggering PydanticValidationError
# ---------------------------------------------------------------------------


class SimpleModel(BaseModel):
    x: int
    y: str


class ManyFieldModel(BaseModel):
    a: int
    b: int
    c: int
    d: int
    e: int
    f: int
    g: int


# ---------------------------------------------------------------------------
# summarize_errors
# ---------------------------------------------------------------------------


class TestSummarizeErrors:
    """Tests for summarize_errors."""

    def test_produces_human_readable_summary(self):
        """Summary should be readable sentences, not raw Pydantic dump."""
        try:
            SimpleModel.model_validate({"x": "not_an_int", "y": 123})
        except PydanticValidationError as exc:
            result = summarize_errors(exc)

        assert "Validation failed" in result
        assert "error" in result.lower()
        # Should mention field names
        assert "x" in result

    def test_single_error(self):
        try:
            SimpleModel.model_validate({"x": "bad", "y": "ok"})
        except PydanticValidationError as exc:
            result = summarize_errors(exc)

        assert "1 error" in result
        assert "x" in result

    def test_multiple_errors(self):
        try:
            SimpleModel.model_validate({"x": "bad"})  # x wrong type, y missing
        except PydanticValidationError as exc:
            result = summarize_errors(exc)

        assert "2 error" in result

    def test_caps_at_5_issues(self):
        """When >5 errors, only show 5 and note remainder."""
        try:
            ManyFieldModel.model_validate(
                {
                    "a": "x",
                    "b": "x",
                    "c": "x",
                    "d": "x",
                    "e": "x",
                    "f": "x",
                    "g": "x",
                }
            )
        except PydanticValidationError as exc:
            result = summarize_errors(exc)

        assert "7 error" in result
        assert "and 2 more" in result

    def test_returns_string(self):
        try:
            SimpleModel.model_validate({"x": "bad", "y": "ok"})
        except PydanticValidationError as exc:
            result = summarize_errors(exc)

        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# save_raw_debug
# ---------------------------------------------------------------------------


class TestSaveRawDebug:
    """Tests for save_raw_debug."""

    def test_creates_file_in_correct_directory(self, tmp_path: Path):
        path = save_raw_debug("research", "raw output", "error summary", tmp_path)

        assert path.exists()
        assert "project-ai" in str(path)
        assert "debug" in str(path)

    def test_filename_pattern(self, tmp_path: Path):
        path = save_raw_debug("research", "raw output", "error summary", tmp_path)

        # Filename should be: RESEARCH_RAW_DEBUG_{timestamp}.txt
        assert path.name.startswith("RESEARCH_RAW_DEBUG_")
        assert path.name.endswith(".txt")
        # Timestamp pattern: YYYYMMDDTHHMMSS (no colons — Windows-safe)
        timestamp_part = path.stem.replace("RESEARCH_RAW_DEBUG_", "")
        assert re.match(r"\d{8}T\d{6}", timestamp_part)

    def test_file_content(self, tmp_path: Path):
        path = save_raw_debug("design", "the raw output", "the error summary", tmp_path)

        content = path.read_text(encoding="utf-8")
        assert "=== RAW LLM OUTPUT ===" in content
        assert "the raw output" in content
        assert "=== VALIDATION ERRORS ===" in content
        assert "the error summary" in content

    def test_artifact_name_uppercased(self, tmp_path: Path):
        path = save_raw_debug("execution_log", "raw", "errors", tmp_path)

        assert "EXECUTION_LOG" in path.name

    def test_returns_path(self, tmp_path: Path):
        result = save_raw_debug("research", "raw", "errors", tmp_path)

        assert isinstance(result, Path)

    def test_uses_write_atomic(self, tmp_path: Path):
        """Verify save_raw_debug uses write_atomic for file writing."""
        with patch("minilegion.core.retry.write_atomic") as mock_write:
            save_raw_debug("research", "raw", "errors", tmp_path)

        mock_write.assert_called_once()
        call_args = mock_write.call_args
        # First arg should be a Path, second should be content string
        assert isinstance(call_args[0][0], Path)
        assert isinstance(call_args[0][1], str)


# ---------------------------------------------------------------------------
# validate_with_retry
# ---------------------------------------------------------------------------


class TestValidateWithRetry:
    """Tests for validate_with_retry."""

    def _make_config(self, max_retries: int = 2) -> MiniLegionConfig:
        return MiniLegionConfig(max_retries=max_retries)

    def test_first_try_success_no_retries(self, tmp_path: Path):
        """Valid JSON on first try returns model immediately."""
        valid_json = '{"x": 42, "y": "hello"}'
        llm_call = MagicMock(return_value=valid_json)

        # Register SimpleModel for this test
        with patch("minilegion.core.retry.validate") as mock_validate:
            mock_validate.return_value = SimpleModel(x=42, y="hello")
            result = validate_with_retry(
                llm_call,
                "test prompt",
                "test_artifact",
                self._make_config(),
                tmp_path,
            )

        assert llm_call.call_count == 1
        assert result.x == 42
        assert result.y == "hello"

    def test_retry_on_failure_then_success(self, tmp_path: Path):
        """Bad JSON first, then valid JSON — should retry once."""
        bad_json = '{"x": "not_int", "y": "ok"}'
        good_json = '{"x": 42, "y": "hello"}'
        llm_call = MagicMock(side_effect=[bad_json, good_json])

        # First validate call raises PydanticValidationError, second succeeds
        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "not_int", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        call_count = [0]

        def mock_validate(artifact_name, data):
            call_count[0] += 1
            if call_count[0] == 1:
                raise pydantic_exc
            return SimpleModel(x=42, y="hello")

        with patch("minilegion.core.retry.validate", side_effect=mock_validate):
            result = validate_with_retry(
                llm_call,
                "test prompt",
                "test_artifact",
                self._make_config(),
                tmp_path,
            )

        assert llm_call.call_count == 2
        assert result.x == 42

    def test_retry_prompt_includes_error_feedback(self, tmp_path: Path):
        """Second call to llm_call should include error feedback."""
        bad_json = '{"x": "not_int", "y": "ok"}'
        good_json = '{"x": 42, "y": "hello"}'
        llm_call = MagicMock(side_effect=[bad_json, good_json])

        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "not_int", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        call_count = [0]

        def mock_validate(artifact_name, data):
            call_count[0] += 1
            if call_count[0] == 1:
                raise pydantic_exc
            return SimpleModel(x=42, y="hello")

        with patch("minilegion.core.retry.validate", side_effect=mock_validate):
            validate_with_retry(
                llm_call,
                "test prompt",
                "test_artifact",
                self._make_config(),
                tmp_path,
            )

        # Second call should have error feedback in prompt
        second_call_prompt = llm_call.call_args_list[1][0][0]
        assert "VALIDATION ERROR" in second_call_prompt
        assert "invalid" in second_call_prompt.lower()

    def test_exhausted_retries_raises_minilegion_error(self, tmp_path: Path):
        """After max retries, should raise MiniLegion ValidationError."""
        bad_json = '{"x": "not_int", "y": "ok"}'
        llm_call = MagicMock(return_value=bad_json)

        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "not_int", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        with patch("minilegion.core.retry.validate", side_effect=pydantic_exc):
            with patch("minilegion.core.retry.save_raw_debug") as mock_debug:
                mock_debug.return_value = tmp_path / "debug.txt"
                with pytest.raises(MiniLegionValidationError):
                    validate_with_retry(
                        llm_call,
                        "test prompt",
                        "test_artifact",
                        self._make_config(max_retries=2),
                        tmp_path,
                    )

        # 1 initial + 2 retries = 3 total calls
        assert llm_call.call_count == 3

    def test_saves_raw_debug_on_exhaustion(self, tmp_path: Path):
        """After max retries, save_raw_debug should be called."""
        bad_json = '{"x": "not_int"}'
        llm_call = MagicMock(return_value=bad_json)

        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "not_int", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        with patch("minilegion.core.retry.validate", side_effect=pydantic_exc):
            with patch("minilegion.core.retry.save_raw_debug") as mock_debug:
                mock_debug.return_value = tmp_path / "debug.txt"
                with pytest.raises(MiniLegionValidationError):
                    validate_with_retry(
                        llm_call,
                        "test prompt",
                        "test_artifact",
                        self._make_config(max_retries=1),
                        tmp_path,
                    )

        mock_debug.assert_called_once()
        # Check it was called with artifact name and raw output
        args = mock_debug.call_args[0]
        assert args[0] == "test_artifact"

    def test_respects_max_retries_1(self, tmp_path: Path):
        """With max_retries=1, should make 2 total calls (1 initial + 1 retry)."""
        bad_json = '{"x": "bad"}'
        llm_call = MagicMock(return_value=bad_json)

        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "bad", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        with patch("minilegion.core.retry.validate", side_effect=pydantic_exc):
            with patch("minilegion.core.retry.save_raw_debug") as mock_debug:
                mock_debug.return_value = tmp_path / "debug.txt"
                with pytest.raises(MiniLegionValidationError):
                    validate_with_retry(
                        llm_call,
                        "test prompt",
                        "test_artifact",
                        self._make_config(max_retries=1),
                        tmp_path,
                    )

        assert llm_call.call_count == 2  # 1 initial + 1 retry

    def test_respects_max_retries_3(self, tmp_path: Path):
        """With max_retries=3, should make 4 total calls (1 initial + 3 retries)."""
        bad_json = '{"x": "bad"}'
        llm_call = MagicMock(return_value=bad_json)

        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "bad", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        with patch("minilegion.core.retry.validate", side_effect=pydantic_exc):
            with patch("minilegion.core.retry.save_raw_debug") as mock_debug:
                mock_debug.return_value = tmp_path / "debug.txt"
                with pytest.raises(MiniLegionValidationError):
                    validate_with_retry(
                        llm_call,
                        "test prompt",
                        "test_artifact",
                        self._make_config(max_retries=3),
                        tmp_path,
                    )

        assert llm_call.call_count == 4  # 1 initial + 3 retries

    def test_applies_fixups_before_validation(self, tmp_path: Path):
        """validate_with_retry should call apply_fixups on raw output."""
        raw_output = '```json\n{"x": 42, "y": "hello"}\n```'
        llm_call = MagicMock(return_value=raw_output)

        with patch(
            "minilegion.core.retry.apply_fixups", return_value='{"x": 42, "y": "hello"}'
        ) as mock_fixups:
            with patch("minilegion.core.retry.validate") as mock_validate:
                mock_validate.return_value = SimpleModel(x=42, y="hello")
                validate_with_retry(
                    llm_call,
                    "test prompt",
                    "test_artifact",
                    self._make_config(),
                    tmp_path,
                )

        mock_fixups.assert_called_once_with(raw_output)

    def test_error_message_includes_artifact_name(self, tmp_path: Path):
        """The raised MiniLegion ValidationError should mention the artifact."""
        bad_json = '{"x": "bad"}'
        llm_call = MagicMock(return_value=bad_json)

        pydantic_exc = None
        try:
            SimpleModel.model_validate({"x": "bad", "y": "ok"})
        except PydanticValidationError as exc:
            pydantic_exc = exc

        with patch("minilegion.core.retry.validate", side_effect=pydantic_exc):
            with patch("minilegion.core.retry.save_raw_debug") as mock_debug:
                mock_debug.return_value = tmp_path / "debug.txt"
                with pytest.raises(MiniLegionValidationError, match="test_artifact"):
                    validate_with_retry(
                        llm_call,
                        "test prompt",
                        "test_artifact",
                        self._make_config(max_retries=0),
                        tmp_path,
                    )
