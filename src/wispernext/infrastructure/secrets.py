"""Secret lookup contracts that keep credentials out of application settings."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol

GROQ_API_KEY_ENV: Final = "WISPER_GROQ_API_KEY"


@dataclass(frozen=True, slots=True)
class SecretValue:
    """Opaque secret wrapper whose representation never exposes its value."""

    _value: str

    def reveal(self) -> str:
        """Reveal the value only at the provider call boundary."""
        return self._value

    def __repr__(self) -> str:
        return "SecretValue(**redacted**)"


class SecretProvider(Protocol):
    """Read secrets from a user-controlled secure source."""

    def get_groq_api_key(self) -> SecretValue | None:
        """Return the configured Groq key without logging or persistence."""
        ...


class EnvironmentSecretProvider:
    """Read the Groq key from the process environment without persisting it."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = os.environ if environ is None else environ

    def get_groq_api_key(self) -> SecretValue | None:
        value = self._environ.get(GROQ_API_KEY_ENV)
        if value is None or not value.strip():
            return None
        return SecretValue(value.strip())
