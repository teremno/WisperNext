from wispernext.application import (
    ProviderFailureCode,
    ProviderTextResult,
    TextProcessingFailureCode,
    TextProcessingMode,
    TextProcessingProviderError,
    TextProcessingService,
    processing_mode,
)
from wispernext.infrastructure.config import LanguageCode
from wispernext.infrastructure.secrets import SecretValue


class FakeSecretProvider:
    def __init__(self, configured: bool = True) -> None:
        self.configured = configured

    def get_groq_api_key(self) -> SecretValue | None:
        return SecretValue("secret") if self.configured else None


class FailingSecretProvider:
    def get_groq_api_key(self) -> SecretValue | None:
        raise RuntimeError("private provider detail")


class FakeTransport:
    def __init__(self, result: ProviderTextResult | Exception) -> None:
        self.result = result
        self.calls: list[tuple[str, TextProcessingMode, LanguageCode | None]] = []

    def process(
        self,
        transcript: str,
        *,
        model: str,
        mode: TextProcessingMode,
        target_language: LanguageCode | None,
    ) -> ProviderTextResult:
        self.calls.append((model, mode, target_language))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeFactory:
    def __init__(self, transport: FakeTransport) -> None:
        self.transport = transport
        self.create_count = 0

    def create(self, _api_key: SecretValue) -> FakeTransport:
        self.create_count += 1
        return self.transport


def service(
    result: ProviderTextResult | Exception,
    *,
    configured: bool = True,
) -> tuple[TextProcessingService, FakeFactory]:
    factory = FakeFactory(FakeTransport(result))
    return TextProcessingService(FakeSecretProvider(configured), factory), factory


def test_processing_mode_separates_formatting_translation_and_passthrough() -> None:
    assert processing_mode(None, None, False) is None
    assert processing_mode(LanguageCode.UKRAINIAN, None, True) is TextProcessingMode.FORMAT
    assert (
        processing_mode(
            LanguageCode.UKRAINIAN,
            LanguageCode.ENGLISH,
            False,
        )
        is TextProcessingMode.TRANSLATE
    )
    assert (
        processing_mode(
            LanguageCode.UKRAINIAN,
            LanguageCode.UKRAINIAN,
            False,
        )
        is None
    )
    assert processing_mode(None, LanguageCode.ENGLISH, False) is TextProcessingMode.TRANSLATE


def test_passthrough_makes_no_provider_or_secret_dependent_call() -> None:
    processor, factory = service(ProviderTextResult("unused", "en"), configured=False)

    result = processor.process(
        "raw words",
        model="model",
        input_language=None,
        output_language=None,
        safe_formatting=False,
    )

    assert result.text == "raw words"
    assert not result.transformed
    assert not result.used_fallback
    assert factory.create_count == 0


def test_safe_formatting_accepts_conservative_punctuation() -> None:
    processor, factory = service(ProviderTextResult("Привіт, це тест.", "uk"))

    result = processor.process(
        "привіт це тест",
        model="model",
        input_language=LanguageCode.UKRAINIAN,
        output_language=None,
        safe_formatting=True,
    )

    assert result.text == "Привіт, це тест."
    assert result.transformed
    assert not result.used_fallback
    assert factory.transport.calls == [("model", TextProcessingMode.FORMAT, None)]


def test_translation_accepts_requested_output_language() -> None:
    processor, _factory = service(ProviderTextResult("Hello, this is a test.", "en"))

    result = processor.process(
        "Привіт, це тест.",
        model="model",
        input_language=LanguageCode.UKRAINIAN,
        output_language=LanguageCode.ENGLISH,
        safe_formatting=True,
    )

    assert result.text == "Hello, this is a test."
    assert result.transformed
    assert not result.used_fallback
    assert result.attempts == 1


def test_unchanged_ukrainian_to_russian_translation_is_retried_once() -> None:
    source = "Я говорю українською мовою."

    class RetryTransport(FakeTransport):
        def __init__(self) -> None:
            super().__init__(ProviderTextResult(source, "ru"))
            self.results = [
                ProviderTextResult(source, "ru"),
                ProviderTextResult("Я говорю на русском языке.", "ru"),
            ]

        def process(
            self,
            transcript: str,
            *,
            model: str,
            mode: TextProcessingMode,
            target_language: LanguageCode | None,
        ) -> ProviderTextResult:
            self.calls.append((model, mode, target_language))
            return self.results.pop(0)

    transport = RetryTransport()
    processor = TextProcessingService(FakeSecretProvider(), FakeFactory(transport))

    result = processor.process(
        source,
        model="model",
        input_language=LanguageCode.UKRAINIAN,
        output_language=LanguageCode.RUSSIAN,
        safe_formatting=True,
    )

    assert result.text == "Я говорю на русском языке."
    assert result.transformed
    assert not result.used_fallback
    assert result.attempts == 2
    assert len(transport.calls) == 2


