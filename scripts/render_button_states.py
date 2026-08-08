"""Render all floating-button states into one local QA image."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from wispernext.domain import ApplicationState, StateSnapshot
from wispernext.ui.floating_button import FloatingMicrophoneButton

STATES = (
    ("READY", ApplicationState.IDLE),
    ("OPENING", ApplicationState.OPENING_AUDIO),
    ("RECORDING", ApplicationState.RECORDING),
    ("PROCESSING", ApplicationState.TRANSCRIBING),
    ("ERROR", ApplicationState.RECOVERABLE_ERROR),
    ("DISABLED", ApplicationState.SHUTTING_DOWN),
)


def main() -> int:
    QApplication([])
    canvas = QPixmap(600, 116)
    canvas.fill(QColor("#080C10"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#D9E4E8"))
    painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
    for index, (label, state) in enumerate(STATES):
        button = FloatingMicrophoneButton(
            toggle_callback=lambda: None,
            position_callback=lambda x, y: None,
        )
        button.render_snapshot(StateSnapshot(state, index, None))
        x = 18 + index * 97
        button.render(painter, QPoint(x + 8, 10))
        painter.drawText(x, 88, 80, 20, Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    output = Path(".pytest-tmp/button_states.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(output)):
        return 2
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
