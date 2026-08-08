"""Groq SDK adapter for bounded speech-to-text requests."""

import httpx
from groq import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    Groq,
    PermissionDeniedError,
    RateLimitError,
)

from wispernext.application import ProviderFailureCode, TranscriptionProviderError
from wispernext.infrastructure.secrets import SecretValue


class GroqTranscriptionTransport:
    """Map the official SDK response and failures into the internal contract."""

    def __init__(self, client: Groq) -> None:
        self._client = client

    def transcribe(self, wav_bytes: bytes, *, model: str, language: str | None) -> str:
        try:
            if language is None:
                response = self._client.audio.transcriptions.create(
                    file=("dictation.wav", wav_bytes, "audio/wav"),
                    model=model,
                    response_format="json",
                    temperature=0.0,
                )
            else:
                response = self._client.audio.transcriptions.create(
                    file=("dictation.wav", wav_bytes, "audio/wav"),
                    model=model,
                    language=language,
                    response_format="json",
                    temperature=0.0,
                )
            return response.text
        except AuthenticationError as exc:
            raise TranscriptionProviderError(ProviderFailureCode.AUTHENTICATION) from exc
        except PermissionDeniedError as exc:
            raise TranscriptionProviderError(ProviderFailureCode.PERMISSION_DENIED) from exc
        except RateLimitError as exc:
            raise TranscriptionProviderError(ProviderFailureCode.RATE_LIMITED) from exc
        except APITimeoutError as exc:
            raise TranscriptionProviderError(ProviderFailureCode.TIMEOUT) from exc
        except APIConnectionError as exc:
            raise TranscriptionProviderError(ProviderFailureCode.UNAVAILABLE) from exc
        except BadRequestError as exc:
            raise TranscriptionProviderError(ProviderFailureCode.INVALID_REQUEST) from exc
        except Exception as exc:
            raise TranscriptionProviderError(ProviderFailureCode.UNEXPECTED) from exc


class GroqTranscriptionTransportFactory:
    """Create short-lived SDK clients only when valid audio is ready to send."""

    def create(self, api_key: SecretValue) -> GroqTranscriptionTransport:
        timeout = httpx.Timeout(20.0, connect=3.0, read=15.0, write=10.0)
        client = Groq(api_key=api_key.reveal(), timeout=timeout, max_retries=1)
        return GroqTranscriptionTransport(client)