def test_two_invalid_ukrainian_to_russian_results_use_visible_fallback_category() -> None:
    source = "Перевіряю стабільність перекладу."
    processor, factory = service(ProviderTextResult(source, "ru"))

    result = processor.process(
        source,
        model="model",
        input_language=LanguageCode.UKRAINIAN,
        output_language=LanguageCode.RUSSIAN,
        safe_formatting=True,
    )

    assert result.text == source
    assert result.used_fallback
    assert result.failure is TextProcessingFailureCode.UNSAFE_RESPONSE
    assert result.attempts == 2
    assert len(factory.transport.calls) == 2


def test_russian_result_with_ukrainian_specific_characters_is_rejected() -> None:
    processor, _factory = service(ProviderTextResult("Це нібито русский текст.", "ru"))

    result = processor.process(
        "Це український текст.",
        model="model",
        input_language=LanguageCode.UKRAINIAN,
        output_language=LanguageCode.RUSSIAN,
        safe_formatting=False,
    )

    assert result.used_fallback
    assert result.failure is TextProcessingFailureCode.UNSAFE_RESPONSE
    assert result.attempts == 2


def test_missing_key_preserves_raw_transcript() -> None:
    processor, _factory = service(ProviderTextResult("unused", "en"), configured=False)

    result = processor.process(
        "raw",
        model="model",
        input_language=None,
        output_language=LanguageCode.ENGLISH,
        safe_formatting=False,
    )

    assert result.text == "raw"
    assert result.used_fallback
    assert result.failure is TextProcessingFailureCode.MISSING_API_KEY


def test_provider_failure_preserves_raw_transcript() -> None:
    processor, _factory = service(TextProcessingProviderError(ProviderFailureCode.TIMEOUT))

    result = processor.process(
        "raw transcript",
        model="model",
        input_language=LanguageCode.ENGLISH,
        output_language=None,
        safe_formatting=True,
    )

    assert result.text == "raw transcript"
    assert result.used_fallback
    assert result.failure is TextProcessingFailureCode.TIMEOUT


def test_secret_storage_failure_preserves_raw_transcript() -> None:
    factory = FakeFactory(FakeTransport(ProviderTextResult("unused", "en")))
    processor = TextProcessingService(FailingSecretProvider(), factory)

    result = processor.process(
        "raw transcript",
        model="model",
        input_language=LanguageCode.ENGLISH,
        output_language=None,
        safe_formatting=True,
    )

    assert result.text == "raw transcript"
    assert result.used_fallback
    assert result.failure is TextProcessingFailureCode.UNEXPECTED
    assert factory.create_count == 0


def test_meta_commentary_language_mismatch_and_number_change_are_rejected() -> None:
    unsafe_results = (
        ProviderTextResult("Here is the formatted text: raw words", "en"),
        ProviderTextResult("Hallo, dies ist 42.", "de"),
        ProviderTextResult("Hello, this is 43.", "en"),
    )
    for unsafe in unsafe_results:
        processor, _factory = service(unsafe)
        result = processor.process(
            "hello this is 42",
            model="model",
            input_language=LanguageCode.ENGLISH,
            output_language=None,
            safe_formatting=True,
        )

        assert result.text == "hello this is 42"
        assert result.used_fallback
        assert result.failure is TextProcessingFailureCode.UNSAFE_RESPONSE


def test_excessive_same_language_rewrite_is_rejected() -> None:
    processor, _factory = service(
        ProviderTextResult(
            "An entirely unrelated response discussing a different subject today.",
            "en",
        )
    )

    result = processor.process(
        "please schedule the meeting for tomorrow morning",
        model="model",
        input_language=LanguageCode.ENGLISH,
        output_language=None,
        safe_formatting=True,
    )

    assert result.used_fallback
    assert result.text == "please schedule the meeting for tomorrow morning"
