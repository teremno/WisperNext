"""Deterministic checks that formatting keeps the speaker's words and literals."""

import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

# Keep contractions intact; typographic apostrophes do not change the spoken word.
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u02bc": "'", "\u2018": "'"})
_LITERALS = re.compile(
    r"https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[\w-]+|"
    r"[+\-\u2212]?\d+(?:[.,:/-]\d+)*(?:[%\u2030])?"
)
# Small spelling edits must not turn a negative statement into an affirmative one.
_NEGATIONS = frozenset(
    [
        "no",
        "not",
        "never",
        "cannot",
        "can't",
        "don't",
        "doesn't",
        "didn't",
        "won't",
        "wouldn't",
        "shouldn't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "ні",
        "не",
        "немає",
        "ніколи",
        "нет",
        "нельзя",
        "никогда",
        "nicht",
        "nein",
        "kein",
        "keine",
        "keinen",
        "keinem",
        "keiner",
        "keines",
        "niemals",
        "non",
        "pas",
        "jamais",
        "aucun",
        "aucune",
        "nunca",
        "nenhum",
        "nenhuma",
        "nenhum",
        "ni",
        "nie",
        "nigdy",
        "geen",
        "niet",
        "nooit",
        "hayır",
        "değil",
        "yok",
        "لا",
        "ليس",
        "لم",
        "لن",
        "ما",
        "नहीं",
        "मत",
        "不",
        "没",
        "无",
        "非",
        "ない",
        "ぬ",
        "ません",
        "안",
        "못",
        "아니다",
        "없다",
    ]
)
_POLARITY_PREFIXES = ("un", "non", "dis", "не", "без")
# A pronoun swap changes who does what even when the words sound alike.
_PRONOUNS = frozenset(
    [
        "я",
        "ти",
        "він",
        "вона",
        "воно",
        "ми",
        "ви",
        "вони",
        "мене",
        "тебе",
        "його",
        "її",
        "нас",
        "вас",
        "їх",
        "мені",
        "тобі",
        "йому",
        "їй",
        "нам",
        "вам",
        "ты",
        "он",
        "она",
        "оно",
        "они",
        "меня",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
    ]
)
_PROTECTED = _NEGATIONS | _PRONOUNS
# Hesitation sounds are not words; formatting may drop them.
_HESITATIONS = frozenset(
    [
        *("е", "ее", "еее", "ем", "емм", "мм", "ммм", "хм", "э", "ээ", "эм"),
        *("um", "umm", "uh", "uhm", "er", "erm", "hmm", "mm", "äh", "ähm", "öh", "euh"),
    ]
)
_MAXIMUM_REPAIR_RUN = 3


def lexical_tokens(text: str) -> list[str]:
    """Tokenize Unicode letters and marks, including unspaced Chinese/Japanese text."""
    normalized = unicodedata.normalize("NFC", text.translate(_APOSTROPHES)).casefold()
    tokens: list[str] = []
    word: list[str] = []
    for index, character in enumerate(normalized):
        if _is_cjk(character):
            if word:
                tokens.append("".join(word))
                word.clear()
            tokens.append(character)
        elif unicodedata.category(character)[0] in {"L", "M"} or (
            character == "'"
            and word
            and index + 1 < len(normalized)
            and unicodedata.category(normalized[index + 1])[0] == "L"
        ):
            word.append(character)
        elif word:
            tokens.append("".join(word))
            word.clear()
    if word:
        tokens.append("".join(word))
    return tokens


def preserves_literals(source: str, candidate: str) -> bool:
    """Keep signed numbers, dates, percentages, URLs, and addresses unchanged."""

    def question_count(text: str) -> int:
        return sum(text.count(mark) for mark in ("?", "\u061f", "\uff1f"))

    return _literals(source) == _literals(candidate) and question_count(
        candidate
    ) >= question_count(source)


def preserves_wording(source: str, candidate: str) -> bool:
    """Allow bounded context-supported recognition repairs without broad rewriting."""
    original = lexical_tokens(source)
    formatted = lexical_tokens(candidate)
    if original == formatted:
        return True
    changes = 0
    matcher = SequenceMatcher(None, original, formatted, autojunk=False)
    for tag, start, end, repaired_start, repaired_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        before = original[start:end]
        after = formatted[repaired_start:repaired_end]
        if tag == "delete" and all(word in _HESITATIONS for word in before):
            continue
        if not _is_recognition_repair(before, after):
            return False
        changes += max(len(before), len(after))
    # Long dictation from a distant microphone may contain several separate errors, but
    # unchanged words must still dominate so the meaning stays anchored.
    maximum_changes = 1 if len(original) <= 2 else min(len(original) // 2, 4 + len(original) // 10)
    return changes <= maximum_changes


def _is_recognition_repair(before: list[str], after: list[str]) -> bool:
    """Accept near-sounding words, or one word split apart or run together."""
    if not before or not after or max(len(before), len(after)) > _MAXIMUM_REPAIR_RUN:
        return False
    if len(before) == len(after):
        return all(_is_word_repair(old, new) for old, new in zip(before, after, strict=True))
    # Re-spacing must keep the letters: "купи ти" -> "купити", "кар тонний" -> "картонний".
    joined_before = "".join(before)
    joined_after = "".join(after)
    if any(word in _PROTECTED for word in (*before, *after)):
        return joined_before == joined_after
    return _within_edit_limit(joined_before, joined_after, 1)


def _is_word_repair(before: str, after: str) -> bool:
    if before == after:
        return True
    if before in _PROTECTED or after in _PROTECTED or _changes_polarity(before, after):
        return False
    if _without_marks(before) == _without_marks(after):
        # Added or removed vocalization changes the written form the speaker chose.
        return False
    if max(len(before), len(after)) > 64:
        return False
    if min(len(before), len(after)) < 4:
        # Short function words that differ by one sound: "в" -> "у", "та" -> "то".
        return _within_edit_limit(before, after, 1)
    matcher = SequenceMatcher(None, before, after, autojunk=False)
    # A recognition error may affect several letters in one word. The unchanged
    # neighboring words still need to anchor its meaning.
    return matcher.ratio() >= 0.55 and _within_edit_limit(before, after, 3)


def _within_edit_limit(before: str, after: str, limit: int) -> bool:
    """Compare short words with a bounded Levenshtein distance."""
    if abs(len(before) - len(after)) > limit:
        return False
    previous = list(range(len(after) + 1))
    for index, character in enumerate(before, start=1):
        current = [index]
        for column, other in enumerate(after, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (character != other),
                )
            )
        if min(current) > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _without_marks(word: str) -> str:
    return "".join(character for character in word if unicodedata.category(character) != "Mn")


def _changes_polarity(before: str, after: str) -> bool:
    """Never erase or insert a common attached negative prefix."""
    return any(
        before == prefix + after or after == prefix + before for prefix in _POLARITY_PREFIXES
    )


def _literals(text: str) -> Counter[str]:
    return Counter(match.rstrip(".,!?;。！？") for match in _LITERALS.findall(text))


def _is_cjk(character: str) -> bool:
    code = ord(character)
    return 0x3400 <= code <= 0x9FFF or 0x3040 <= code <= 0x30FF or 0x20000 <= code <= 0x3134F
