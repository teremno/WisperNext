"""Secret lookup contracts that keep credentials out of application settings."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol

GROQ_API_KEY_ENV: Final = "WISPER_GROQ_API_KEY"
GROQ_CREDENTIAL_TARGET: Final = "WisperNext/GroqApiKey"


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


class SecretStore(Protocol):
    """Persist and retrieve an opaque secret in an operating-system store."""

    def read(self, target: str) -> bytes | None: ...

    def write(self, target: str, value: bytes) -> None: ...

    def delete(self, target: str) -> bool: ...


class EnvironmentSecretProvider:
    """Read the Groq key from the process environment without persisting it."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = os.environ if environ is None else environ

    def get_groq_api_key(self) -> SecretValue | None:
        value = self._environ.get(GROQ_API_KEY_ENV)
        if value is None or not value.strip():
            return None
        return SecretValue(value.strip())


class CredentialManagerSecretProvider:
    """Read the Groq key from a user-scoped Windows credential store."""

    def __init__(self, store: SecretStore) -> None:
        self._store = store

    def get_groq_api_key(self) -> SecretValue | None:
        encoded = self._store.read(GROQ_CREDENTIAL_TARGET)
        if encoded is None:
            return None
        try:
            value = encoded.decode("utf-8").strip()
        except UnicodeError as exc:
            raise SecretStorageError("Stored Groq credential is not valid UTF-8.") from exc
        if not value:
            return None
        return SecretValue(value)

    def save_groq_api_key(self, secret: SecretValue) -> None:
        value = secret.reveal().strip()
        if not value:
            raise ValueError("Groq API key must not be blank.")
        self._store.write(GROQ_CREDENTIAL_TARGET, value.encode("utf-8"))

    def delete_groq_api_key(self) -> bool:
        return self._store.delete(GROQ_CREDENTIAL_TARGET)


class ChainedSecretProvider:
    """Return the first configured secret without exposing provider internals."""

    def __init__(self, *providers: SecretProvider) -> None:
        self._providers = providers

    def get_groq_api_key(self) -> SecretValue | None:
        for provider in self._providers:
            secret = provider.get_groq_api_key()
            if secret is not None:
                return secret
        return None


class SecretStorageError(RuntimeError):
    """Privacy-safe failure from an operating-system credential store."""
