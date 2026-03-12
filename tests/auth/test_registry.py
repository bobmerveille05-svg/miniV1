import pytest
from minilegion.auth.registry import get_provider, PROVIDERS
from minilegion.auth.base import AuthProvider


def test_providers_dict_has_copilot():
    assert "copilot" in PROVIDERS


def test_get_provider_copilot_returns_auth_provider():
    provider = get_provider("copilot")
    assert isinstance(provider, AuthProvider)


def test_get_provider_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown auth provider"):
        get_provider("unknown-provider")


def test_auth_provider_is_abstract():
    # Cannot instantiate directly
    with pytest.raises(TypeError):
        AuthProvider()
