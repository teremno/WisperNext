"""Groq SDK adapter for bounded speech-to-text requests."""

from collections.abc import Mapping
from typing import Any

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
from wispernext.application.text_fidelity import lexical_tokens
from wispernext.infrastructure.secrets import SecretValue

# Whisper's own thresholds for a segment decoded from silence or background noise.
_NO_SPEECH_PROBABILITY = 0.6
_LOW_AVERAGE_LOG_PROBABILITY = -1.0
_MINIMUM_ECHO_WORDS = 4
# Whisper learned these closing lines from video subtitles and appends them to trailing
# silence with high confidence. They are dropped only after other speech.
_SUBTITLE_ARTIFACTS = frozenset(
    [
        "дякую за перегляд",
        "продовження далі",
        "субтитри зроблені",
        "редактор субтитрів",
        "спасибо за просмотр",
        "продолжение следует",
        "субтитры сделал",
        "thank you for watching",
        "thanks for watching",
    ]
)


class GroqTranscriptionTransport:
    """Map the official SDK response and failures into the internal contract."""

    def __init__(self, client: Groq) -> None:
        self._client = client

    def close(self) -> None:
        """Release the per-recording HTTP connection pool deterministically."""
        self._client.close()

    def transcribe(
        self, wav_bytes: bytes, *, model: str, language: str | None, prompt: str | None
    ) -> str:
        options: dict[str, Any] = {}
        if language is not None:
            options["language"] = language
        if prompt is not None:
            options["prompt"] = prompt
        try:
            response = self._client.audio.transcriptions.create(
                file=("dictation.wav", wav_bytes, "audio/wav"),
                model=model,
                response_format="verbose_json",
                temperature=0.0,
                **options,
            )
            return _speech_text(response, prompt)
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


def _speech_text(response: Any, prompt: str | None) -> str:
    """Drop segments Whisper decoded from silence and segments that echo the prompt."""
    segments = getattr(response, "segments", None)
    if not isinstance(segments, list) or not segments:
        return str(response.text)
    prompt_text = " ".join(lexical_tokens(prompt)) if prompt else ""
    kept: list[str] = []
    for segment in segments:
        text = str(_field(segment, "text") or "")
        no_speech = _number(_field(segment, "no_speech_prob"), 0.0)
        log_probability = _number(_field(segment, "avg_logprob"), 0.0)
        if no_speech > _NO_SPEECH_PROBABILITY and log_probability < _LOW_AVERAGE_LOG_PROBABILITY:
            continue
        tokens = lexical_tokens(text)
        # A real short reply such as "Привіт." may match the prompt; an echo is longer.
        if len(tokens) >= _MINIMUM_ECHO_WORDS and " ".join(tokens) in prompt_text:
            continue
        if text.strip():
            kept.append(text.strip())
    while len(kept) > 1 and " ".join(lexical_tokens(kept[-1])) in _SUBTITLE_ARTIFACTS:
        kept.pop()
    return " ".join(kept)


def _field(segment: object, name: str) -> object:
    if isinstance(segment, Mapping):
        return segment.get(name)
    return getattr(segment, name, None)


def _number(value: object, default: float) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return default


class GroqTranscriptionTransportFactory:
    """Create short-lived SDK clients only when valid audio is ready to send."""

    def create(self, api_key: SecretValue) -> GroqTranscriptionTransport:
        timeout = httpx.Timeout(20.0, connect=3.0, read=15.0, write=10.0)
        client = Groq(api_key=api_key.reveal(), timeout=timeout, max_retries=1)
        return GroqTranscriptionTransport(client)
