import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from wispernext.domain import ApplicationState, StateSnapshot
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
        toggle_callback=lambda: None, position_callback=lambda x, y: None
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
        toggle_callback=lambda: None, position_callback=lambda x, y: None
    )

    button.render_snapshot(StateSnapshot(ApplicationState.RECORDING, 2, None))

    assert "зупинити" in button.accessibleDescription().casefold()
    assert button.isEnabled()
