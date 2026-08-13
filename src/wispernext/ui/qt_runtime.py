"""PySide6 runtime composition for the Windows floating control."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from contextlib import suppress
from typing import override

from PySide6.QtCore import (
    QAbstractNativeEventFilter,
    QByteArray,
    QLocale,
    QObject,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import QApplication

from wispernext.application import DictationController
from wispernext.audio.session import AudioSessionError
from wispernext.bootstrap import build_application_services
from wispernext.domain import ApplicationState, StateSnapshot, parse_hotkey
from wispernext.infrastructure.config import Settings
from wispernext.platform.windows.hotkeys import (
    HotkeyRegistrationError,
    WindowsGlobalHotkey,
    is_registered_hotkey_message,
)
from wispernext.platform.windows.single_instance import WindowsSingleInstance
from wispernext.ui.floating_button import FloatingMicrophoneButton
from wispernext.ui.i18n import resolve_interface_language, tr
from wispernext.ui.settings_dialog import SettingsDialog
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
    active_language = [
        resolve_interface_language(settings.interface_language, QLocale.system().name())
    ]
    dispatcher = UiDispatcher()
    controller_holder: list[DictationController] = []
    settings_callback_holder: list[Callable[[], None]] = []
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: controller_holder[0].toggle_recording(),
        position_callback=lambda x, y: controller_holder[0].save_button_position(x, y),
        settings_callback=lambda: settings_callback_holder[0](),
        interface_language=active_language[0],
    )
    controller = DictationController(
        state_machine=services.state_machine,
        microphone_catalog=services.microphone_catalog,
        audio_session=services.audio_session,
        transcription=services.transcription,
        text_processing=services.text_processing,
        clipboard_delivery=services.clipboard_delivery,
        auto_paste=services.auto_paste,
        focus_port=services.focus_port,
        settings_store=services.settings_store,
        initial_settings=settings,
        state_listener=lambda snapshot: _render_state(app, button, snapshot),
        notice_listener=lambda key: button.show_notice(tr(active_language[0], key)),
        ui_dispatcher=dispatcher.dispatch,
        diagnostic_journal=services.diagnostic_journal,
    )
    controller_holder.append(controller)
    settings_dialogs: list[SettingsDialog] = []

    def open_settings() -> None:
        if settings_dialogs and settings_dialogs[0].isVisible():
            settings_dialogs[0].raise_()
            settings_dialogs[0].activateWindow()
            return

        dialog: SettingsDialog

        def refresh() -> None:
            controller.request_microphones(
                dialog.load_microphones,
                lambda key: dialog.show_error(tr(active_language[0], key)),
            )

        def saved(updated: Settings) -> None:
            active_language[0] = resolve_interface_language(
                updated.interface_language, QLocale.system().name()
            )
            button.set_interface_language(active_language[0])
            tray.set_interface_language(active_language[0])
            if updated.launch_floating_button:
                button.show()
            dialog.saved(updated)

        dialog = SettingsDialog(
            controller.current_settings(),
            interface_language=active_language[0],
            refresh_callback=refresh,
            save_callback=lambda updated: controller.update_settings(
                updated,
                saved,
                lambda key: dialog.show_error(tr(active_language[0], key)),
            ),
        )
        settings_dialogs.append(dialog)
        dialog.destroyed.connect(lambda: settings_dialogs.clear())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.start_refresh()

    settings_callback_holder.append(open_settings)

    tray = WisperTrayIcon(
        settings_callback=open_settings,
        shutdown_callback=controller.shutdown,
        interface_language=active_language[0],
    )

    hotkey = WindowsGlobalHotkey()
    event_filter = HotkeyEventFilter(controller.toggle_recording)
    app.installNativeEventFilter(event_filter)
    try:
        hotkey.register(parse_hotkey(settings.hotkey))
    except HotkeyRegistrationError:
        button.show_notice(tr(active_language[0], "notice.hotkey_unavailable"))

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
