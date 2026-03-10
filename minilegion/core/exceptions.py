"""Exception hierarchy for MiniLegion.

All custom exceptions inherit from MiniLegionError, organized by category:
- StateError / InvalidTransitionError: state machine violations
- ConfigError: configuration loading or validation failures
- ValidationError: schema or data validation failures
- LLMError: LLM API call failures
- PreflightError: pre-flight check failures
- ApprovalError: approval gate rejections
- FileIOError: file read/write failures
"""


class MiniLegionError(Exception):
    """Base exception for all MiniLegion errors."""

    pass


class StateError(MiniLegionError):
    """Invalid state transition or state corruption."""

    pass


class InvalidTransitionError(StateError):
    """Attempted an invalid stage transition."""

    pass


class ConfigError(MiniLegionError):
    """Configuration loading or validation failure."""

    pass


class ValidationError(MiniLegionError):
    """Schema or data validation failure."""

    pass


class LLMError(MiniLegionError):
    """LLM API call failure."""

    pass


class PreflightError(MiniLegionError):
    """Pre-flight check failure (missing files, missing approvals)."""

    pass


class ApprovalError(MiniLegionError):
    """Approval gate rejection."""

    pass


class FileIOError(MiniLegionError):
    """File read/write failure."""

    pass
