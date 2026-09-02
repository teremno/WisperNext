import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication

from wispernext.domain import ApplicationState, StateSnapshot
from wispernext.infrastructure.config import InterfaceLanguage
from wispernext.ui.floating_button import (
    ButtonRecoveryReason,
    ButtonVisualState,
    FloatingMicrophoneButton,
    visual_state,
)


class FakeNativeWindow:
    def __init__(self, *, visible: bool = True, topmost: bool = True) -> None:
        self.visible = visible
        self.topmost = topmost
        self.apply_count = 0

    def apply_required_state(self, _window_handle: int) -> None:
        self.apply_count += 1
        self.visible = True
        self.topmost = True

    def is_topmost(self, _window_handle: int) -> bool:
        return self.topmost

    def is_visible(self, _window_handle: int) -> bool:
        return self.visible


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


def test_watchdog_recovery_is_idle_while_visible_and_topmost() -> None:
    app = application()
    native_window = FakeNativeWindow()
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: None,
        position_callback=lambda x, y: None,
        native_window=native_window,
    )
    button.place(None, None)
    button.show()
    app.processEvents()
    initial_apply_count = native_window.apply_count

    assert button.recover_visibility() is None
    assert native_window.apply_count == initial_apply_count


def test_watchdog_restores_a_demoted_button_without_activating_it() -> None:
    app = application()
    native_window = FakeNativeWindow()
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: None,
        position_callback=lambda x, y: None,
        native_window=native_window,
    )
    button.place(None, None)
    button.show()
    app.processEvents()
    native_window.topmost = False

    result = button.recover_visibility()

    assert result is not None
    assert result.reason is ButtonRecoveryReason.NOT_TOPMOST
    assert result.succeeded
    assert native_window.topmost


def test_watchdog_restores_a_button_hidden_only_at_the_native_layer() -> None:
    app = application()
    native_window = FakeNativeWindow()
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: None,
        position_callback=lambda x, y: None,
        native_window=native_window,
    )
    button.place(None, None)
    button.show()
    app.processEvents()
    native_window.visible = False

    result = button.recover_visibility()

    assert result is not None
    assert result.reason is ButtonRecoveryReason.HIDDEN
    assert result.succeeded
    assert native_window.visible


def test_manual_recovery_reshows_the_button_even_when_state_looks_valid() -> None:
    app = application()
    native_window = FakeNativeWindow()
    button = FloatingMicrophoneButton(
        toggle_callback=lambda: None,
        position_callback=lambda x, y: None,
        native_window=native_window,
    )
    button.place(None, None)
    button.show()
    app.processEvents()
    initial_apply_count = native_window.apply_count

    result = button.recover_visibility(ButtonRecoveryReason.MANUAL)

    assert result is not None
    assert result.reason is ButtonRecoveryReason.MANUAL
    assert result.succeeded
    assert native_window.apply_count > initial_apply_count
