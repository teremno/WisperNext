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
    """Allow presentation changes and a few small spelling corrections, never rewriting."""
    original = lexical_tokens(source)
    formatted = lexical_tokens(candidate)
    if original == formatted:
        return True
    if len(original) != len(formatted):
        return False
    changes = 0
    for before, after in zip(original, formatted, strict=True):
        if before == after:
            continue
        if before in _NEGATIONS or after in _NEGATIONS:
            return False
        if min(len(before), len(after)) < 4:
            return False
        matcher = SequenceMatcher(None, before, after, autojunk=False)
        edits = sum(
            max(end_before - start_before, end_after - start_after)
            for tag, start_before, end_before, start_after, end_after in matcher.get_opcodes()
            if tag != "equal"
        )
        if edits > 1 or matcher.ratio() < 0.85:
            return False
        changes += 1
    return changes <= max(1, len(original) // 20)


def _literals(text: str) -> Counter[str]:
    return Counter(match.rstrip(".,!?;。！？") for match in _LITERALS.findall(text))


def _is_cjk(character: str) -> bool:
    code = ord(character)
    return 0x3400 <= code <= 0x9FFF or 0x3040 <= code <= 0x30FF or 0x20000 <= code <= 0x3134F
