"""Accessible localized settings dialog for stable product controls."""

from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from wispernext.audio.devices import InputDevice
from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import InterfaceLanguage, LanguageCode, Settings
from wispernext.ui.i18n import (
    CONTENT_LANGUAGE_ORDER,
    interface_language_options,
    language_name,
    tr,
)


def language_options(
    interface_language: InterfaceLanguage = InterfaceLanguage.UKRAINIAN,
) -> tuple[tuple[str, LanguageCode], ...]:
    """Return all content languages in stable UI order."""
    return tuple(
        (language_name(interface_language, language), language)
        for language in CONTENT_LANGUAGE_ORDER
    )


class SettingsDialog(QDialog):
    """Edit validated non-secret settings without touching Windows audio settings."""

    def __init__(
        self,
        settings: Settings,
        *,
        interface_language: InterfaceLanguage,
        refresh_callback: Callable[[], None],
        save_callback: Callable[[Settings], None],
    ) -> None:
        super().__init__()
        self._base_settings = settings
        self._language = interface_language
        self._saving = False
        self._refresh_callback = refresh_callback
        self._save_callback = save_callback
        self.setWindowTitle(self._text("settings.window_title"))
        self.setMinimumWidth(560)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(_STYLE)

        title = QLabel(self._text("settings.title"))
        title.setObjectName("title")
        subtitle = QLabel(self._text("settings.subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")

        self._interface_language = QComboBox()
        self._interface_language.addItem(self._text("settings.system_default"), None)
        for label, interface_option in interface_language_options():
            self._interface_language.addItem(label, interface_option.value)
        _select_interface_language(self._interface_language, settings.interface_language)
        interface_group = QGroupBox(self._text("settings.interface_group"))
        interface_layout = QFormLayout(interface_group)
        interface_layout.addRow(self._text("settings.interface_language"), self._interface_language)

        self._microphone = QComboBox()
        self._microphone.setAccessibleName(self._text("settings.microphone_accessible"))
        self._microphone.addItem(self._text("settings.microphone_default"), None)
        self._refresh = QPushButton(self._text("settings.refresh"))
        self._refresh.setAccessibleName(self._text("settings.refresh_accessible"))
        self._refresh.clicked.connect(self.start_refresh)
        microphone_row = QWidget()
        microphone_layout = QHBoxLayout(microphone_row)
        microphone_layout.setContentsMargins(0, 0, 0, 0)
        microphone_layout.addWidget(self._microphone, 1)
        microphone_layout.addWidget(self._refresh)

        audio_group = QGroupBox(self._text("settings.microphone_group"))
        audio_layout = QFormLayout(audio_group)
        audio_layout.addRow(self._text("settings.microphone_source"), microphone_row)

        self._input_language = QComboBox()
        self._input_language.setAccessibleName(self._text("settings.input_accessible"))
        self._input_language.addItem(self._text("settings.input_auto"), None)
        self._output_language = QComboBox()
        self._output_language.setAccessibleName(self._text("settings.output_accessible"))
        self._output_language.addItem(self._text("settings.output_same"), None)
        for label, content_language in language_options(interface_language):
            self._input_language.addItem(label, content_language.value)
            self._output_language.addItem(label, content_language.value)
        _select_language(self._input_language, settings.input_language)
        _select_language(self._output_language, settings.output_language)
        self._safe_formatting = QCheckBox(self._text("settings.safe_formatting"))
        self._safe_formatting.setChecked(settings.safe_formatting)
        language_group = QGroupBox(self._text("settings.language_group"))
        language_layout = QFormLayout(language_group)
        language_layout.addRow(self._text("settings.input_language"), self._input_language)
        language_layout.addRow(self._text("settings.output_language"), self._output_language)
        language_layout.addRow(self._safe_formatting)

        self._auto_paste = QCheckBox(self._text("settings.auto_paste"))
        self._auto_paste.setChecked(settings.auto_paste)
        self._launch_button = QCheckBox(self._text("settings.launch_button"))
        self._launch_button.setChecked(settings.launch_floating_button)
        self._max_seconds = QSpinBox()
        self._max_seconds.setRange(5, 1_800)
        self._max_seconds.setSuffix(self._text("settings.seconds_suffix"))
        self._max_seconds.setValue(settings.max_recording_seconds)
        behavior_group = QGroupBox(self._text("settings.behavior_group"))
        behavior_layout = QFormLayout(behavior_group)
        behavior_layout.addRow(self._auto_paste)
        behavior_layout.addRow(self._text("settings.max_recording"), self._max_seconds)
        behavior_layout.addRow(self._launch_button)

        self._status = QLabel(self._text("settings.loading"))
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        self._status.setAccessibleName(self._text("settings.status_accessible"))
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = self._buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText(self._text("settings.save"))
        save_button.setDefault(True)
        self._buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            self._text("settings.cancel")
        )
        self._buttons.accepted.connect(self._save)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(interface_group)
        layout.addWidget(audio_group)
        layout.addWidget(language_group)
        layout.addWidget(behavior_group)
        layout.addWidget(self._status)
        layout.addWidget(self._buttons)

    def start_refresh(self) -> None:
        """Disable device controls while requesting fresh metadata."""
        self._set_refreshing(True)
        self._status.setText(self._text("settings.refreshing"))
        self._refresh_callback()

    def load_microphones(self, devices: tuple[InputDevice, ...]) -> None:
        """Populate stable device choices while preserving the current preference."""
        selected_id = self._base_settings.selected_microphone_id
        self._microphone.clear()
        self._microphone.addItem(self._text("settings.microphone_default"), None)
        for device in devices:
            label = f"{device.name} · {device.host_api}"
            self._microphone.addItem(label, device.stable_id)
        if self._base_settings.microphone_selection_mode is MicrophoneSelectionMode.MANUAL:
            index = self._microphone.findData(selected_id)
            if index >= 0:
                self._microphone.setCurrentIndex(index)
            else:
                self._status.setText(self._text("settings.saved_microphone_unavailable"))
                self._set_refreshing(False)
                return
        self._status.setText(self._text("settings.microphones_found", count=len(devices)))
        self._set_refreshing(False)

    def show_error(self, message: str) -> None:
        self._saving = False
        self._status.setText(message)
        self._set_refreshing(False)
        self._buttons.setEnabled(True)

    def saved(self, settings: Settings) -> None:
        self._base_settings = settings
        self._saving = False
        self.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._saving:
            event.ignore()
            return
        super().closeEvent(event)

    def draft_settings(self) -> Settings:
        """Build the immutable settings value represented by visible controls."""
        selected_id = self._microphone.currentData()
        mode = (
            MicrophoneSelectionMode.SYSTEM_DEFAULT
            if selected_id is None
            else MicrophoneSelectionMode.MANUAL
        )
        return replace(
            self._base_settings,
            microphone_selection_mode=mode,
            selected_microphone_id=selected_id,
            interface_language=_selected_interface_language(self._interface_language),
            input_language=_selected_language(self._input_language),
            output_language=_selected_language(self._output_language),
            safe_formatting=self._safe_formatting.isChecked(),
            auto_paste=self._auto_paste.isChecked(),
            max_recording_seconds=self._max_seconds.value(),
            launch_floating_button=self._launch_button.isChecked(),
        )

    def _set_refreshing(self, refreshing: bool) -> None:
        self._refresh.setEnabled(not refreshing)
        self._microphone.setEnabled(not refreshing)

    def _save(self) -> None:
        self._saving = True
        self._buttons.setEnabled(False)
        self._status.setText(self._text("settings.saving"))
        self._save_callback(self.draft_settings())

    def _text(self, key: str, **values: object) -> str:
        return tr(self._language, key, **values)


