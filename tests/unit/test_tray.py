import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from wispernext.ui.tray import WisperTrayIcon


def application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_tray_exposes_settings_before_exit() -> None:
    application()
    events: list[str] = []
    tray = WisperTrayIcon(
        settings_callback=lambda: events.append("settings"),
        shutdown_callback=lambda: events.append("exit"),
    )

    actions = tray.contextMenu().actions() if tray.contextMenu() is not None else []
    visible_actions = [action for action in actions if not action.isSeparator()]

    assert [action.text() for action in visible_actions] == [
        "Налаштування…",
        "Вийти з WisperNext",
    ]
    visible_actions[0].trigger()
    assert events == ["settings"]
