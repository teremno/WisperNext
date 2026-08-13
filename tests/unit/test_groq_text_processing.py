import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from groq import APITimeoutError

from wispernext.application import (
    ProviderFailureCode,
    TextProcessingMode,
    TextProcessingProviderError,
)
from wispernext.groq.text_processing import (
    GroqTextProcessingTransport,
    GroqTextProcessingTransportFactory,
)
from wispernext.infrastructure.config import LanguageCode
from wispernext.infrastructure.secrets import SecretValue


class FakeCompletions:
    def __init__(self, result: str | Exception) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        message = SimpleNamespace(content=self.result)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_client(completions: FakeCompletions) -> Any:
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_transport_uses_schema_bound_capped_translation_request() -> None:
    completions = FakeCompletions('{"text":"Hello","language":"en"}')
    transport = GroqTextProcessingTransport(fake_client(completions))

    result = transport.process(
        "Привіт",
        model="openai/gpt-oss-120b",
        mode=TextProcessingMode.TRANSLATE,
        target_language=LanguageCode.ENGLISH,
    )

    assert result.text == "Hello"
    assert result.language == "en"
    call = completions.calls[0]
    assert call["model"] == "openai/gpt-oss-120b"
    assert call["reasoning_effort"] == "low"
    assert call["temperature"] == 0.1
    assert call["max_completion_tokens"] == 256
    response_format = call["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    messages = call["messages"]
    assert isinstance(messages, list)
    assert "Привіт" not in messages[0]["content"]
    assert json.loads(messages[1]["content"])["transcript"] == "Привіт"


@pytest.mark.parametrize("target_language", list(LanguageCode))
def test_transport_supports_every_configured_translation_target(
    target_language: LanguageCode,
) -> None:
    payload = json.dumps({"text": "translated", "language": target_language.value})
    transport = GroqTextProcessingTransport(fake_client(FakeCompletions(payload)))

    result = transport.process(
        "source",
        model="openai/gpt-oss-120b",
        mode=TextProcessingMode.TRANSLATE,
        target_language=target_language,
    )

    assert result.language == target_language.value


def test_transport_maps_timeout_without_exposing_provider_message() -> None:
    timeout = APITimeoutError(request=httpx.Request("POST", "https://api.groq.com"))
    transport = GroqTextProcessingTransport(fake_client(FakeCompletions(timeout)))

    with pytest.raises(TextProcessingProviderError) as raised:
        transport.process(
            "text",
            model="model",
            mode=TextProcessingMode.FORMAT,
            target_language=None,
        )

    assert raised.value.code is ProviderFailureCode.TIMEOUT
    assert str(raised.value) == "timeout"


def test_transport_rejects_non_schema_payload() -> None:
    transport = GroqTextProcessingTransport(fake_client(FakeCompletions("not json")))

    with pytest.raises(TextProcessingProviderError) as raised:
        transport.process(
            "text",
            model="model",
            mode=TextProcessingMode.FORMAT,
            target_language=None,
        )

    assert raised.value.code is ProviderFailureCode.UNEXPECTED


def test_factory_configures_bounded_timeout_and_one_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_groq(**kwargs: object) -> Any:
        captured.update(kwargs)
        return fake_client(FakeCompletions("unused"))

    monkeypatch.setattr("wispernext.groq.text_processing.Groq", fake_groq)

    GroqTextProcessingTransportFactory().create(SecretValue("secret"))

    assert captured["api_key"] == "secret"
    assert captured["max_retries"] == 1
    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 3.0
    assert timeout.read == 20.0
    assert timeout.write == 10.0