def _select_language(combo: QComboBox, language: LanguageCode | None) -> None:
    if language is None:
        combo.setCurrentIndex(0)
        return
    index = combo.findData(language.value)
    combo.setCurrentIndex(max(index, 0))


def _selected_language(combo: QComboBox) -> LanguageCode | None:
    value = combo.currentData()
    return LanguageCode(value) if isinstance(value, str) else None


def _select_interface_language(combo: QComboBox, language: InterfaceLanguage | None) -> None:
    if language is None:
        combo.setCurrentIndex(0)
        return
    index = combo.findData(language.value)
    combo.setCurrentIndex(max(index, 0))


def _selected_interface_language(combo: QComboBox) -> InterfaceLanguage | None:
    value = combo.currentData()
    return InterfaceLanguage(value) if isinstance(value, str) else None


_STYLE = """
QDialog {
    background: #101820;
    color: #e8fffb;
    font-family: "Segoe UI";
    font-size: 14px;
}
QLabel#title {
    color: #2de1c2;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 2px;
}
QLabel { color: #e8fffb; }
QLabel#subtitle, QLabel#status { color: #b8cbc8; }
QGroupBox {
    border: 1px solid #3b5553;
    margin-top: 12px;
    padding: 14px;
    font-weight: 700;
    color: #2de1c2;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QComboBox, QSpinBox {
    min-height: 34px;
    background: #17242d;
    color: #e8fffb;
    border: 1px solid #52716e;
    padding: 2px 8px;
}
QPushButton {
    min-height: 36px;
    background: #21323b;
    color: #e8fffb;
    border: 1px solid #2de1c2;
    padding: 0 14px;
    font-weight: 600;
}
QPushButton:hover, QPushButton:focus { background: #29444a; }
QPushButton:default { background: #2de1c2; color: #101820; }
QCheckBox { min-height: 32px; color: #e8fffb; }
"""
