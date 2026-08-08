"""Small accessible settings dialog for the current stable controls."""

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
from wispernext.infrastructure.config import Settings


class SettingsDialog(QDialog):
    """Edit validated non-secret settings without touching Windows audio settings."""

    def __init__(
        self,
        settings: Settings,
        *,
        refresh_callback: Callable[[], None],
        save_callback: Callable[[Settings], None],
    ) -> None:
        super().__init__()
        self._base_settings = settings
        self._saving = False
        self._refresh_callback = refresh_callback
        self._save_callback = save_callback
        self.setWindowTitle("Налаштування WisperNext")
        self.setMinimumWidth(520)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(_STYLE)

        title = QLabel("НАЛАШТУВАННЯ")
        title.setObjectName("title")
        subtitle = QLabel("Основні параметри диктування. Windows-настройки не змінюються.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")

        self._microphone = QComboBox()
        self._microphone.setAccessibleName("Вибір мікрофона")
        self._microphone.addItem("Системний мікрофон за замовчуванням", None)
        self._refresh = QPushButton("Оновити список")
        self._refresh.setAccessibleName("Оновити список мікрофонів")
        self._refresh.clicked.connect(self.start_refresh)
        microphone_row = QWidget()
        microphone_layout = QHBoxLayout(microphone_row)
        microphone_layout.setContentsMargins(0, 0, 0, 0)
        microphone_layout.addWidget(self._microphone, 1)
        microphone_layout.addWidget(self._refresh)

        audio_group = QGroupBox("МІКРОФОН")
        audio_layout = QFormLayout(audio_group)
        audio_layout.addRow("Джерело:", microphone_row)

        self._auto_paste = QCheckBox("Автоматично вставляти розпізнаний текст")
        self._auto_paste.setChecked(settings.auto_paste)
        self._launch_button = QCheckBox("Показувати плаваючу кнопку після запуску")
        self._launch_button.setChecked(settings.launch_floating_button)
        self._max_seconds = QSpinBox()
        self._max_seconds.setRange(5, 1_800)
        self._max_seconds.setSuffix(" с")
        self._max_seconds.setValue(settings.max_recording_seconds)
        behavior_group = QGroupBox("ПОВЕДІНКА")
        behavior_layout = QFormLayout(behavior_group)
        behavior_layout.addRow(self._auto_paste)
        behavior_layout.addRow("Максимальний запис:", self._max_seconds)
        behavior_layout.addRow(self._launch_button)

        self._status = QLabel("Завантаження списку мікрофонів…")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        self._status.setAccessibleName("Стан налаштувань")
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = self._buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Зберегти")
        save_button.setDefault(True)
        self._buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Скасувати")
        self._buttons.accepted.connect(self._save)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(audio_group)
        layout.addWidget(behavior_group)
        layout.addWidget(self._status)
        layout.addWidget(self._buttons)

    def start_refresh(self) -> None:
        """Disable device controls while requesting fresh metadata."""
        self._set_refreshing(True)
        self._status.setText("Оновлення списку мікрофонів…")
        self._refresh_callback()

    def load_microphones(self, devices: tuple[InputDevice, ...]) -> None:
        """Populate stable device choices while preserving the current preference."""
        selected_id = self._base_settings.selected_microphone_id
        self._microphone.clear()
        self._microphone.addItem("Системний мікрофон за замовчуванням", None)
        for device in devices:
            label = f"{device.name} · {device.host_api}"
            self._microphone.addItem(label, device.stable_id)
        if self._base_settings.microphone_selection_mode is MicrophoneSelectionMode.MANUAL:
            index = self._microphone.findData(selected_id)
            if index >= 0:
                self._microphone.setCurrentIndex(index)
            else:
                self._status.setText("Збережений мікрофон зараз недоступний.")
                self._set_refreshing(False)
                return
        self._status.setText(f"Знайдено мікрофонів: {len(devices)}")
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
        self._status.setText("Збереження…")
        self._save_callback(self.draft_settings())


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
