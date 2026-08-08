"""Copy an existing process Groq key into Windows Credential Manager safely."""

import hmac
import json

from wispernext.infrastructure.secrets import (
    GROQ_CREDENTIAL_TARGET,
    CredentialManagerSecretProvider,
    EnvironmentSecretProvider,
)
from wispernext.infrastructure.windows_credentials import WindowsCredentialStore


def main() -> int:
    source = EnvironmentSecretProvider().get_groq_api_key()
    if source is None:
        print(json.dumps({"status": "source_key_missing"}))
        return 2

    provider = CredentialManagerSecretProvider(WindowsCredentialStore())
    provider.save_groq_api_key(source)
    stored = provider.get_groq_api_key()
    verified = stored is not None and hmac.compare_digest(source.reveal(), stored.reveal())
    print(
        json.dumps(
            {
                "status": "stored_and_verified" if verified else "verification_failed",
                "target": GROQ_CREDENTIAL_TARGET,
            }
        )
    )
    return 0 if verified else 3


if __name__ == "__main__":
    raise SystemExit(main())
