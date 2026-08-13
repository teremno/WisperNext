"""System-tray settings and lifecycle controls."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from wispernext.infrastructure.config import InterfaceLanguage
from wispernext.ui.i18n import tr


class WisperTrayIcon(QSystemTrayIcon):
    """Expose settings and a deliberate Exit action from the Windows tray."""

    def __init__(
        self,
        *,
        settings_callback: Callable[[], None],
        shutdown_callback: Callable[[], None],
        interface_language: InterfaceLanguage = InterfaceLanguage.ENGLISH,
    ) -> None:
        super().__init__(_tray_icon())
        menu = QMenu()
        settings_action = QAction(menu)
        settings_action.triggered.connect(settings_callback)
        menu.addAction(settings_action)
        menu.addSeparator()
        exit_action = QAction(menu)
        exit_action.triggered.connect(shutdown_callback)
        menu.addAction(exit_action)
        self.setContextMenu(menu)
        self.activated.connect(
            lambda reason: (
                settings_callback()
                if reason is QSystemTrayIcon.ActivationReason.DoubleClick
                else None
            )
        )
        self._menu = menu
        self._settings_action = settings_action
        self._exit_action = exit_action
        self.set_interface_language(interface_language)

    def set_interface_language(self, interface_language: InterfaceLanguage) -> None:
        """Apply localized tray labels without rebuilding signal connections."""
        self.setToolTip(tr(interface_language, "tray.tooltip"))
        self._settings_action.setText(tr(interface_language, "tray.settings"))
        self._exit_action.setText(tr(interface_language, "tray.exit"))


def _tray_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#101820"))
    painter.setPen(QPen(QColor("#2DE1C2"), 2))
    painter.drawEllipse(1, 1, 30, 30)
    painter.setPen(
        QPen(
            QColor("#E8FFFB"),
            2,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    painter.drawRoundedRect(12, 7, 8, 12, 4, 4)
    painter.drawArc(9, 14, 14, 11, 180 * 16, 180 * 16)
    painter.drawLine(16, 25, 16, 27)
    painter.end()
    return QIcon(pixmap)
