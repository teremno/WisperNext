# Agent Implementation Guide

## Operating mode

Implement the product from scratch. Do not stop after generating folders or placeholder classes. Complete one testable milestone at a time, then commit and push it.

## Required milestone order

### Milestone 0 — Repository and quality gates

- Confirm package imports.
- Configure formatting, linting, typing, tests, and CI.
- Keep production modules minimal.

### Milestone 1 — Domain and state machine

- Define typed states, intents, results, and errors.
- Implement and test every legal and illegal transition.
- No UI, microphone, network, or Windows APIs yet.

### Milestone 2 — Settings and secrets

- Implement validated settings and atomic persistence.
- Store the Groq key through the documented secret mechanism, never plain application settings.
- Add migration/version handling.

### Milestone 3 — Safe audio vertical slice

- Metadata-only enumeration.
- Stable microphone identity.
- Manual selection.
- Single-owner open/start/stop/close lifecycle.
- Fake-backend contract tests.
- Real Windows microphone test before declaring the milestone complete.

### Milestone 4 — Groq transcription

- Validated audio upload.
- Timeouts, cancellation where supported, typed error mapping.
- No fallback provider.
- No weak or empty audio sent to Groq.

### Milestone 5 — Clipboard delivery

- Copy, verify, and return a typed result.
- Optional auto-paste behind a setting.
- Do not attempt aggressive focus recovery.

### Milestone 6 — Floating button and hotkeys

- Single-instance application.
- Non-activating floating button.
- Toggle behavior.
- State shown by icon/shape and color.
- Allowed global hotkeys.
- Test with Windows On-Screen Keyboard.

### Milestone 7 — Groq formatting and multilingual output

- Input language: Auto or selected language.
- Output language: Same as input or selected language.
- Support the specified 15 languages.
- Punctuation/capitalization/paragraphs only when no translation is requested.
- Reject empty, obviously malformed, or meta-commentary output.

### Milestone 8 — Settings, microphone test, diagnostics

- Simple settings UI only.
- Microphone list and explicit selection.
- Manual short microphone test.
- Privacy-safe support report.

### Milestone 9 — Packaging

- Windows installer.
- Desktop shortcut created automatically.
- Start menu shortcut.
- Clean uninstall.
- Autostart optional and disabled by default.

### Milestone 10 — Reliability release gate

- 100 repeated recordings.
- No leaked streams, threads, handles, or unbounded memory growth.
- Independent Windows application can record before and after the test.
- Bluetooth, USB, and built-in microphone scenarios documented.

## Stop conditions

Stop and request user action only for:

- Groq credentials;
- Windows permission dialogs;
- administrator permission;
- real-device interaction;
- a destructive action;
- a genuine contradiction in the authoritative documents.

Do not stop for ordinary library selection, code organization, naming, test design, or reversible implementation choices.
