"""PySide6 runtime composition for the Windows floating control."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from contextlib import suppress
from typing import override

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication

from wispernext.application import DictationController
from wispernext.audio.session import AudioSessionError
from wispernext.bootstrap import build_application_services
from wispernext.domain import ApplicationState, StateSnapshot, parse_hotkey
from wispernext.platform.windows.hotkeys import (
    HotkeyRegistrationError,
    WindowsGlobalHotkey,
    is_registered_hotkey_message,
)
from wispernext.platform.windows.single_instance import WindowsSingleInstance
from wispernext.ui.floating_button import FloatingMicrophoneButton
from wispernext.ui.tray import WisperTrayIcon


class UiDispatcher(QObject):
    """Marshal plain Python callbacks from the worker onto the Qt UI thread."""

    dispatched = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.dispatched.connect(self._run, Qt.ConnectionType.QueuedConnection)

    def dispatch(self, callback: Callable[[], None]) -> None:
        self.dispatched.emit(callback)

    @staticmethod
    def _run(callback: Callable[[], None]) -> None:
        callback()


class HotkeyEventFilter(QAbstractNativeEventFilter):
    """Translate only Wisper's registered WM_HOTKEY into the shared toggle intent."""

    def __init__(self, callback: Callable[[], None]) -> None:
        super().__init__()
        self._callback = callback

    @override
    def nativeEventFilter(
        self,
        event_type: QByteArray | bytes | bytearray | memoryview[int],
        message: int,
    ) -> bool:
        event_name = event_type.data() if isinstance(event_type, QByteArray) else bytes(event_type)
        if event_name in {b"windows_dispatcher_MSG", b"windows_generic_MSG"} and (
            is_registered_hotkey_message(int(message))
        ):
            self._callback()
            return True
        return False


def run_desktop_application(
    arguments: Sequence[str] | None = None,
    *,
    exit_after_ms: int | None = None,
) -> int:
    """Run one Windows desktop instance until Qt requests shutdown."""
    instance = WindowsSingleInstance()
    if not instance.is_primary:
        return 0

    app = QApplication(list(arguments) if arguments is not None else sys.argv)
    app.setApplicationName("WisperNext")
    app.setQuitOnLastWindowClosed(False)
    services = build_application_services()
    settings = services.settings_store.load().settings
    dispatcher = UiDispatcher()
    controller_holder: list[DictationController] = []
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: controller_holder[0].toggle_recording(),
        position_callback=lambda x, y: controller_holder[0].save_button_position(x, y),
    )
    controller = DictationController(
        state_machine=services.state_machine,
        microphone_catalog=services.microphone_catalog,
        audio_session=services.audio_session,
        transcription=services.transcription,
        clipboard_delivery=services.clipboard_delivery,
        auto_paste=services.auto_paste,
        focus_port=services.focus_port,
        settings_store=services.settings_store,
        initial_settings=settings,
        state_listener=lambda snapshot: _render_state(app, button, snapshot),
        notice_listener=button.show_notice,
        ui_dispatcher=dispatcher.dispatch,
    )
    controller_holder.append(controller)
    tray = WisperTrayIcon(controller.shutdown)

    hotkey = WindowsGlobalHotkey()
    event_filter = HotkeyEventFilter(controller.toggle_recording)
    app.installNativeEventFilter(event_filter)
    try:
        hotkey.register(parse_hotkey(settings.hotkey))
    except HotkeyRegistrationError:
        button.show_notice("Глобальна клавіша зайнята. Кнопка мікрофона працює.")

    button.place(settings.floating_button_x, settings.floating_button_y)
    if settings.launch_floating_button:
        button.show()
    tray.show()
    controller.start()
    if exit_after_ms is not None:
        QTimer.singleShot(exit_after_ms, app.quit)

    def cleanup() -> None:
        hotkey.close()
        with suppress(AudioSessionError):
            services.audio_session.stop()
        controller.close()
        instance.close()

    app.aboutToQuit.connect(cleanup)
    return app.exec()


def _render_state(
    app: QApplication,
    button: FloatingMicrophoneButton,
    snapshot: StateSnapshot,
) -> None:
    button.render_snapshot(snapshot)
    if snapshot.state is ApplicationState.TERMINATED:
        app.quit()
