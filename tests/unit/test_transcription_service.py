from dataclasses import dataclass

import pytest

from wispernext.application import (
    ProviderFailureCode,
    TranscriptionFailureCode,
    TranscriptionProviderError,
    TranscriptionService,
)
from wispernext.audio.signal import AudioCategory, CapturedAudio
from wispernext.infrastructure.config import LanguageCode
from wispernext.infrastructure.secrets import EnvironmentSecretProvider, SecretValue


class FakeTransport:
    def __init__(
        self,
        *,
        text: str = "recognized",
        failure: ProviderFailureCode | None = None,
    ) -> None:
        self.text = text
        self.failure = failure
        self.calls: list[tuple[bytes, str, str | None]] = []

    def transcribe(self, wav_bytes: bytes, *, model: str, language: str | None) -> str:
        self.calls.append((wav_bytes, model, language))
        if self.failure is not None:
            raise TranscriptionProviderError(self.failure)
        return self.text


@dataclass
class FakeFactory:
    transport: FakeTransport
    create_count: int = 0
    revealed_keys: list[str] | None = None

    def create(self, api_key: SecretValue) -> FakeTransport:
        self.create_count += 1
        if self.revealed_keys is None:
            self.revealed_keys = []
        self.revealed_keys.append(api_key.reveal())
        return self.transport


def valid_audio(sample_rate: int = 48_000) -> CapturedAudio:
    return CapturedAudio(
        tuple(0.1 if index % 2 else -0.1 for index in range(sample_rate)), sample_rate
    )


@pytest.mark.parametrize(
    "audio, category",
    [
        (CapturedAudio((), 48_000), AudioCategory.NO_AUDIO_FRAMES),
        (CapturedAudio((0.1,) * 10, 48_000), AudioCategory.TOO_SHORT),
        (CapturedAudio((0.0001,) * 48_000, 48_000), AudioCategory.WEAK_SIGNAL),
        (CapturedAudio((1.0,) * 48_000, 48_000), AudioCategory.CLIPPED_SIGNAL),
    ],
)
def test_invalid_audio_causes_zero_secret_reads_and_zero_provider_calls(
    audio: CapturedAudio, category: AudioCategory
) -> None:
    transport = FakeTransport()
    factory = FakeFactory(transport)
    service = TranscriptionService(EnvironmentSecretProvider({}), factory)

    result = service.transcribe(audio, model="whisper-large-v3-turbo", language=None)

    assert result.failure is TranscriptionFailureCode.INVALID_AUDIO
    assert result.validation.category is category
    assert factory.create_count == 0
    assert transport.calls == []


def test_missing_key_causes_zero_provider_calls() -> None:
    factory = FakeFactory(FakeTransport())
    service = TranscriptionService(EnvironmentSecretProvider({}), factory)

    result = service.transcribe(valid_audio(), model="whisper-large-v3-turbo", language=None)

    assert result.failure is TranscriptionFailureCode.MISSING_API_KEY
    assert factory.create_count == 0


def test_valid_audio_is_resampled_encoded_and_transcribed_once() -> None:
    transport = FakeTransport(text="  Привіт  ")
    factory = FakeFactory(transport)
    service = TranscriptionService(
        EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": "secret"}), factory
    )

    result = service.transcribe(
        valid_audio(),
        model="whisper-large-v3-turbo",
        language=LanguageCode.UKRAINIAN,
    )

    assert result.succeeded
    assert result.text == "Привіт"
    assert factory.create_count == 1
    assert factory.revealed_keys == ["secret"]
    assert len(transport.calls) == 1
    wav_bytes, model, language = transport.calls[0]
    assert wav_bytes.startswith(b"RIFF")
    assert model == "whisper-large-v3-turbo"
    assert language == "uk"


@pytest.mark.parametrize("code", list(ProviderFailureCode))
def test_provider_failures_are_mapped_without_provider_messages(code: ProviderFailureCode) -> None:
    factory = FakeFactory(FakeTransport(failure=code))
    service = TranscriptionService(
        EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": "secret"}), factory
    )

    result = service.transcribe(valid_audio(), model="model", language=None)

    assert result.failure is TranscriptionFailureCode(code.value)
    assert result.text is None


def test_empty_provider_response_is_not_reported_as_success() -> None:
    factory = FakeFactory(FakeTransport(text="  "))
    service = TranscriptionService(
        EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": "secret"}), factory
    )

    result = service.transcribe(valid_audio(), model="model", language=None)

    assert result.failure is TranscriptionFailureCode.EMPTY_RESPONSE
