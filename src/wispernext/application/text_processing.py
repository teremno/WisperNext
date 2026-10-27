"""Conservative optional formatting and translation with raw-transcript fallback."""

from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from wispernext.application.text_fidelity import (
    lexical_tokens,
    preserves_literals,
    preserves_wording,
)
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
    INVALID_OUTPUT = "invalid_output"
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
    def close(self) -> None: ...

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
            with closing(self._transport_factory.create(api_key)) as transport:
                return self._process_with_transport(
                    transcript,
                    transport,
                    model=model,
                    mode=mode,
                    input_language=input_language,
                    output_language=output_language,
                )
        except Exception:
            return _fallback(transcript, TextProcessingFailureCode.UNEXPECTED)

    def _process_with_transport(
        self,
        transcript: str,
        transport: TextProcessingTransport,
        *,
        model: str,
        mode: TextProcessingMode,
        input_language: LanguageCode | None,
        output_language: LanguageCode | None,
    ) -> TextProcessingResult:
        # A malformed structured answer is worth one more request in any mode; an unsafe
        # formatting answer is not, because the model tends to repeat the same edit.
        max_attempts = 2
        retry_unsafe = mode is TextProcessingMode.TRANSLATE
        for attempt in range(1, max_attempts + 1):
            try:
                response = transport.process(
                    transcript,
                    model=model,
                    mode=mode,
                    target_language=output_language or input_language,
                )
            except TextProcessingProviderError as exc:
                if exc.code is ProviderFailureCode.INVALID_OUTPUT and attempt < max_attempts:
                    continue
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
            if attempt == max_attempts or not retry_unsafe:
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
    if _has_forbidden_wrapper(candidate) and not _has_forbidden_wrapper(source):
        return False
    if not preserves_literals(source, candidate):
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
        # Character counts differ greatly between CJK and spaced European scripts.
        cjk_languages = {LanguageCode.CHINESE_SIMPLIFIED, LanguageCode.JAPANESE}
        if (
            input_language is None
            or input_language in cjk_languages
            or output_language in cjk_languages
        ):
            return 0.15 <= ratio <= 8.0
        return 0.35 <= ratio <= 3.0
    if len(candidate) > max(source_length * 1.8, source_length + 16):
        return False

    return preserves_wording(source, candidate)


def _has_forbidden_wrapper(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("```", "# ", "## ", "**")) or stripped.endswith("```"):
        return True
    normalized = stripped.casefold()
    prefixes = (
        "here is the formatted text",
        "here is the corrected text",
        "here is the translated text",
        "here's the formatted text",
        "here's the corrected text",
        "here's the translated text",
        "translation:",
        "translated text:",
        "formatted text:",
        "ось відформатований текст",
        "ось виправлений текст",
        "ось переклад",
        "переклад:",
        "відформатований текст:",
        "вот исправленный текст",
        "вот перевод",
        "перевод:",
        "hier ist die übersetzung",
        "übersetzung:",
        "voici le texte corrigé",
        "voici la traduction",
        "traduction:",
        "aquí está la traducción",
        "traducción:",
    )
    return normalized.startswith(prefixes)


def _normalized_text(text: str) -> str:
    return " ".join(lexical_tokens(text))


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
