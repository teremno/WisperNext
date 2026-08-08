import pytest
from PySide6.QtCore import QByteArray

from wispernext.ui.qt_runtime import HotkeyEventFilter


@pytest.mark.parametrize(
    "event_type",
    [QByteArray(b"windows_dispatcher_MSG"), QByteArray(b"windows_generic_MSG")],
)
def test_registered_hotkey_from_supported_qt_windows_message_toggles_once(
    event_type: QByteArray, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def toggled() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(
        "wispernext.ui.qt_runtime.is_registered_hotkey_message",
        lambda address: address == 123,
    )
    event_filter = HotkeyEventFilter(toggled)

    handled = event_filter.nativeEventFilter(event_type, 123)

    assert handled
    assert calls == 1


def test_unrelated_native_message_is_not_consumed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "wispernext.ui.qt_runtime.is_registered_hotkey_message",
        lambda _address: False,
    )
    event_filter = HotkeyEventFilter(lambda: None)

    assert not event_filter.nativeEventFilter(QByteArray(b"windows_generic_MSG"), 123)
