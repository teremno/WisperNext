"""Conservative optional formatting and translation with raw-transcript fallback."""

import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Protocol

from wispernext.application.transcription import ProviderFailureCode
from wispernext.infrastructure.config import LanguageCode
from wispernext.infrastructure.secrets import SecretProvider, SecretValue


class TextProcessingMode(StrEnum):
    FORMAT = "format"
    TRANSLATE = "translate"


class TextProcessingFailureCode(StrEnum):
    MISSING_API_KEY = "missing_api_key"
    AUTHENTICATION = "authentication"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_REQUEST = "invalid_request"
    EMPTY_RESPONSE = "empty_response"
    UNSAFE_RESPONSE = "unsafe_response"
    UNEXPECTED = "unexpected"


class TextProcessingProviderError(RuntimeError):
    """Privacy-safe provider error with no transcript or credential content."""

    def __init__(self, code: ProviderFailureCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProviderTextResult:
    text: str
    language: str


class TextProcessingTransport(Protocol):
    def process(
        self,
        transcript: str,
        *,
        model: str,
        mode: TextProcessingMode,
        target_language: LanguageCode | None,
    ) -> ProviderTextResult: ...


class TextProcessingTransportFactory(Protocol):
    def create(self, api_key: SecretValue) -> TextProcessingTransport: ...


@dataclass(frozen=True, slots=True)
class TextProcessingResult:
    text: str
    transformed: bool
    used_fallback: bool
    failure: TextProcessingFailureCode | None = None


def processing_mode(
    input_language: LanguageCode | None,
    output_language: LanguageCode | None,
    safe_formatting: bool,
) -> TextProcessingMode | None:
    """Return the one optional operation required by language settings."""
    translation_required = output_language is not None and output_language != input_language
    if input_language is None and output_language is not None:
        translation_required = True
    if translation_required:
        return TextProcessingMode.TRANSLATE
    if safe_formatting:
        return TextProcessingMode.FORMAT
    return None


class TextProcessingService:
    """Call one bounded provider operation and fall back on any unsafe result."""

    def __init__(
        self,
        secret_provider: SecretProvider,
        transport_factory: TextProcessingTransportFactory,
    ) -> None:
        self._secret_provider = secret_provider
        self._transport_factory = transport_factory

    def process(
        self,
        transcript: str,
        *,
        model: str,
        input_language: LanguageCode | None,
        output_language: LanguageCode | None,
        safe_formatting: bool,
    ) -> TextProcessingResult:
        mode = processing_mode(input_language, output_language, safe_formatting)
        if mode is None:
            return TextProcessingResult(transcript, False, False)
        try:
            api_key = self._secret_provider.get_groq_api_key()
        except Exception:
            return _fallback(transcript, TextProcessingFailureCode.UNEXPECTED)
        if api_key is None:
            return _fallback(transcript, TextProcessingFailureCode.MISSING_API_KEY)
        try:
            response = self._transport_factory.create(api_key).process(
                transcript,
                model=model,
                mode=mode,
                target_language=output_language,
            )
        except TextProcessingProviderError as exc:
            return _fallback(transcript, TextProcessingFailureCode(exc.code.value))
        except Exception:
            return _fallback(transcript, TextProcessingFailureCode.UNEXPECTED)

        candidate = response.text.strip()
        if not candidate:
            return _fallback(transcript, TextProcessingFailureCode.EMPTY_RESPONSE)
        if not _is_safe_result(
            transcript,
            candidate,
            response.language,
            mode=mode,
            input_language=input_language,
            output_language=output_language,
        ):
            return _fallback(transcript, TextProcessingFailureCode.UNSAFE_RESPONSE)
        return TextProcessingResult(candidate, candidate != transcript, False)


def _fallback(transcript: str, failure: TextProcessingFailureCode) -> TextProcessingResult:
    return TextProcessingResult(transcript, False, True, failure)


def _is_safe_result(
    source: str,
    candidate: str,
    reported_language: str,
    *,
    mode: TextProcessingMode,
    input_language: LanguageCode | None,
    output_language: LanguageCode | None,
) -> bool:
    supported_codes = {language.value for language in LanguageCode}
    if reported_language not in supported_codes:
        return False
    expected_language = output_language or input_language
    if expected_language is not None and reported_language != expected_language.value:
        return False
    if _has_forbidden_wrapper(candidate) or _numbers(source) != _numbers(candidate):
        return False

    source_length = max(len(source.strip()), 1)
    ratio = len(candidate) / source_length
    if mode is TextProcessingMode.TRANSLATE:
        return 0.35 <= ratio <= 3.0
    if not 0.55 <= ratio <= 1.8:
        return False

    source_words = _words(source)
    candidate_words = _words(candidate)
    if not source_words:
        return False
    word_ratio = len(candidate_words) / len(source_words)
    similarity = SequenceMatcher(None, source_words, candidate_words).ratio()
    return 0.7 <= word_ratio <= 1.35 and similarity >= 0.62


def _has_forbidden_wrapper(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("```", "# ", "## ", "**")) or stripped.endswith("```"):
        return True
    normalized = stripped.casefold()
    prefixes = (
        "here is",
        "here's",
        "translation:",
        "translated text:",
        "formatted text:",
        "ось ",
        "переклад:",
        "відформатований текст:",
        "hier ist",
        "übersetzung:",
        "voici",
        "traduction:",
        "aquí está",
        "traducción:",
    )
    return normalized.startswith(prefixes)


def _numbers(text: str) -> Counter[str]:
    return Counter(re.findall(r"\d+(?:[.,]\d+)?", text))


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", text.casefold(), flags=re.UNICODE)
