"""Tests for minilegion.core.exceptions — exception hierarchy."""

import pytest

from minilegion.core.exceptions import (
    ApprovalError,
    ConfigError,
    FileIOError,
    InvalidTransitionError,
    LLMError,
    MiniLegionError,
    PreflightError,
    StateError,
    ValidationError,
)


ALL_EXCEPTIONS = [
    StateError,
    ConfigError,
    ValidationError,
    LLMError,
    PreflightError,
    ApprovalError,
    FileIOError,
]


class TestExceptionHierarchy:
    """Test that all exception classes form the correct hierarchy."""

    @pytest.mark.parametrize("exc_class", ALL_EXCEPTIONS)
    def test_subclass_of_minilegion_error(self, exc_class):
        """Each exception is a subclass of MiniLegionError."""
        assert issubclass(exc_class, MiniLegionError)

    def test_invalid_transition_is_subclass_of_state_error(self):
        """InvalidTransitionError inherits from StateError."""
        assert issubclass(InvalidTransitionError, StateError)

    def test_invalid_transition_is_subclass_of_minilegion_error(self):
        """InvalidTransitionError is also a MiniLegionError (transitive)."""
        assert issubclass(InvalidTransitionError, MiniLegionError)

    @pytest.mark.parametrize("exc_class", ALL_EXCEPTIONS)
    def test_catching_minilegion_error_catches_subcategory(self, exc_class):
        """Catching MiniLegionError catches all subcategories."""
        with pytest.raises(MiniLegionError):
            raise exc_class("test message")

    @pytest.mark.parametrize("exc_class", ALL_EXCEPTIONS + [InvalidTransitionError])
    def test_exception_carries_message(self, exc_class):
        """Each exception carries its message correctly."""
        msg = f"Test message for {exc_class.__name__}"
        exc = exc_class(msg)
        assert str(exc) == msg

    def test_catching_state_error_catches_invalid_transition(self):
        """StateError catch block catches InvalidTransitionError."""
        with pytest.raises(StateError):
            raise InvalidTransitionError("cannot transition")
