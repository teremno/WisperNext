"""Verify Credential Manager authentication without exposing secret or provider details."""

import json

import httpx
from groq import Groq

from wispernext.infrastructure.secrets import CredentialManagerSecretProvider
from wispernext.infrastructure.windows_credentials import WindowsCredentialStore


def main() -> int:
    secret = CredentialManagerSecretProvider(WindowsCredentialStore()).get_groq_api_key()
    if secret is None:
        print(json.dumps({"status": "credential_missing"}))
        return 2
    try:
        client = Groq(
            api_key=secret.reveal(),
            timeout=httpx.Timeout(10.0, connect=3.0),
            max_retries=0,
        )
        models = client.models.list()
    except Exception:
        print(json.dumps({"status": "groq_verification_failed"}))
        return 3
    print(json.dumps({"status": "credential_only_groq_ok", "models_visible": len(models.data)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
