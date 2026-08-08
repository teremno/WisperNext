# ADR 0008: Global hotkey and single-instance policy

## Context

Wisper needs one global toggle that can arrive from a physical keyboard or Windows On-Screen
Keyboard without intercepting ordinary typing. A repeated desktop launch must not create a second
microphone owner.

## Decision

Validate hotkeys with a platform-independent parser before registration. Permit F1-F24, documented
special/numpad/media keys, and modifier combinations. Reject unmodified letters, digits,
punctuation, duplicate modifiers, modifier-only strings, and unknown keys.

Use Win32 `RegisterHotKey` with `MOD_NOREPEAT`, never a low-level keyboard hook. Install one Qt
native event filter for `windows_dispatcher_MSG` and translate only Wisper's `WM_HOTKEY` ID into
the same controller toggle used by the floating button. Registration failure leaves the button
usable and presents a short status.

Use a session-local Win32 named mutex, `Local\\WisperNext.Singleton.v1`, acquired before creating
Qt or any application service. A second process closes its duplicate handle and exits without
opening a microphone, registering a hotkey, or showing another UI.

## Alternatives considered

- Low-level keyboard hook: rejected because it observes unrelated keys and adds privacy/reliability
  risk.
- Polling key state: rejected because it is unreliable and assumes a physical input path.
- File lock: rejected because stale files and filesystem permissions complicate recovery.
- Qt local socket: unnecessary because the second launch does not need to send commands yet.

## Consequences

- Windows decides whether a key is available; conflicts are explicit and non-fatal.
- On-Screen Keyboard support depends on Windows delivering the same normal registered-hotkey path
  and therefore must be observed on real Windows 11.
- The mutex is released deterministically on normal shutdown and by Windows on process exit.

## Verification method

- Table-driven tests cover all accepted and rejected hotkey classes.
- A real named-mutex test proves only one owner and successful reacquisition after cleanup.
- Opt-in Windows tests receive one special key from a physical keyboard and On-Screen Keyboard,
  plus one modifier combination.

## Reference

- https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractNativeEventFilter.html
