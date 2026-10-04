"""Runtime-bound credential resolution for ASTER.

MS-0.24 supports environment-variable credential references only. Secret
material is returned to the composition root for adapter construction and is
never represented as a domain or audit value.
"""

from __future__ import annotations

import os
from collections.abc import Mapping


class UnsupportedCredentialReference(ValueError):
    """Raised when a credential reference uses an unsupported scheme."""


class CredentialResolutionError(RuntimeError):
    """Raised when a supported credential reference cannot be resolved."""


class EnvironmentCredentialResolver:
    """Resolve canonical env:NAME references from the process environment."""

    SCHEME = "env"

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = environment if environment is not None else os.environ

    def resolve(self, reference: str) -> str:
        scheme, separator, name = reference.partition(":")
        if separator != ":" or scheme != self.SCHEME or not name:
            raise UnsupportedCredentialReference(
                f"unsupported credential reference: {reference}"
            )

        value = self._environment.get(name)
        if value is None or not value.strip():
            raise CredentialResolutionError(
                f"unresolved credential reference: {reference}"
            )

        return value
