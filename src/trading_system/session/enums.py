"""Enumerations for the MS-0.8 session policy contract."""

from enum import StrEnum


class SessionIdentity(StrEnum):
    """Canonical UTC session identity."""

    ASIAN = "ASIAN"
    LONDON = "LONDON"
    LONDON_NEW_YORK_OVERLAP = "LONDON_NEW_YORK_OVERLAP"
    NEW_YORK = "NEW_YORK"
    OUTSIDE_SESSION = "OUTSIDE_SESSION"
