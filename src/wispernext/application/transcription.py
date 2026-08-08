"""Validated transcription use case with no provider-specific details."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from wispernext.audio.signal import (
    AudioCategory,
    AudioValidation,
    CapturedAudio,
    resample_mono,
    validate_audio,
)
from wispernext.audio.wav import encode_pcm16_wav
from wispernext.infrastructure.config import LanguageCode
from wispernext.infrastructure.secrets import SecretProvider, SecretValue

TRANSCRIPTION_SAMPLE_RATE = 16_000


class ProviderFailureCode(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    UNEXPECTED = "unexpected"


class TranscriptionFailureCode(StrEnum):
    INVALID_AUDIO = "invalid_audio"
    MISSING_API_KEY = "missing_api_key"
    AUTHENTICATION = "authentication"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    EMPTY_RESPONSE = "empty_response"
    UNEXPECTED = "unexpected"


class TranscriptionProviderError(RuntimeError):
    """Privacy-safe provider failure carrying only an internal category."""

    def __init__(self, code: ProviderFailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class TranscriptionTransport(Protocol):
    def transcribe(self, wav_bytes: bytes, *, model: str, language: str | None) -> str: ...


class TranscriptionTransportFactory(Protocol):
    def create(self, api_key: SecretValue) -> TranscriptionTransport: ...


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    text: str | None
    failure: TranscriptionFailureCode | None
    validation: AudioValidation

    @property
    def succeeded(self) -> bool:
        return self.failure is None


class TranscriptionService:
    """Validate audio, resolve a secret lazily, and invoke one provider request."""

    def __init__(
        self,
        secret_provider: SecretProvider,
        transport_factory: TranscriptionTransportFactory,
    ) -> None:
        self._secret_provider = secret_provider
        self._transport_factory = transport_factory

    def transcribe(
        self,
        audio: CapturedAudio,
        *,
        model: str,
        language: LanguageCode | None,
    ) -> TranscriptionResult:
        validation = validate_audio(audio)
        if validation.category is not AudioCategory.VALID_AUDIO:
            return TranscriptionResult(None, TranscriptionFailureCode.INVALID_AUDIO, validation)

        api_key = self._secret_provider.get_groq_api_key()
        if api_key is None:
            return TranscriptionResult(None, TranscriptionFailureCode.MISSING_API_KEY, validation)

        normalized = resample_mono(audio, TRANSCRIPTION_SAMPLE_RATE)
        wav_bytes = encode_pcm16_wav(normalized)
        transport = self._transport_factory.create(api_key)
        try:
            text = transport.transcribe(
                wav_bytes,
                model=model,
                language=_provider_language(language),
            ).strip()
        except TranscriptionProviderError as exc:
            return TranscriptionResult(None, _map_provider_failure(exc.code), validation)
        if not text:
            return TranscriptionResult(None, TranscriptionFailureCode.EMPTY_RESPONSE, validation)
        return TranscriptionResult(text, None, validation)


def _provider_language(language: LanguageCode | None) -> str | None:
    if language is LanguageCode.CHINESE_SIMPLIFIED:
        return "zh"
    return language.value if language is not None else None


def _map_provider_failure(code: ProviderFailureCode) -> TranscriptionFailureCode:
    return TranscriptionFailureCode(code.value)
