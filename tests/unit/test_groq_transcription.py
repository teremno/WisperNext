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
    def __init__(self, result: str | Exception, segments: list[object] | None = None) -> None:
        self.result = result
        self.segments = segments
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return SimpleNamespace(text=self.result, segments=self.segments)


def fake_client(transcriptions: FakeTranscriptions) -> Any:
    return SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions))


def test_transport_sends_wav_with_language_and_prompt_and_returns_only_text() -> None:
    transcriptions = FakeTranscriptions("recognized")
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    result = transport.transcribe(b"RIFFdata", model="whisper", language="uk", prompt="Привіт.")

    assert result == "recognized"
    assert transcriptions.calls == [
        {
            "file": ("dictation.wav", b"RIFFdata", "audio/wav"),
            "model": "whisper",
            "language": "uk",
            "prompt": "Привіт.",
            "response_format": "verbose_json",
            "temperature": 0.0,
        }
    ]


def test_transport_omits_language_and_prompt_when_absent() -> None:
    transcriptions = FakeTranscriptions("recognized")
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    transport.transcribe(b"RIFFdata", model="whisper", language=None, prompt=None)

    assert "language" not in transcriptions.calls[0]
    assert "prompt" not in transcriptions.calls[0]


def segment(text: str, *, no_speech: float = 0.01, log_probability: float = -0.2) -> object:
    return {"text": text, "no_speech_prob": no_speech, "avg_logprob": log_probability}


def test_transport_drops_segments_decoded_from_silence() -> None:
    transcriptions = FakeTranscriptions(
        " Завтра зустрінемось. Дякую за перегляд!",
        [
            segment(" Завтра зустрінемось."),
            segment(" Дякую за перегляд!", no_speech=0.9, log_probability=-1.4),
        ],
    )
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    result = transport.transcribe(b"RIFFdata", model="whisper", language="uk", prompt=None)

    assert result == "Завтра зустрінемось."


def test_transport_keeps_quiet_but_confident_speech() -> None:
    transcriptions = FakeTranscriptions(
        " Так.", [segment(" Так.", no_speech=0.9, log_probability=-0.3)]
    )
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    assert transport.transcribe(b"RIFF", model="whisper", language="uk", prompt=None) == "Так."


def test_transport_drops_an_echoed_prompt_but_keeps_a_short_matching_reply() -> None:
    prompt = "Привіт. Я зараз диктую текст українською мовою."
    transcriptions = FakeTranscriptions(
        "unused",
        [segment(" Привіт."), segment(" Я зараз диктую текст українською мовою.")],
    )
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    result = transport.transcribe(b"RIFF", model="whisper", language="uk", prompt=prompt)

    assert result == "Привіт."


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
        transport.transcribe(b"RIFFdata", model="whisper", language=None, prompt=None)

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


def test_transport_drops_a_confident_subtitle_line_after_real_speech() -> None:
    transcriptions = FakeTranscriptions(
        "unused",
        [segment(" Завтра зустрінемось."), segment(" Дякую за перегляд!", no_speech=0.35)],
    )
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    result = transport.transcribe(b"RIFF", model="whisper", language="uk", prompt=None)

    assert result == "Завтра зустрінемось."


def test_transport_keeps_a_subtitle_like_phrase_when_it_is_the_whole_dictation() -> None:
    transcriptions = FakeTranscriptions("unused", [segment(" Дякую за перегляд.")])
    transport = GroqTranscriptionTransport(fake_client(transcriptions))

    result = transport.transcribe(b"RIFF", model="whisper", language="uk", prompt=None)

    assert result == "Дякую за перегляд."
