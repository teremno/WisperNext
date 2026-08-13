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
    attempts: int = 0


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
            transport = self._transport_factory.create(api_key)
        except Exception:
            return _fallback(transcript, TextProcessingFailureCode.UNEXPECTED)
        max_attempts = 2 if mode is TextProcessingMode.TRANSLATE else 1
        for attempt in range(1, max_attempts + 1):
            try:
                response = transport.process(
                    transcript,
                    model=model,
                    mode=mode,
                    target_language=output_language,
                )
            except TextProcessingProviderError as exc:
                return _fallback(
                    transcript, TextProcessingFailureCode(exc.code.value), attempts=attempt
                )
            except Exception:
                return _fallback(transcript, TextProcessingFailureCode.UNEXPECTED, attempts=attempt)

            candidate = response.text.strip()
            if not candidate:
                failure = TextProcessingFailureCode.EMPTY_RESPONSE
            elif not _is_safe_result(
                transcript,
                candidate,
                response.language,
                mode=mode,
                input_language=input_language,
                output_language=output_language,
            ):
                failure = TextProcessingFailureCode.UNSAFE_RESPONSE
            else:
                return TextProcessingResult(
                    candidate, candidate != transcript, False, attempts=attempt
                )
            if attempt == max_attempts:
                return _fallback(transcript, failure, attempts=attempt)
        raise AssertionError("Text processing attempt loop must return.")


def _fallback(
    transcript: str,
    failure: TextProcessingFailureCode,
    *,
    attempts: int = 0,
) -> TextProcessingResult:
    return TextProcessingResult(transcript, False, True, failure, attempts)


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

    if (
        mode is TextProcessingMode.TRANSLATE
        and input_language is not None
        and output_language is not None
        and input_language is not output_language
    ):
        if _normalized_text(source) == _normalized_text(candidate):
            return False
        if _contains_source_specific_characters(candidate, input_language, output_language):
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


def _normalized_text(text: str) -> str:
    return " ".join(_words(text))


def _contains_source_specific_characters(
    candidate: str,
    input_language: LanguageCode,
    output_language: LanguageCode,
) -> bool:
    source_specific = {
        (LanguageCode.UKRAINIAN, LanguageCode.RUSSIAN): frozenset("іїєґ"),
        (LanguageCode.RUSSIAN, LanguageCode.UKRAINIAN): frozenset("ыэъё"),
    }.get((input_language, output_language))
    return source_specific is not None and not source_specific.isdisjoint(candidate.casefold())
