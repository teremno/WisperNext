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

- [ ] Floating button does not steal focus on Windows 11.
- [ ] Same button toggles start/stop.
- [ ] Allowed hotkeys work.
- [ ] Letters, digits, and ordinary punctuation are rejected as unmodified hotkeys.
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

- [ ] Clipboard copy is verified.
- [ ] Auto-paste is optional.
- [ ] Failure preserves text in clipboard when possible.
- [ ] No aggressive focus stealing or arbitrary UI automation.

## Packaging and release

- [ ] Desktop shortcut is created.
- [ ] Start menu shortcut is created.
- [ ] Single-instance behavior works.
- [ ] Uninstall is clean.
- [ ] Autostart is opt-in.
- [ ] 100 repeated recordings pass on Windows hardware.
