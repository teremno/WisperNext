# ADR 0007: Non-activating floating button

## Context

The floating microphone control must stay visible and accept mouse/touch activation without taking
keyboard focus from another application's text field. It must scale across Windows displays, expose
accessible state, and remain a presentation adapter rather than owning dictation state.

## Decision

Use `PySide6-Essentials` for Qt Core, Gui, and Widgets only. Render a fixed 64 logical-pixel custom
`QWidget` with `Tool`, `FramelessWindowHint`, `WindowStaysOnTopHint`, and
`WindowDoesNotAcceptFocus`, plus `WA_ShowWithoutActivating`. On Windows, reinforce the native
window with `WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE` after its handle exists.

Reassert `HWND_TOPMOST` with `SetWindowPos` without activation whenever Windows loses the native
topmost state. A low-frequency UI timer repairs only hidden, minimized, off-screen, or demoted
state. Display topology changes trigger the same bounded recovery path, and the tray provides an
explicit **Show microphone button** action. Recovery events contain only an allowlisted reason and
success/failure status.

Use a restrained industrial/utilitarian visual system: dark neutral surface, one high-contrast
state accent, and a different geometric icon for ready, opening, recording, processing, error, and
disabled. Expose an accessible name and state description. Do not animate or add status panels.

Store Qt logical coordinates in versioned settings. Clamp restored coordinates to the nearest
available screen so display removal or resolution changes cannot strand the control off-screen.
Dragging persists position on the background worker; a click sends only the shared toggle intent.

## Alternatives considered

- Native Win32 custom painting: rejected because DPI, accessibility, touch, and multi-monitor
  behavior would require substantially more bespoke code.
- A normal Qt window: rejected because it can activate and steal focus.
- A transparent click-through overlay: rejected because the user must deliberately click and drag
  the control.
- PySide6 with Addons: rejected because this UI uses only the Essentials modules.

## Consequences

- The runtime adds the official Qt Essentials wheels (about 79 MB in the development environment).
- Windows behavior still requires real focus tests; Qt flags alone are not treated as proof.
- Settings/dialog UI remains a later milestone and may activate only when explicitly opened.

## Verification method

- Unit tests cover every state mapping, accessibility metadata, no-focus/topmost flags, and
  multi-monitor clamping, plus idle and active recovery behavior.
- A Windows smoke test drives a real OS mouse click and compares foreground window and field focus
  before/after.
- Later hardware tests repeat the scenario in Notepad, a browser field, and another desktop field.

## References

- https://doc.qt.io/qtforpython-6/PySide6/QtCore/Qt.html
- https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html
