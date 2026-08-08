import pytest

from wispernext.domain import HotkeyModifier, HotkeyValidationError, parse_hotkey


@pytest.mark.parametrize(
    ("value", "canonical"),
    [
        ("F8", "F8"),
        ("f24", "F24"),
        ("Pause", "Pause"),
        ("Page Up", "PageUp"),
        ("Ctrl+Shift+A", "Ctrl+Shift+A"),
        ("win+alt+7", "Alt+Win+7"),
        ("Ctrl+Numpad1", "Ctrl+Numpad1"),
        ("VolumeMute", "VolumeMute"),
    ],
)
def test_supported_hotkeys_are_canonicalized(value: str, canonical: str) -> None:
    assert parse_hotkey(value).canonical == canonical


def test_modifier_set_is_typed_and_order_independent() -> None:
    result = parse_hotkey("Shift+Ctrl+F8")

    assert result.modifiers == frozenset({HotkeyModifier.CTRL, HotkeyModifier.SHIFT})
    assert result.canonical == "Ctrl+Shift+F8"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "A",
        "0",
        "/",
        "Ctrl",
        "Ctrl+Alt",
        "Ctrl+Ctrl+F8",
        "F0",
        "F25",
        "Ctrl+Unknown",
        "Ctrl++A",
    ],
)
def test_unsafe_or_unsupported_hotkeys_are_rejected(value: str) -> None:
    with pytest.raises(HotkeyValidationError):
        parse_hotkey(value)
