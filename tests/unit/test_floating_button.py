import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication

from wispernext.domain import ApplicationState, StateSnapshot
from wispernext.infrastructure.config import InterfaceLanguage
from wispernext.ui.floating_button import (
    ButtonVisualState,
    FloatingMicrophoneButton,
    visual_state,
)


def application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_every_application_state_maps_to_an_explicit_visual_shape() -> None:
    assert {visual_state(state) for state in ApplicationState} == set(ButtonVisualState)
    assert visual_state(ApplicationState.IDLE) is ButtonVisualState.READY
    assert visual_state(ApplicationState.RECORDING) is ButtonVisualState.RECORDING
    assert visual_state(ApplicationState.TRANSCRIBING) is ButtonVisualState.PROCESSING
    assert visual_state(ApplicationState.RECOVERABLE_ERROR) is ButtonVisualState.ERROR


def test_widget_is_accessible_non_focusable_and_always_on_top() -> None:
    application()
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: None,
        position_callback=lambda x, y: None,
        interface_language=InterfaceLanguage.UKRAINIAN,
    )

    flags = button.windowFlags()

    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert button.focusPolicy() is Qt.FocusPolicy.NoFocus
    assert button.accessibleName()
    assert button.accessibleDescription()
    assert button.width() == 64
    assert button.height() == 64


def test_rendering_snapshot_updates_accessible_state_without_owning_domain_state() -> None:
    application()
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: None,
        position_callback=lambda x, y: None,
        interface_language=InterfaceLanguage.UKRAINIAN,
    )

    button.render_snapshot(StateSnapshot(ApplicationState.RECORDING, 2, None))

    assert "зупинити" in button.accessibleDescription().casefold()
    assert button.isEnabled()


def test_right_click_opens_settings_without_toggling_recording() -> None:
    app = application()
    events: list[str] = []
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: events.append("toggle"),
        position_callback=lambda x, y: None,
        settings_callback=lambda: events.append("settings"),
    )
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse,
        QPoint(16, 16),
        QPoint(16, 16),
    )

    app.sendEvent(button, event)

    assert events == ["settings"]
    assert event.isAccepted()
