"""Speech-recognition style hints passed to Whisper as preceding text.

Whisper continues the style of its prompt: vocabulary, spelling, and punctuation. A short,
grammatically punctuated sample discourages a comma at every pause. Keep each hint well
under the 224-token provider limit and free of private content.
"""

from wispernext.infrastructure.config import LanguageCode

_HINTS = {
    LanguageCode.UKRAINIAN: (
        "Привіт. Я зараз диктую текст українською мовою. Завтра зранку треба перевірити "
        "код на GitHub і відповісти на листи. Ну, думаю, встигну до обіду."
    ),
}


def transcription_prompt(language: LanguageCode | None) -> str | None:
    """Return the style hint for a fixed input language, if one exists."""
    if language is None:
        return None
    return _HINTS.get(language)
