from wispernext.infrastructure.secrets import EnvironmentSecretProvider


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
