"""Validated transcription use case with no provider-specific details."""

from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from wispernext.application.transcription_hints import transcription_prompt
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
# Groq resamples with a proper anti-aliasing filter, so native audio is sent while it
# fits under the 25 MB free-tier upload limit.
MAX_NATIVE_UPLOAD_BYTES = 24 * 1024 * 1024


class ProviderFailureCode(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    INVALID_OUTPUT = "invalid_output"
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
    INVALID_OUTPUT = "invalid_output"
    EMPTY_RESPONSE = "empty_response"
    UNEXPECTED = "unexpected"


class TranscriptionProviderError(RuntimeError):
    """Privacy-safe provider failure carrying only an internal category."""

    def __init__(self, code: ProviderFailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class TranscriptionTransport(Protocol):
    def close(self) -> None: ...

    def transcribe(
        self, wav_bytes: bytes, *, model: str, language: str | None, prompt: str | None
    ) -> str: ...


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

        try:
            api_key = self._secret_provider.get_groq_api_key()
            if api_key is None:
                return TranscriptionResult(
                    None, TranscriptionFailureCode.MISSING_API_KEY, validation
                )
            wav_bytes = encode_pcm16_wav(_provider_audio(audio))
            with closing(self._transport_factory.create(api_key)) as transport:
                text = transport.transcribe(
                    wav_bytes,
                    model=model,
                    language=_provider_language(language),
                    prompt=transcription_prompt(language),
                ).strip()
        except TranscriptionProviderError as exc:
            return TranscriptionResult(None, _map_provider_failure(exc.code), validation)
        except Exception:
            return TranscriptionResult(None, TranscriptionFailureCode.UNEXPECTED, validation)
        if not text:
            return TranscriptionResult(None, TranscriptionFailureCode.EMPTY_RESPONSE, validation)
        return TranscriptionResult(text, None, validation)


def _provider_audio(audio: CapturedAudio) -> CapturedAudio:
    native_bytes = 44 + 2 * len(audio.samples)
    if audio.sample_rate >= TRANSCRIPTION_SAMPLE_RATE and native_bytes <= MAX_NATIVE_UPLOAD_BYTES:
        return audio
    return resample_mono(audio, TRANSCRIPTION_SAMPLE_RATE)


def _provider_language(language: LanguageCode | None) -> str | None:
    if language is LanguageCode.CHINESE_SIMPLIFIED:
        return "zh"
    return language.value if language is not None else None


def _map_provider_failure(code: ProviderFailureCode) -> TranscriptionFailureCode:
    return TranscriptionFailureCode(code.value)
