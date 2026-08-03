# ADR 0003: Windows audio backend

## Context

WisperNext needs metadata-only enumeration and exactly one explicitly selected mono float32
input stream. It must not change Windows defaults, levels, drivers, services, privacy
settings, or exclusive-mode configuration.

## Decision

Use `python-sounddevice` 0.5.x as the thin PortAudio binding. Enumerate with
`query_devices()`/`query_hostapis()` and capture through one `RawInputStream` in the device's
default sample rate and PortAudio's normal mode. Do not call global PortAudio
terminate/reinitialize functions and do not pass exclusive-mode settings. Keep all library
types behind the `AudioBackend` protocol.

This is the only runtime dependency added in Milestone 3. It provides maintained Windows
wheels containing the required PortAudio binding; signal analysis and resampling remain
standard-library code.

## Alternatives considered

- Direct WASAPI COM implementation: rejected for the first slice because it substantially
  increases native lifetime and packaging risk.
- SoundCard: rejected because its own documentation describes the project as still under
  development with known issues.
- PyAudio: rejected because sounddevice provides the required raw callback API and simpler
  current Windows wheel installation.

## Consequences

- Hardware behavior depends on PortAudio's Windows host APIs and needs real Windows tests.
- The adapter can be replaced without changing the session service or domain code.
- Callback work is bounded to copying float32 frames and recording status flags.

## Verification method

- Unit test proves enumeration constructs zero streams.
- Fake-backend contracts prove one start/stop/close lifecycle and partial-open cleanup.
- Opt-in Windows tests must verify built-in, USB, and Bluetooth endpoints and 100 repeats.
