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
- [ ] Windows On-Screen Keyboard test is documented.

## Groq

- [x] Groq is the only cloud provider.
- [x] Weak/empty audio is never uploaded.
- [x] API timeouts are bounded.
- [x] API key is not written to logs or plain settings.
- [ ] Punctuation mode preserves words and order as far as practical.
- [ ] Translation mode uses configured output language.

## Languages

- [ ] English
- [ ] Spanish
- [ ] French
- [ ] German
- [ ] Italian
- [ ] Portuguese
- [ ] Ukrainian
- [ ] Polish
- [ ] Dutch
- [ ] Turkish
- [ ] Arabic
- [ ] Hindi
- [ ] Japanese
- [ ] Korean
- [ ] Chinese (Simplified)

## Delivery

- [x] Clipboard copy is verified.
- [x] Auto-paste is optional.
- [x] Failure preserves text in clipboard when possible.
- [x] No aggressive focus stealing or arbitrary UI automation.

## Packaging and release

- [ ] Desktop shortcut is created.
- [ ] Start menu shortcut is created.
- [x] Single-instance behavior works.
- [ ] Uninstall is clean.
- [ ] Autostart is opt-in.
- [ ] 100 repeated recordings pass on Windows hardware.
