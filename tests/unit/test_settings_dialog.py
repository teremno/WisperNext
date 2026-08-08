import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from wispernext.audio.devices import ConnectionKind, InputDevice
from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import Settings
from wispernext.ui.settings_dialog import SettingsDialog

DEVICE = InputDevice(2, "stable-usb", "USB Mic", "WASAPI", 48_000, 1, ConnectionKind.USB)


def application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_dialog_preserves_manual_microphone_and_builds_valid_settings() -> None:
    application()
    original = Settings(
        microphone_selection_mode=MicrophoneSelectionMode.MANUAL,
        selected_microphone_id=DEVICE.stable_id,
        auto_paste=True,
        max_recording_seconds=90,
    )
    dialog = SettingsDialog(original, refresh_callback=lambda: None, save_callback=lambda _: None)

    dialog.load_microphones((DEVICE,))
    draft = dialog.draft_settings()

    assert draft.microphone_selection_mode is MicrophoneSelectionMode.MANUAL
    assert draft.selected_microphone_id == DEVICE.stable_id
    assert draft.auto_paste
    assert draft.max_recording_seconds == 90


def test_dialog_defaults_to_system_microphone_and_refresh_is_explicit() -> None:
    application()
    refresh_count = 0

    def refresh() -> None:
        nonlocal refresh_count
        refresh_count += 1

    dialog = SettingsDialog(Settings(), refresh_callback=refresh, save_callback=lambda _: None)

    assert refresh_count == 0
    dialog.start_refresh()
    dialog.load_microphones((DEVICE,))

    assert refresh_count == 1
    assert dialog.draft_settings().microphone_selection_mode is (
        MicrophoneSelectionMode.SYSTEM_DEFAULT
    )
