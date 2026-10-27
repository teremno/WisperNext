"""Regression cases for personal voice, Unicode scripts, and factual preservation."""

from dataclasses import dataclass

import pytest

from wispernext.application.text_fidelity import (
    lexical_tokens,
    preserves_literals,
    preserves_wording,
)
from wispernext.application.text_processing import (
    ProviderTextResult,
    TextProcessingFailureCode,
    TextProcessingService,
)
from wispernext.infrastructure.config import LanguageCode
from wispernext.infrastructure.secrets import EnvironmentSecretProvider, SecretValue


@dataclass
class FixedTransport:
    result: ProviderTextResult
    close_count: int = 0

    def process(self, transcript: str, **kwargs: object) -> ProviderTextResult:
        return self.result

    def close(self) -> None:
        self.close_count += 1


@dataclass
class FixedFactory:
    transport: FixedTransport

    def create(self, api_key: SecretValue) -> FixedTransport:
        return self.transport


def service(result: ProviderTextResult) -> tuple[TextProcessingService, FixedFactory]:
    factory = FixedFactory(FixedTransport(result))
    return TextProcessingService(
        EnvironmentSecretProvider({"WISPER_GROQ_API_KEY": "test"}), factory
    ), factory


def test_arabic_added_vocalization_keeps_original_transcript() -> None:
    source = "طيب لا أعرف ربما غدا"
    processor, factory = service(ProviderTextResult("طيب، لا أعرف. ربما غداً.", "ar"))
    result = processor.process(
        source,
        model="model",
        input_language=LanguageCode.ARABIC,
        output_language=None,
        safe_formatting=True,
    )
    assert result.text == source
    assert result.used_fallback
    assert result.failure is TextProcessingFailureCode.UNSAFE_RESPONSE
    assert factory.transport.close_count == 1


VOICE_CASES = [
    (
        LanguageCode.ENGLISH,
        "well I don't know maybe tomorrow",
        "Well, I don't know. Maybe tomorrow.",
    ),
    (LanguageCode.UKRAINIAN, "ну я не знаю може завтра", "Ну, я не знаю. Може, завтра."),
    (LanguageCode.RUSSIAN, "ну я не знаю может завтра", "Ну, я не знаю. Может, завтра."),
    (
        LanguageCode.GERMAN,
        "na ja ich weiß nicht vielleicht morgen",
        "Na ja, ich weiß nicht. Vielleicht morgen.",
    ),
    (
        LanguageCode.FRENCH,
        "bon je ne sais pas peut-être demain",
        "Bon, je ne sais pas. Peut-être demain.",
    ),
    (LanguageCode.SPANISH, "bueno no sé quizá mañana", "Bueno, no sé. Quizá mañana."),
    (LanguageCode.ITALIAN, "beh non lo so forse domani", "Beh, non lo so. Forse domani."),
    (LanguageCode.PORTUGUESE, "bem não sei talvez amanhã", "Bem, não sei. Talvez amanhã."),
    (LanguageCode.POLISH, "no nie wiem może jutro", "No, nie wiem. Może jutro."),
    (
        LanguageCode.DUTCH,
        "nou ik weet het niet misschien morgen",
        "Nou, ik weet het niet. Misschien morgen.",
    ),
    (LanguageCode.TURKISH, "yani bilmiyorum belki yarın", "Yani, bilmiyorum. Belki yarın."),
    (LanguageCode.ARABIC, "طيب لا أعرف ربما غدا", "طيب، لا أعرف. ربما غدا."),
    (LanguageCode.HINDI, "मुझे नहीं पता शायद कल", "मुझे नहीं पता। शायद कल।"),
    (LanguageCode.CHINESE_SIMPLIFIED, "嗯我不知道也许明天", "嗯，我不知道。也许明天。"),
    (LanguageCode.JAPANESE, "ええとわからないたぶん明日", "ええと、わからない。たぶん明日。"),
    (LanguageCode.KOREAN, "음 잘 모르겠어요 아마 내일", "음, 잘 모르겠어요. 아마 내일."),
]


@pytest.mark.parametrize("language,source,candidate", VOICE_CASES)
def test_formatting_preserves_personal_voice_in_every_language(
    language: LanguageCode, source: str, candidate: str
) -> None:
    processor, _ = service(ProviderTextResult(candidate, language.value))
    result = processor.process(
        source, model="model", input_language=language, output_language=None, safe_formatting=True
    )
    assert result.text == candidate
    assert not result.used_fallback


