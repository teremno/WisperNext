from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from groq import APIConnectionError, APITimeoutError

from wispernext.application import ProviderFailureCode, TranscriptionProviderError
from wispernext.groq.transcription import (
    GroqTranscriptionTransport,
    GroqTranscriptionTransportFactory,
)
from wispernext.infrastructure.secrets import SecretValue


class FakeTranscriptions:
    def __init__(self, result: str | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return SimpleNamespace(text=self.result)


def fake_client(transcriptions: FakeTranscriptions) -> Any:
    return SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions))


def test_transport_sends_wav_with_language_and_returns_only_text() -> None:
    transcriptions = FakeTranscriptions("recognized")
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    result = transport.transcribe(b"RIFFdata", model="whisper", language="uk")

    assert result == "recognized"
    assert transcriptions.calls == [
        {
            "file": ("dictation.wav", b"RIFFdata", "audio/wav"),
            "model": "whisper",
            "language": "uk",
            "response_format": "json",
            "temperature": 0.0,
        }
    ]


def test_transport_omits_language_for_auto_detection() -> None:
    transcriptions = FakeTranscriptions("recognized")
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    transport.transcribe(b"RIFFdata", model="whisper", language=None)

    assert "language" not in transcriptions.calls[0]


@pytest.mark.parametrize(
    "sdk_error, expected",
    [
        (
            APITimeoutError(request=httpx.Request("POST", "https://api.groq.com")),
            ProviderFailureCode.TIMEOUT,
        ),
        (
            APIConnectionError(request=httpx.Request("POST", "https://api.groq.com")),
            ProviderFailureCode.UNAVAILABLE,
        ),
    ],
)
def test_transport_maps_network_failures_without_exposing_sdk_message(
    sdk_error: Exception, expected: ProviderFailureCode
) -> None:
    transport = GroqTranscriptionTransport(fake_client(FakeTranscriptions(sdk_error)))

    with pytest.raises(TranscriptionProviderError) as raised:
        transport.transcribe(b"RIFFdata", model="whisper", language=None)

    assert raised.value.code is expected
    assert str(raised.value) == expected.value


def test_factory_configures_bounded_timeout_and_one_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_groq(**kwargs: object) -> Any:
        captured.update(kwargs)
        return fake_client(FakeTranscriptions("unused"))

    monkeypatch.setattr("wispernext.groq.transcription.Groq", fake_groq)

    GroqTranscriptionTransportFactory().create(SecretValue("secret"))

    assert captured["api_key"] == "secret"
    assert captured["max_retries"] == 1
    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 3.0
    assert timeout.read == 15.0
    assert timeout.write == 10.0
