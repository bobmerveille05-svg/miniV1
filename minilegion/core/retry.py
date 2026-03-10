"""Retry logic with error feedback and RAW_DEBUG capture.

Provides validate_with_retry which:
1. Calls an LLM callable to get raw output
2. Applies pre-parse fixups (BOM, fences, trailing commas)
3. Validates against the schema registry
4. On failure, retries with human-readable error feedback
5. After max retries, saves raw output to debug file and raises

Usage::

    from minilegion.core.retry import validate_with_retry

    result = validate_with_retry(
        llm_call=my_llm_callable,
        prompt="Generate research...",
        artifact_name="research",
        config=config,
        project_dir=project_dir,
    )
"""

from datetime import datetime
from pathlib import Path
from typing import Callable

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from minilegion.core.config import MiniLegionConfig
from minilegion.core.exceptions import ValidationError
from minilegion.core.file_io import write_atomic
from minilegion.core.fixups import apply_fixups
from minilegion.core.registry import validate


def summarize_errors(exc: PydanticValidationError) -> str:
    """Convert a Pydantic ValidationError into a human-readable summary.

    Extracts field-level errors and formats them as concise sentences.
    Caps at 5 issues to keep feedback manageable for LLM retry prompts.

    Args:
        exc: A Pydantic ValidationError instance.

    Returns:
        Human-readable summary string, e.g.:
        "Validation failed with 3 error(s). Issues: 'x': Input should be a
        valid integer; 'y': Field required."
    """
    errors = exc.errors()
    total = len(errors)
    capped = errors[:5]

    issues = []
    for err in capped:
        # Build field path from loc tuple (e.g., ("field", 0, "subfield") -> "field.0.subfield")
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "unknown error")
        issues.append(f"'{loc}': {msg}")

    summary = f"Validation failed with {total} error(s). Issues: {'; '.join(issues)}."

    if total > 5:
        summary += f" (and {total - 5} more)"

    return summary


def save_raw_debug(
    artifact_name: str,
    raw_output: str,
    error_summary: str,
    project_dir: Path,
) -> Path:
    """Save raw LLM output and validation errors to a debug file.

    Creates a timestamped debug file in project-ai/debug/ for post-mortem
    analysis when validation retries are exhausted.

    Args:
        artifact_name: Name of the artifact being validated.
        raw_output: The raw LLM output that failed validation.
        error_summary: Human-readable error summary from summarize_errors.
        project_dir: Root directory of the project.

    Returns:
        Path to the created debug file.
    """
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"{artifact_name.upper()}_RAW_DEBUG_{timestamp}.txt"
    debug_path = project_dir / "project-ai" / "debug" / filename

    content = (
        f"=== RAW LLM OUTPUT ===\n"
        f"{raw_output}\n"
        f"\n"
        f"=== VALIDATION ERRORS ===\n"
        f"{error_summary}\n"
    )

    write_atomic(debug_path, content)
    return debug_path


def validate_with_retry(
    llm_call: Callable[[str], str],
    prompt: str,
    artifact_name: str,
    config: MiniLegionConfig,
    project_dir: Path,
) -> BaseModel:
    """Call LLM, validate output, retry with error feedback on failure.

    Flow:
    1. Call llm_call(prompt) to get raw output
    2. Apply fixups (BOM, fences, trailing commas)
    3. Validate against schema registry
    4. On success: return validated model
    5. On failure: build error feedback, retry with augmented prompt
    6. After max retries: save debug file, raise ValidationError

    Args:
        llm_call: Callable that takes a prompt string, returns raw LLM output.
        prompt: The initial prompt to send to the LLM.
        artifact_name: Name of the artifact schema to validate against.
        config: MiniLegionConfig with max_retries setting.
        project_dir: Root directory for debug file output.

    Returns:
        Validated Pydantic model instance.

    Raises:
        minilegion.core.exceptions.ValidationError: After exhausting retries.
    """
    current_prompt = prompt
    last_raw_output = ""
    last_error_summary = ""

    for attempt in range(1 + config.max_retries):
        # Step 1: Call LLM
        raw_output = llm_call(current_prompt)
        last_raw_output = raw_output

        # Step 2: Apply fixups
        cleaned = apply_fixups(raw_output)

        # Step 3: Try validation
        try:
            return validate(artifact_name, cleaned)
        except PydanticValidationError as exc:
            # Step 5: Build error feedback
            error_summary = summarize_errors(exc)
            last_error_summary = error_summary

            # Step 6: Construct retry prompt with error feedback
            current_prompt = (
                f"{prompt}\n\n"
                f"--- VALIDATION ERROR ---\n"
                f"Your previous output was invalid. "
                f"Here is what you got wrong:\n"
                f"{error_summary}\n\n"
                f"Please output valid JSON matching the schema."
            )

    # Step 8: Exhausted retries — save debug and raise
    debug_path = save_raw_debug(
        artifact_name, last_raw_output, last_error_summary, project_dir
    )

    raise ValidationError(
        f"Validation failed for '{artifact_name}' after {config.max_retries} "
        f"retries. Last errors: {last_error_summary}. "
        f"Debug saved to: {debug_path}"
    )
