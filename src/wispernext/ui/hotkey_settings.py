"""Apply a global shortcut on the UI thread and restore it if saving fails."""

from collections.abc import Callable
from typing import Protocol

from wispernext.domain import HotkeySpec, parse_hotkey
from wispernext.infrastructure.config import Settings
from wispernext.platform.windows.hotkeys import HotkeyRegistrationError


class HotkeyPort(Protocol):
    def register(self, hotkey: HotkeySpec) -> None: ...


SettingsSaved = Callable[[Settings], None]
SettingsError = Callable[[str], None]
PersistSettings = Callable[[Settings, SettingsSaved, SettingsError], None]


def save_with_hotkey(
    updated: Settings,
    previous: Settings,
    hotkey: HotkeyPort,
    persist: PersistSettings,
    on_saved: SettingsSaved,
    on_error: SettingsError,
) -> None:
    """Reject occupied shortcuts before persistence; roll back on storage errors."""
    changed = updated.hotkey != previous.hotkey

    def restore() -> bool:
        try:
            hotkey.register(parse_hotkey(previous.hotkey))
        except HotkeyRegistrationError:
            return False
        return True

    if changed:
        try:
            hotkey.register(parse_hotkey(updated.hotkey))
        except HotkeyRegistrationError:
            restored = restore()
            on_error("notice.hotkey_unavailable" if restored else "notice.hotkey_restore_failed")
            return

    def failed(key: str) -> None:
        if changed and not restore():
            on_error("notice.hotkey_restore_failed")
            return
        on_error(key)

    persist(updated, on_saved, failed)
