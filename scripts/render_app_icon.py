"""Render the WisperNext application icon into a multi-size Windows .ico file.

The design scales up the tray icon: a dark disc, a teal ring, and a microphone. Larger sizes
add sound waves. Each size is drawn separately, so small icons stay sharp instead of being
downscaled from 256 px.
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap, QRadialGradient

SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
TEAL = QColor("#2DE1C2")
MIC = QColor("#E8FFFB")


def render(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = size / 256

    ring = max(1.5, 12 * scale)
    disc = QRectF(ring / 2, ring / 2, size - ring, size - ring)
    gradient = QRadialGradient(QPointF(size * 0.38, size * 0.3), size * 0.75)
    gradient.setColorAt(0.0, QColor("#1E2E3A"))
    gradient.setColorAt(1.0, QColor("#0A1016"))
    painter.setBrush(gradient)
    painter.setPen(QPen(TEAL, ring))
    painter.drawEllipse(disc)

    stroke = max(1.5, 14 * scale)
    pen = QPen(MIC, stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(MIC)
    painter.drawRoundedRect(
        QRectF(104 * scale, 52 * scale, 48 * scale, 92 * scale), 24 * scale, 24 * scale
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(76 * scale, 96 * scale, 104 * scale, 82 * scale), 180 * 16, 180 * 16)
    painter.drawLine(QPointF(128 * scale, 178 * scale), QPointF(128 * scale, 204 * scale))
    painter.drawLine(QPointF(100 * scale, 204 * scale), QPointF(156 * scale, 204 * scale))

    if size >= 40:
        # Two sound waves on each side, centered on the microphone head.
        painter.setPen(
            QPen(TEAL, max(1.5, 10 * scale), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        for radius, span in ((60, 56), (86, 50)):
            box = QRectF(
                (128 - radius) * scale,
                (86 - radius) * scale,
                2 * radius * scale,
                2 * radius * scale,
            )
            painter.drawArc(box, int((180 - span / 2) * 16), span * 16)
            painter.drawArc(box, int(-span / 2 * 16), span * 16)
    painter.end()
    return pixmap


def png_bytes(pixmap: QPixmap) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not pixmap.save(buffer, "PNG"):
        raise RuntimeError("PNG encoding failed.")
    return bytes(data.data())


def ico_bytes(images: list[tuple[int, bytes]]) -> bytes:
    """Pack PNG images into an ICO container; Windows reads PNG entries at every size."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = b""
    payload = b""
    for size, png in images:
        dimension = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(png), offset)
        payload += png
        offset += len(png)
    return header + entries + payload


def main() -> int:
    QGuiApplication(sys.argv[:1])
    output = Path(__file__).resolve().parent.parent / "assets" / "wispernext.ico"
    images = [(size, png_bytes(render(size))) for size in SIZES]
    output.write_bytes(ico_bytes(images))
    preview = Path(__file__).resolve().parent.parent / ".pytest-tmp" / "app_icon_preview.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    render(256).save(str(preview))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
