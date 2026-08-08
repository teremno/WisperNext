# ADR 0006: Focus context and conservative auto-paste

## Context

Wisper must place dictated text in the clipboard, but optional paste must never guess where the
user intended the text to go. Processing can take long enough for the foreground application,
window, or input context to change. Forcing focus or retrying simulated input could paste private
text into the wrong application.

## Decision

Capture an immutable foreground context at recording start: window handle, process ID, and thread
ID. Auto-paste remains disabled by default. Permit one `Ctrl+V` attempt only when all of these are
true:

- clipboard delivery was read back and verified exactly;
- the authoritative application state is `IDLE`;
- the original and current foreground contexts match exactly;
- the foreground process is not Wisper itself;
- the Win32 adapter rechecks the window handle immediately before `SendInput`.

On any failed condition, leave the verified text in the clipboard. Never call `SetForegroundWindow`,
simulate clicks, search for another window, or retry input.

## Alternatives considered

- Restore the original window with `SetForegroundWindow`: rejected because it steals focus and can
  target a stale or unintended field.
- Match process ID only: rejected because one process can own several windows and documents.
- UI Automation element tracking: deferred because a persistent automation engine adds complexity
  and still cannot guarantee user intent across arbitrary applications.
- Retry `Ctrl+V`: rejected because a delayed retry may land in a newly focused target.

## Consequences

- Auto-paste may conservatively decline even when a paste might have worked.
- Clipboard delivery remains useful whenever paste is declined.
- The future application controller must capture context before recording and transition to `IDLE`
  before requesting optional paste.

## Verification method

- Table-driven tests reject disabled, unverified, processing, unavailable, Wisper-owned, and changed
  contexts without sending input.
- Contract tests prove the safe path performs exactly one paste attempt.
- Real paste tests require an explicitly prepared disposable target and are deferred to the Windows
  UI/reliability hardware matrix.
