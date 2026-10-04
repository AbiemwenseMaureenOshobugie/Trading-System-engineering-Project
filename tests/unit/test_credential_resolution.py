"""MS-0.24 external credential-resolution tests."""

import pytest

from trading_system.application import CredentialResolverPort
from trading_system.runtime import (
    CredentialResolutionError,
    EnvironmentCredentialResolver,
    UnsupportedCredentialReference,
)


def test_environment_resolver_implements_credential_port():
    resolver = EnvironmentCredentialResolver({"ASTER_KEY": "secret-value"})
    assert isinstance(resolver, CredentialResolverPort)


def test_env_reference_resolves_value():
    resolver = EnvironmentCredentialResolver({"TWELVE_DATA_API_KEY": "test-key"})
    assert resolver.resolve("env:TWELVE_DATA_API_KEY") == "test-key"


def test_missing_environment_variable_fails_closed():
    resolver = EnvironmentCredentialResolver({})
    with pytest.raises(CredentialResolutionError) as exc_info:
        resolver.resolve("env:TWELVE_DATA_API_KEY")
    assert str(exc_info.value) == "unresolved credential reference: env:TWELVE_DATA_API_KEY"


def test_empty_environment_variable_fails_closed():
    resolver = EnvironmentCredentialResolver({"TWELVE_DATA_API_KEY": "   "})
    with pytest.raises(CredentialResolutionError):
        resolver.resolve("env:TWELVE_DATA_API_KEY")


@pytest.mark.parametrize(
    "reference",
    ["vault:TWELVE_DATA_API_KEY", "aws:TWELVE_DATA_API_KEY",
     "secret://TWELVE_DATA_API_KEY", "", "env:", "TWELVE_DATA_API_KEY"],
)
def test_unsupported_reference_schemes_are_rejected(reference):
    resolver = EnvironmentCredentialResolver({"TWELVE_DATA_API_KEY": "secret-value"})
    with pytest.raises(UnsupportedCredentialReference):
        resolver.resolve(reference)


def test_credential_value_is_not_in_resolution_failure():
    secret = "super-secret-value"
    resolver = EnvironmentCredentialResolver({"TWELVE_DATA_API_KEY": secret})
    with pytest.raises(UnsupportedCredentialReference) as exc_info:
        resolver.resolve("vault:TWELVE_DATA_API_KEY")
    assert secret not in str(exc_info.value)
