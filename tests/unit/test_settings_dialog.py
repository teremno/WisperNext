import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QDialogButtonBox

from wispernext.audio.devices import ConnectionKind, InputDevice
from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import InterfaceLanguage, LanguageCode, Settings
from wispernext.ui.settings_dialog import SettingsDialog, language_options

DEVICE = InputDevice(2, "stable-usb", "USB Mic", "WASAPI", 48_000, 1, ConnectionKind.USB)


@pytest.mark.parametrize("value,expected", [("F9", "F9"), ("ctrl+alt+r", "Ctrl+Alt+R")])
def test_recording_shortcut_is_visible_and_saved(value: str, expected: str) -> None:
    application()
    saved: list[Settings] = []
    dialog = SettingsDialog(
        Settings(),
        interface_language=InterfaceLanguage.UKRAINIAN,
        refresh_callback=lambda: None,
        save_callback=saved.append,
    )
    shortcut = dialog.findChild(QComboBox, "hotkey")
    assert shortcut is not None
    assert shortcut.currentText() == "F8"
    shortcut.setCurrentText(value)
    dialog.load_microphones((DEVICE,))
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    buttons.button(QDialogButtonBox.StandardButton.Save).click()
    assert saved[0].hotkey == expected


@pytest.mark.parametrize("value", ["", "A", "Ctrl+", "Space"])
def test_invalid_shortcut_does_not_save_or_disable_dialog(value: str) -> None:
    application()
    saved: list[Settings] = []
    dialog = SettingsDialog(
        Settings(),
        interface_language=InterfaceLanguage.ENGLISH,
        refresh_callback=lambda: None,
        save_callback=saved.append,
    )
    shortcut = dialog.findChild(QComboBox, "hotkey")
    assert shortcut is not None
    shortcut.setCurrentText(value)
    dialog.load_microphones((DEVICE,))
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    buttons.button(QDialogButtonBox.StandardButton.Save).click()
    assert saved == []
    assert buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()


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
    dialog = SettingsDialog(
        original,
        interface_language=InterfaceLanguage.UKRAINIAN,
        refresh_callback=lambda: None,
        save_callback=lambda _: None,
    )

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

    dialog = SettingsDialog(
        Settings(),
        interface_language=InterfaceLanguage.ENGLISH,
        refresh_callback=refresh,
        save_callback=lambda _: None,
    )

    assert refresh_count == 0
    dialog.start_refresh()
    dialog.load_microphones((DEVICE,))

    assert refresh_count == 1
    assert dialog.draft_settings().microphone_selection_mode is (
        MicrophoneSelectionMode.SYSTEM_DEFAULT
    )


def test_dialog_exposes_all_languages_and_preserves_separate_choices() -> None:
    application()
    original = Settings(
        input_language=LanguageCode.ENGLISH,
        output_language=LanguageCode.UKRAINIAN,
        interface_language=InterfaceLanguage.RUSSIAN,
        safe_formatting=False,
    )
    dialog = SettingsDialog(
        original,
        interface_language=InterfaceLanguage.RUSSIAN,
        refresh_callback=lambda: None,
        save_callback=lambda _: None,
    )

    draft = dialog.draft_settings()

    assert {language for _label, language in language_options()} == set(LanguageCode)
    assert len(language_options()) == 16
    assert draft.interface_language is InterfaceLanguage.RUSSIAN
    assert draft.input_language is LanguageCode.ENGLISH
    assert draft.output_language is LanguageCode.UKRAINIAN
    assert not draft.safe_formatting


def test_disconnected_manual_microphone_survives_refresh_and_save() -> None:
    application()
    original = Settings(
        microphone_selection_mode=MicrophoneSelectionMode.MANUAL,
        selected_microphone_id="disconnected-mic",
    )
    dialog = SettingsDialog(
        original,
        interface_language=InterfaceLanguage.ENGLISH,
        refresh_callback=lambda: None,
        save_callback=lambda _: None,
    )
    assert dialog.draft_settings().selected_microphone_id == "disconnected-mic"
    dialog.load_microphones((DEVICE,))
    draft = dialog.draft_settings()
    assert draft.selected_microphone_id == "disconnected-mic"
    assert draft.microphone_selection_mode is MicrophoneSelectionMode.MANUAL


def test_refresh_preserves_unsaved_user_microphone_choice() -> None:
    application()
    dialog = SettingsDialog(
        Settings(),
        interface_language=InterfaceLanguage.ENGLISH,
        refresh_callback=lambda: None,
        save_callback=lambda _: None,
    )
    dialog.load_microphones((DEVICE,))
    microphone = dialog.findChildren(QComboBox)[1]
    microphone.setCurrentIndex(microphone.findData(DEVICE.stable_id))
    dialog.start_refresh()
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    assert not buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    dialog.load_microphones((DEVICE,))
    assert dialog.draft_settings().selected_microphone_id == DEVICE.stable_id
    assert buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
