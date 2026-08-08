"""Verify one real Ctrl+V into a disposable focused field and restore the clipboard."""

import json
import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit

from wispernext.application import (
    AutoPasteService,
    ClipboardDeliveryResult,
    ClipboardDeliveryStatus,
)
from wispernext.domain import ApplicationState
from wispernext.platform.windows.clipboard import WindowsClipboard, WindowsPasteAdapter


def main() -> int:
    app = QApplication([])
    target = QLineEdit()
    target.setWindowTitle("WisperNext auto-paste smoke target")
    target.resize(520, 80)
    target.show()
    target.activateWindow()
    target.setFocus()
    clipboard = WindowsClipboard()
    paste = WindowsPasteAdapter()
    original = clipboard.read_text()
    if original is None:
        print(json.dumps({"status": "skipped_non_text_or_empty_clipboard"}))
        return 3
    sentinel = "WisperNext auto-paste verified"
    result = {"status": "timeout", "field_received_text": False}

    def exercise() -> None:
        context = paste.current_focus()
        clipboard.write_text(sentinel)
        outcome = AutoPasteService(paste, wisper_process_id=os.getpid() + 1).try_paste(
            enabled=True,
            clipboard_delivery=ClipboardDeliveryResult(
                ClipboardDeliveryStatus.VERIFIED,
                1,
                False,
            ),
            recording_context=context,
            application_state=ApplicationState.IDLE,
        )
        result["status"] = outcome.status.value
        QTimer.singleShot(300, verify)

    def verify() -> None:
        result["field_received_text"] = target.text() == sentinel
        app.quit()

    QTimer.singleShot(500, exercise)
    QTimer.singleShot(3_000, app.quit)
    try:
        app.exec()
    finally:
        clipboard.write_text(original)
    succeeded = result["status"] == "pasted" and result["field_received_text"] is True
    print(json.dumps(result))
    return 0 if succeeded else 2


if __name__ == "__main__":
    raise SystemExit(main())
