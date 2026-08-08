import pytest

from wispernext.infrastructure.secrets import (
    GROQ_CREDENTIAL_TARGET,
    ChainedSecretProvider,
    CredentialManagerSecretProvider,
    EnvironmentSecretProvider,
    SecretStorageError,
    SecretValue,
)


class FakeSecretStore:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def read(self, target: str) -> bytes | None:
        return self.values.get(target)

    def write(self, target: str, value: bytes) -> None:
        self.values[target] = value

    def delete(self, target: str) -> bool:
        return self.values.pop(target, None) is not None


def test_environment_provider_returns_redacted_secret_wrapper() -> None:
    raw_key = "gsk_test-secret-value"
    provider = EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": f"  {raw_key}  "})

    secret = provider.get_groq_api_key()

    assert secret is not None
    assert secret.reveal() == raw_key
    assert raw_key not in repr(secret)
    assert "redacted" in repr(secret).lower()


def test_environment_provider_treats_missing_or_blank_key_as_unconfigured() -> None:
    assert EnvironmentSecretProvider({}).get_groq_api_key() is None
    assert EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": "   "}).get_groq_api_key() is None


def test_credential_provider_persists_replaces_reads_and_deletes_opaque_key() -> None:
    store = FakeSecretStore()
    provider = CredentialManagerSecretProvider(store)

    provider.save_groq_api_key(SecretValue("first"))
    provider.save_groq_api_key(SecretValue("second"))
    loaded = provider.get_groq_api_key()

    assert store.values == {GROQ_CREDENTIAL_TARGET: b"second"}
    assert loaded is not None
    assert loaded.reveal() == "second"
    assert provider.delete_groq_api_key()
    assert provider.get_groq_api_key() is None
    assert not provider.delete_groq_api_key()


def test_credential_provider_rejects_invalid_stored_text_without_exposing_it() -> None:
    store = FakeSecretStore()
    store.values[GROQ_CREDENTIAL_TARGET] = b"\xffsecret"

    with pytest.raises(SecretStorageError) as raised:
        CredentialManagerSecretProvider(store).get_groq_api_key()

    assert "secret" not in str(raised.value)


def test_chained_provider_prefers_credential_manager_then_falls_back_to_environment() -> None:
    store = FakeSecretStore()
    credential_provider = CredentialManagerSecretProvider(store)
    environment_provider = EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": "environment"})
    chained = ChainedSecretProvider(credential_provider, environment_provider)

    fallback = chained.get_groq_api_key()
    credential_provider.save_groq_api_key(SecretValue("credential"))
    preferred = chained.get_groq_api_key()

    assert fallback is not None and fallback.reveal() == "environment"
    assert preferred is not None and preferred.reveal() == "credential"
