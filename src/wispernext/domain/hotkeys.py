"""Pure validation and canonicalization for safe global hotkeys."""

import re
from dataclasses import dataclass
from enum import StrEnum


class HotkeyValidationError(ValueError):
    """Raised when a configured hotkey could interfere with ordinary typing."""


class HotkeyModifier(StrEnum):
    CTRL = "Ctrl"
    ALT = "Alt"
    SHIFT = "Shift"
    WIN = "Win"


_MODIFIER_ORDER = tuple(HotkeyModifier)
_MODIFIERS = {modifier.value.casefold(): modifier for modifier in HotkeyModifier}
_ALIASES = {
    "pause": "Pause",
    "break": "Pause",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pgup": "PageUp",
    "pagedown": "PageDown",
    "pgdn": "PageDown",
    "scrolllock": "ScrollLock",
    "numpadadd": "NumpadAdd",
    "numpadsubtract": "NumpadSubtract",
    "numpadmultiply": "NumpadMultiply",
    "numpaddivide": "NumpadDivide",
    "numpaddecimal": "NumpadDecimal",
    "mediaplaypause": "MediaPlayPause",
    "medianexttrack": "MediaNextTrack",
    "mediaprevtrack": "MediaPrevTrack",
    "volumemute": "VolumeMute",
    "volumeup": "VolumeUp",
    "volumedown": "VolumeDown",
}


@dataclass(frozen=True, slots=True)
class HotkeySpec:
    modifiers: frozenset[HotkeyModifier]
    key: str
    canonical: str


def parse_hotkey(value: str) -> HotkeySpec:
    """Parse one supported hotkey and reject unsafe unmodified typing keys."""
    if not value.strip():
        raise HotkeyValidationError("Hotkey must not be blank.")
    parts = tuple(part.strip() for part in value.split("+"))
    if any(not part for part in parts) or len(parts) > 5:
        raise HotkeyValidationError("Hotkey has an invalid structure.")

    modifiers: set[HotkeyModifier] = set()
    key_parts: list[str] = []
    for part in parts:
        modifier = _MODIFIERS.get(part.casefold())
        if modifier is None:
            key_parts.append(part)
        elif modifier in modifiers:
            raise HotkeyValidationError("Hotkey contains a duplicate modifier.")
        else:
            modifiers.add(modifier)
    if len(key_parts) != 1:
        raise HotkeyValidationError("Hotkey requires exactly one non-modifier key.")

    key = _canonical_key(key_parts[0])
    ordinary_typing_key = bool(re.fullmatch(r"[A-Z0-9]", key))
    if ordinary_typing_key and not modifiers:
        raise HotkeyValidationError("Unmodified letters and digits are forbidden hotkeys.")

    ordered = [modifier.value for modifier in _MODIFIER_ORDER if modifier in modifiers]
    canonical = "+".join((*ordered, key))
    return HotkeySpec(frozenset(modifiers), key, canonical)


def _canonical_key(value: str) -> str:
    normalized = value.replace(" ", "").casefold()
    function_match = re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", normalized)
    if function_match:
        return f"F{function_match.group(1)}"
    numpad_match = re.fullmatch(r"numpad([0-9])", normalized)
    if numpad_match:
        return f"Numpad{numpad_match.group(1)}"
    if len(normalized) == 1 and normalized.isascii() and normalized.isalnum():
        return normalized.upper()
    alias = _ALIASES.get(normalized)
    if alias is None:
        raise HotkeyValidationError("Hotkey key is not supported.")
    return alias
