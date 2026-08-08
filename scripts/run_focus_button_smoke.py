"""Exercise the real Win32 activation path and restore the pointer position."""

import ctypes
import json
from ctypes import wintypes

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit

from wispernext.ui.floating_button import FloatingMicrophoneButton

_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004


def main() -> int:
    app = QApplication([])
    user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL

    result = {"status": "timeout", "foreground_preserved": False, "field_focus_preserved": False}
    original_pointer = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(original_pointer))
    target = QLineEdit()
    target.setWindowTitle("WisperNext focus target")
    target.setText("Disposable focus target")
    target.resize(420, 48)
    target.move(120, 120)
    target.show()

    def toggled() -> None:
        foreground_preserved = int(user32.GetForegroundWindow()) == int(target.winId())
        result.update(
            status="verified" if foreground_preserved and target.hasFocus() else "focus_changed",
            foreground_preserved=foreground_preserved,
            field_focus_preserved=target.hasFocus(),
        )
        QTimer.singleShot(0, app.quit)

    button = FloatingMicrophoneButton(toggle_callback=toggled, position_callback=lambda x, y: None)
    button.move(580, 112)
    button.show()

    def click_button_through_windows() -> None:
        user32.SetForegroundWindow(int(target.winId()))
        target.setFocus()
        app.processEvents()
        button_rect = wintypes.RECT()
        user32.GetWindowRect(int(button.winId()), ctypes.byref(button_rect))
        center_x = (button_rect.left + button_rect.right) // 2
        center_y = (button_rect.top + button_rect.bottom) // 2
        user32.SetCursorPos(center_x, center_y)
        user32.mouse_event(_MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(_MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    QTimer.singleShot(350, click_button_through_windows)
    QTimer.singleShot(3_000, app.quit)
    app.exec()
    user32.SetCursorPos(original_pointer.x, original_pointer.y)
    print(json.dumps(result))
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
