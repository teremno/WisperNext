# Architecture

## High-level flow

```text
Floating Button / Global Hotkey
              |
              v
Application Controller + State Machine
              |
              v
Audio Session Service
              |
              v
Groq Transcription Client
              |
              v
Optional Groq Text Formatter / Translator
              |
              v
Clipboard Delivery + Optional Safe Auto-paste
```

Settings provide the selected microphone, allowed hotkey, input language, output language, auto-paste preference, and secret lookup configuration.

## Component boundaries

### UI

- Renders immutable state.
- Sends user intents only.
- Owns no audio stream, Groq client, clipboard operation, or business state.
- The floating button is a non-activating Windows tool window where feasible.

### Application controller

- Owns the authoritative state machine.
- Rejects duplicate or invalid transitions.
- Coordinates audio, Groq, and delivery.
- Never performs blocking work on the Qt thread.

### Audio session service

- Sole owner of capture stream creation and closure.
- Enumerates metadata without probe recordings.
- Resolves the stable selected device identity.
- Opens exactly one selected endpoint per recording.
- Never changes Windows audio configuration.

### Groq client

- Transcribes valid audio.
- Optionally formats punctuation or translates.
- Uses bounded timeouts and typed errors.
- Never logs API keys, audio, or dictated text.

### Delivery service

- Copies text to clipboard.
- Reads it back to verify success.
- Auto-pastes only when enabled and the delivery context is considered safe.
- Does not erase the previous clipboard on failure.

## Dependency direction

```text
UI / Windows adapters / Groq adapter / storage
                    |
                    v
             application services
                    |
                    v
                 domain models
```

Domain and application code must not depend directly on PySide6, PortAudio/sounddevice, Groq SDK internals, or Win32 APIs.

## Proposed package structure

```text
src/wispernext/
  application/
  audio/
  groq/
  infrastructure/
  platform/windows/
  ui/
```

Do not split this into more modules unless a real responsibility boundary appears.
