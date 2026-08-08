"""Wait for one real registered hotkey event without opening a microphone."""

import argparse
import ctypes
import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from wispernext.domain import parse_hotkey
from wispernext.platform.windows.hotkeys import HotkeyRegistrationError, WindowsGlobalHotkey
from wispernext.ui.qt_runtime import HotkeyEventFilter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hotkey")
    parser.add_argument("--timeout-ms", type=int, default=45_000)
    parser.add_argument("--self-send-f8", action="store_true")
    parser.add_argument("--register-only", action="store_true")
    args = parser.parse_args()
    hotkey_spec = parse_hotkey(args.hotkey)
    app = QApplication([])
    result = {"status": "timeout", "hotkey": hotkey_spec.canonical}

    def received() -> None:
        result["status"] = "received"
        app.quit()

    registration = WindowsGlobalHotkey()
    event_filter = HotkeyEventFilter(received)
    app.installNativeEventFilter(event_filter)
    try:
        registration.register(hotkey_spec)
    except HotkeyRegistrationError:
        print(json.dumps({"status": "unavailable", "hotkey": hotkey_spec.canonical}))
        return 3
    if args.register_only:
        registration.close()
        print(json.dumps({"status": "available", "hotkey": hotkey_spec.canonical}))
        return 0
    if args.self_send_f8:
        QTimer.singleShot(300, lambda: _send_f8())
    QTimer.singleShot(args.timeout_ms, app.quit)
    app.exec()
    registration.close()
    print(json.dumps(result))
    return 0 if result["status"] == "received" else 2


def _send_f8() -> None:
    user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
    user32.keybd_event(0x77, 0, 0, 0)
    user32.keybd_event(0x77, 0, 0x0002, 0)


if __name__ == "__main__":
    raise SystemExit(main())
