from dataclasses import replace

import pytest

from wispernext.domain import HotkeySpec
from wispernext.infrastructure.config import Settings
from wispernext.platform.windows.hotkeys import HotkeyRegistrationError
from wispernext.ui.hotkey_settings import save_with_hotkey


class FakeHotkey:
    def __init__(self, rejected: set[str]) -> None:
        self.rejected = rejected
        self.calls: list[str] = []

    def register(self, hotkey: HotkeySpec) -> None:
        self.calls.append(hotkey.canonical)
        if hotkey.canonical in self.rejected:
            raise HotkeyRegistrationError("occupied")


@pytest.mark.parametrize("occupied,storage_error", [(False, False), (True, False), (False, True)])
def test_shortcut_applies_before_save_and_restores_on_failure(
    occupied: bool,
    storage_error: bool,
) -> None:
    old = Settings()
    new = replace(old, hotkey="F9")
    hotkey = FakeHotkey({"F9"} if occupied else set())
    persisted: list[Settings] = []
    saved: list[Settings] = []
    errors: list[str] = []

    def persist(settings, on_saved, on_error):
        persisted.append(settings)
        if storage_error:
            on_error("notice.settings_save_failed")
        else:
            on_saved(settings)

    save_with_hotkey(new, old, hotkey, persist, saved.append, errors.append)
    if occupied or storage_error:
        assert hotkey.calls == ["F9", "F8"]
        assert saved == []
        assert errors
    else:
        assert hotkey.calls == ["F9"]
        assert saved == [new]
        assert errors == []
    assert bool(persisted) is not occupied


def test_unchanged_shortcut_is_not_reregistered() -> None:
    settings = Settings()
    hotkey = FakeHotkey(set())
    saved: list[Settings] = []
    errors: list[str] = []
    save_with_hotkey(
        settings,
        settings,
        hotkey,
        lambda value, success, _failure: success(value),
        saved.append,
        errors.append,
    )
    assert saved == [settings]
    assert hotkey.calls == []


def test_failed_restore_is_reported_without_saving() -> None:
    errors: list[str] = []
    save_with_hotkey(
        replace(Settings(), hotkey="F9"),
        Settings(),
        FakeHotkey({"F8", "F9"}),
        lambda *_args: pytest.fail("Must not save an occupied shortcut"),
        lambda _settings: pytest.fail("Must not report success"),
        errors.append,
    )
    assert errors == ["notice.hotkey_restore_failed"]
