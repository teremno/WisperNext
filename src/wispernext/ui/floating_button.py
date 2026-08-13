"""Non-activating accessible floating microphone control."""

import ctypes
from collections.abc import Callable
from enum import StrEnum

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QShowEvent,
)
from PySide6.QtWidgets import QApplication, QWidget

from wispernext.domain import ApplicationState, StateSnapshot
from wispernext.infrastructure.config import InterfaceLanguage
from wispernext.ui.i18n import tr
from wispernext.ui.layout import ScreenRect, visible_button_position

_BUTTON_SIZE = 64
_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_NOACTIVATE = 0x08000000


class ButtonVisualState(StrEnum):
    READY = "ready"
    OPENING = "opening"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"
    DISABLED = "disabled"


_STATE_KEYS = {
    ButtonVisualState.READY: "button.ready",
    ButtonVisualState.OPENING: "button.opening",
    ButtonVisualState.RECORDING: "button.recording",
    ButtonVisualState.PROCESSING: "button.processing",
    ButtonVisualState.ERROR: "button.error",
    ButtonVisualState.DISABLED: "button.disabled",
}


def visual_state(application_state: ApplicationState) -> ButtonVisualState:
    if application_state is ApplicationState.IDLE:
        return ButtonVisualState.READY
    if application_state is ApplicationState.OPENING_AUDIO:
        return ButtonVisualState.OPENING
    if application_state is ApplicationState.RECORDING:
        return ButtonVisualState.RECORDING
    if application_state is ApplicationState.RECOVERABLE_ERROR:
        return ButtonVisualState.ERROR
    if application_state in {ApplicationState.SHUTTING_DOWN, ApplicationState.TERMINATED}:
        return ButtonVisualState.DISABLED
    return ButtonVisualState.PROCESSING


class FloatingMicrophoneButton(QWidget):
    """Render state and emit intents without owning application state or focus."""

    def __init__(
        self,
        *,
        toggle_callback: Callable[[], None],
        position_callback: Callable[[int, int], None],
        settings_callback: Callable[[], None] | None = None,
        interface_language: InterfaceLanguage = InterfaceLanguage.ENGLISH,
    ) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self._toggle_callback = toggle_callback
        self._position_callback = position_callback
        self._settings_callback = settings_callback
        self._interface_language = interface_language
        self._visual_state = ButtonVisualState.OPENING
        self._press_global: QPointF | None = None
        self._window_origin = QPoint()
        self._dragged = False
        self.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAccessibleName(tr(self._interface_language, "button.name"))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_accessibility()

    def place(self, stored_x: int | None, stored_y: int | None) -> None:
        screens = tuple(
            ScreenRect(
                screen.availableGeometry().x(),
                screen.availableGeometry().y(),
                screen.availableGeometry().width(),
                screen.availableGeometry().height(),
            )
            for screen in QApplication.screens()
        )
        x, y = visible_button_position(
            stored_x,
            stored_y,
            button_size=_BUTTON_SIZE,
            screens=screens,
        )
        self.move(x, y)

    def render_snapshot(self, snapshot: StateSnapshot) -> None:
        self._visual_state = visual_state(snapshot.state)
        self.setEnabled(self._visual_state is not ButtonVisualState.DISABLED)
        self._update_accessibility()
        self.update()

    def show_notice(self, message: str) -> None:
        self.setToolTip(message)
        self.setAccessibleDescription(message)

    def set_interface_language(self, interface_language: InterfaceLanguage) -> None:
        """Apply a saved interface language without restarting the application."""
        self._interface_language = interface_language
        self.setAccessibleName(tr(interface_language, "button.name"))
        self._update_accessibility()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_no_activate_style()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        if self._settings_callback is None:
            event.ignore()
            return
        self._settings_callback()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition()
            self._window_origin = self.pos()
            self._dragged = False
            event.accept()
            return
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press_global is None or not event.buttons() & Qt.MouseButton.LeftButton:
            event.ignore()
            return
        delta = event.globalPosition() - self._press_global
        if delta.manhattanLength() >= QApplication.startDragDistance():
            self._dragged = True
        if self._dragged:
            self.move(self._window_origin + delta.toPoint())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() is not Qt.MouseButton.LeftButton or self._press_global is None:
            event.ignore()
            return
        self._press_global = None
        if self._dragged:
            self.place(self.x(), self.y())
            self._position_callback(self.x(), self.y())
        elif self.isEnabled():
            self._toggle_callback()
        event.accept()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = _colors(self._visual_state)
        painter.setBrush(QColor(palette[0]))
        painter.setPen(QPen(QColor(palette[1]), 3))
        painter.drawEllipse(2, 2, 60, 60)
        painter.setPen(QPen(QColor(palette[2]), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        _draw_state_icon(painter, self._visual_state)

    def _update_accessibility(self) -> None:
        label = tr(self._interface_language, _STATE_KEYS[self._visual_state])
        self.setAccessibleDescription(label)
        self.setToolTip(label)

    def _apply_no_activate_style(self) -> None:
        user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
        user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        window_handle = int(self.winId())
        style = user32.GetWindowLongPtrW(window_handle, _GWL_EXSTYLE)
        user32.SetWindowLongPtrW(
            window_handle,
            _GWL_EXSTYLE,
            style | _WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE,
        )


def _colors(state: ButtonVisualState) -> tuple[str, str, str]:
    return {
        ButtonVisualState.READY: ("#101820", "#2DE1C2", "#E8FFFB"),
        ButtonVisualState.OPENING: ("#1B1710", "#FFB400", "#FFE4A3"),
        ButtonVisualState.RECORDING: ("#241014", "#FF4D67", "#FFF1F3"),
        ButtonVisualState.PROCESSING: ("#101624", "#63A9FF", "#EAF3FF"),
        ButtonVisualState.ERROR: ("#25150E", "#FF7A3D", "#FFF0E8"),
        ButtonVisualState.DISABLED: ("#171717", "#737373", "#BDBDBD"),
    }[state]


def _draw_state_icon(painter: QPainter, state: ButtonVisualState) -> None:
    if state is ButtonVisualState.READY:
        painter.drawRoundedRect(25, 15, 14, 23, 7, 7)
        painter.drawArc(20, 27, 24, 19, 180 * 16, 180 * 16)
        painter.drawLine(32, 46, 32, 50)
    elif state is ButtonVisualState.RECORDING:
        painter.setBrush(painter.pen().color())
        painter.drawRoundedRect(22, 22, 20, 20, 3, 3)
    elif state is ButtonVisualState.OPENING:
        painter.drawLine(22, 19, 42, 19)
        painter.drawLine(22, 45, 42, 45)
        painter.drawLine(24, 21, 40, 43)
        painter.drawLine(40, 21, 24, 43)
    elif state is ButtonVisualState.PROCESSING:
        painter.drawLine(19, 24, 29, 32)
        painter.drawLine(29, 32, 19, 40)
        painter.drawLine(35, 24, 45, 32)
        painter.drawLine(45, 32, 35, 40)
    elif state is ButtonVisualState.ERROR:
        painter.drawLine(32, 17, 18, 44)
        painter.drawLine(18, 44, 46, 44)
        painter.drawLine(46, 44, 32, 17)
        painter.drawLine(32, 27, 32, 36)
        painter.drawPoint(32, 40)
    else:
        painter.drawEllipse(21, 21, 22, 22)
        painter.drawLine(22, 42, 42, 22)