@pytest.mark.parametrize(
    "source,candidate",
    [
        ("я не можу прийти завтра о десятій", "Я можу прийти завтра о десятій."),
        ("I am not available for the meeting tomorrow", "I am available for the meeting tomorrow."),
        ("ich kann nicht kommen", "Ich kann kommen."),
        ("не оплачено", "Оплачено."),
        ("I cannot come tomorrow", "I can come tomorrow."),
        ("I am uncertain about tomorrow", "I am certain about tomorrow."),
        ("嗯我不知道也许明天", "我不知道。也许明天。"),
        ("я хочу сказати ну я поки не знаю", "Я хочу зазначити, що поки не знаю."),
        (
            "please keep all these words in their original order",
            "Please keep these words all in their original order.",
        ),
    ],
)
def test_formatter_rejects_lost_negation_tone_or_word_order(source: str, candidate: str) -> None:
    assert not preserves_wording(source, candidate)


@pytest.mark.parametrize(
    "source,candidate",
    [
        ("the value is -12.5", "The value is 12.5."),
        ("growth is 15%", "Growth is 15."),
        ("use version v1", "Use version v2."),
        ("meet on 2026-10-10", "Meet on 2026-10-11."),
        ("send to hello@example.com", "Send to help@example.com."),
        ("open https://example.com/a", "Open https://example.com/b."),
    ],
)
def test_literal_changes_are_rejected(source: str, candidate: str) -> None:
    assert not preserves_literals(source, candidate)


@pytest.mark.parametrize(
    "source,candidate",
    [
        ("hello there", "Hello there!"),
        ("don't go", "Don’t go."),
        ("helo everyone", "Hello everyone."),
        ("добрий день це я ну так це я", "Добрий день! Це я. Ну так, це я."),
        ("我明天去学校", "我明天去学校。"),
        ("42", "42."),
        ("こんにちは", "こんにちは。"),
    ],
)
def test_presentation_and_unmistakable_small_spelling_edits_remain_allowed(
    source: str, candidate: str
) -> None:
    assert preserves_wording(source, candidate)


@pytest.mark.parametrize(
    "language,source,candidate",
    [
        (
            LanguageCode.UKRAINIAN,
            "Кількі трапа буде знаідти картонний конверт.",
            "Тільки треба буде знайти картонний конверт.",
        ),
        (
            LanguageCode.RUSSIAN,
            "толька нада найти картонный конверт",
            "Только надо найти картонный конверт.",
        ),
        (
            LanguageCode.ENGLISH,
            "I need to finde the cardboard envelope",
            "I need to find the cardboard envelope.",
        ),
        (
            LanguageCode.GERMAN,
            "Ich muss den Kartonumschlag fnden",
            "Ich muss den Kartonumschlag finden.",
        ),
    ],
)
def test_clear_contextual_recognition_repairs_reach_the_user(
    language: LanguageCode, source: str, candidate: str
) -> None:
    processor, _ = service(ProviderTextResult(candidate, language.value))

    result = processor.process(
        source,
        model="model",
        input_language=language,
        output_language=None,
        safe_formatting=True,
    )

    assert result.text == candidate
    assert not result.used_fallback


@pytest.mark.parametrize(
    "source,candidate",
    [
        (
            "Кількі трапа буде знаідти картонний конверт.",
            "Завтра треба буде знайти картонний конверт.",
        ),
        (
            "Завтра треба буде знайти картонний конверт.",
            "Завтра треба буде продати картонний конверт.",
        ),
        (
            "Треба буде знайти цей картонний конверт завтра.",
            "Можна буде продати мій паперовий пакет завтра.",
        ),
        (
            "Ich kann nicht kommen morgen.",
            "Ich kann kommen morgen.",
        ),
    ],
)
def test_contextual_repair_still_rejects_changed_meaning(source: str, candidate: str) -> None:
    assert not preserves_wording(source, candidate)


def test_unicode_combining_marks_remain_part_of_hindi_words() -> None:
    assert lexical_tokens("मुझे नहीं पता") == ["मुझे", "नहीं", "पता"]


