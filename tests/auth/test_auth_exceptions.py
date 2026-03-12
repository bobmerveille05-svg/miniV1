from minilegion.core.exceptions import (
    AuthError,
    AuthExpiredError,
    AuthProviderError,
    AuthNotConfiguredError,
    MiniLegionError,
)


def test_auth_error_is_minilegion_error():
    assert issubclass(AuthError, MiniLegionError)


def test_auth_expired_is_auth_error():
    err = AuthExpiredError("copilot")
    assert isinstance(err, AuthError)
    assert "copilot" in str(err)


def test_auth_provider_error_is_auth_error():
    err = AuthProviderError("network failure")
    assert isinstance(err, AuthError)


def test_auth_not_configured_is_auth_error():
    err = AuthNotConfiguredError("copilot")
    assert isinstance(err, AuthError)
    assert "copilot" in str(err)
