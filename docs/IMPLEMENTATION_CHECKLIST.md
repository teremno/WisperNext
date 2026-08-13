# Implementation Checklist

## Foundation

- [x] Package installs in editable mode.
- [x] CI runs on Windows.
- [x] Ruff, mypy, and pytest pass.
- [x] Single authoritative state machine exists.

## Audio safety

- [x] Device enumeration opens zero streams.
- [x] One start opens one selected endpoint.
- [x] One stop closes it exactly once.
- [x] Cleanup is idempotent.
- [x] No automatic physical microphone fallback.
- [x] No Windows audio mutation exists.
- [x] Built-in, USB, and Bluetooth devices are represented.

## Accessibility and input

- [x] Floating button does not steal focus on Windows 11.
- [x] Same button toggles start/stop.
- [ ] Allowed hotkeys work.
- [x] Letters, digits, and ordinary punctuation are rejected as unmodified hotkeys.
- [x] Windows On-Screen Keyboard test is documented (no global hotkey event observed; floating
  button remains the verified keyboard-free control).

## Groq

- [x] Groq is the only cloud provider.
- [x] Weak/empty audio is never uploaded.
- [x] API timeouts are bounded.
- [x] API key is not written to logs or plain settings.
- [x] Punctuation mode preserves words and order as far as practical.
- [x] Translation mode uses configured output language.

## Languages

- [x] English
- [x] Spanish
- [x] French
- [x] German
- [x] Italian
- [x] Portuguese
- [x] Ukrainian
- [x] Russian
- [x] Polish
- [x] Dutch
- [x] Turkish
- [x] Arabic
- [x] Hindi
- [x] Japanese
- [x] Korean
- [x] Chinese (Simplified)
- [x] Interface is available in English, Ukrainian, and Russian.
- [x] Supported Windows interface locales are selected automatically.
- [x] Unsupported Windows interface locales fall back to English.

## Delivery

- [x] Clipboard copy is verified.
- [x] Auto-paste is optional.
- [x] Failure preserves text in clipboard when possible.
- [x] No aggressive focus stealing or arbitrary UI automation.

## Private diagnostics

- [x] Diagnostic events use an explicit metadata allowlist and contain no dictated text, audio,
  clipboard content, API keys, window titles, or target-application names.
- [x] One operation ID correlates processing and completion/failure events.
- [x] Journal storage is bounded to five rotating 1 MiB JSONL files.
- [x] Journal failure does not stop dictation and is surfaced once to the user.
- [x] Invalid cross-language output is retried once and then uses an explicit safe fallback.

## Packaging and release

- [ ] Desktop shortcut is created.
- [ ] Start menu shortcut is created.
- [x] Single-instance behavior works.
- [ ] Uninstall is clean.
- [ ] Autostart is opt-in.
- [ ] 100 repeated recordings pass on Windows hardware.