@pytest.mark.parametrize(
    "language,source,candidate",
    [
        (LanguageCode.ENGLISH, "here is my address", "Here is my address."),
        (LanguageCode.UKRAINIAN, "ось моя адреса", "Ось моя адреса."),
        (LanguageCode.FRENCH, "voici mon adresse", "Voici mon adresse."),
        (LanguageCode.GERMAN, "hier ist meine adresse", "Hier ist meine Adresse."),
        (
            LanguageCode.UKRAINIAN,
            "добре це не тільки робота це моє життя",
            "Добре, це не тільки робота, це моє життя.",
        ),
        (
            LanguageCode.ENGLISH,
            "it's not just work it's my life",
            "It's not just work, it's my life.",
        ),
        (
            LanguageCode.GERMAN,
            "das ist nicht nur Arbeit das ist mein Leben",
            "Das ist nicht nur Arbeit, das ist mein Leben.",
        ),
    ],
)
def test_genuine_spoken_openings_and_contrasts_are_not_blacklisted(
    language: LanguageCode, source: str, candidate: str
) -> None:
    processor, _ = service(ProviderTextResult(candidate, language.value))
    result = processor.process(
        source, model="model", input_language=language, output_language=None, safe_formatting=True
    )
    assert result.text == candidate
    assert not result.used_fallback


def test_single_cjk_character_can_receive_sentence_punctuation() -> None:
    processor, _ = service(ProviderTextResult("好。", "zh-CN"))
    result = processor.process(
        "好",
        model="model",
        input_language=LanguageCode.CHINESE_SIMPLIFIED,
        output_language=None,
        safe_formatting=True,
    )
    assert result.text == "好。"
    assert not result.used_fallback


def test_lost_word_causes_raw_fallback_and_transport_is_closed() -> None:
    processor, factory = service(ProviderTextResult("Я можу прийти завтра.", "uk"))
    result = processor.process(
        "я не можу прийти завтра",
        model="model",
        input_language=LanguageCode.UKRAINIAN,
        output_language=None,
        safe_formatting=True,
    )
    assert result.text == "я не можу прийти завтра"
    assert result.failure is TextProcessingFailureCode.UNSAFE_RESPONSE
    assert factory.transport.close_count == 1


def test_content_language_set_is_covered() -> None:
    assert {language for language, _, _ in VOICE_CASES} == set(LanguageCode)


@pytest.mark.parametrize(
    "input_language,output_language,source,candidate",
    [
        (LanguageCode.ENGLISH, LanguageCode.CHINESE_SIMPLIFIED, "See you tomorrow.", "明天见。"),
        (LanguageCode.CHINESE_SIMPLIFIED, LanguageCode.ENGLISH, "明天见", "See you tomorrow."),
    ],
)
def test_translation_length_guard_accounts_for_cjk_scripts(
    input_language: LanguageCode, output_language: LanguageCode, source: str, candidate: str
) -> None:
    processor, _ = service(ProviderTextResult(candidate, output_language.value))
    result = processor.process(
        source,
        model="model",
        input_language=input_language,
        output_language=output_language,
        safe_formatting=True,
    )
    assert result.text == candidate
    assert not result.used_fallback


def test_existing_question_cannot_become_a_statement() -> None:
    assert not preserves_literals("can you call me?", "Can you call me.")
    assert preserves_literals("можеш подзвонити?", "Can you call me?")


@pytest.mark.parametrize(
    "source,candidate",
    [
        ("я піду в магазин завтра зранку", "Я піду у магазин завтра зранку."),
        ("якщо ти хочеш та приходь", "Якщо ти хочеш, то приходь."),
        ("я хочу купи ти хліба сьогодні ввечері", "Я хочу купити хліба сьогодні ввечері."),
        (
            "давай зустрінемось завтравечері біля входу",
            "Давай зустрінемось завтра ввечері біля входу.",
        ),
        ("мені треба кар тонний конверт на пошті", "Мені треба картонний конверт на пошті."),
        ("ну е-е я думаю що так", "Ну, я думаю, що так."),
        ("я незнаю що робити", "Я не знаю, що робити."),
        ("Я, думаю, що, це, добре, працює", "Я думаю, що це добре працює."),
    ],
)
def test_common_ukrainian_recognition_repairs_are_accepted(source: str, candidate: str) -> None:
    assert preserves_wording(source, candidate)
    assert preserves_literals(source, candidate)


@pytest.mark.parametrize(
    "source,candidate",
    [
        ("я не можу прийти", "Я можу прийти."),
        ("він прийде завтра", "Вона прийде завтра."),
        ("ти прийдеш завтра", "Ми прийдемо завтра."),
        ("купи ти хліба", "Купи хліба."),
        ("я піду в магазин", "Я піду в магазин і в аптеку."),
        ("добре домовились до завтра дякую за перегляд", "Добре, домовились, до завтра."),
        ("я сам це зроблю", "Я сам це не зроблю."),
    ],
)
def test_repairs_that_change_negation_person_or_content_are_rejected(
    source: str, candidate: str
) -> None:
    assert not preserves_wording(source, candidate)
