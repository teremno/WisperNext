# ADR 0004: Stable microphone identity

## Context

PortAudio runtime indices can change between launches and must never be persisted as device
identity. The public sounddevice metadata does not expose a Windows MMDevice endpoint ID.
Automatic fallback to another physical microphone is forbidden.

## Decision

Persist a versioned SHA-256-derived preference key over normalized device name, host API,
default sample rate, and maximum input-channel count, plus the last-seen metadata. Keep the
runtime index only in the current enumeration result.

Resolve only an exact unique key. Return typed `NOT_FOUND` or `AMBIGUOUS` outcomes and require
explicit user selection instead of guessing. Treat connection-kind labels as display hints
derived from metadata, never as selection authority.

## Alternatives considered

- Persist PortAudio index: rejected because it is unstable and explicitly forbidden.
- Match name only: rejected because identical names are common and would create ambiguity.
- Add a native MMDevice enumerator now: deferred until a reliable mapping between its
  endpoint IDs and PortAudio capture devices can be implemented and hardware-verified.

## Consequences

- Runtime-index changes do not break a unique unchanged device.
- Metadata changes may require reselection, which is safer than choosing a different device.
- Two metadata-identical devices intentionally resolve as ambiguous.

## Verification method

- Tests move the same identity across runtime indices.
- Tests require ambiguity for duplicate identities and not-found for missing identities.
- Hardware tests must document identity behavior across reconnect and reboot scenarios.
