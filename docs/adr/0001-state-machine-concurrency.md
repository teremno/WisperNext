# ADR 0001: State-machine concurrency

## Context

Button, hotkey, worker completion, failure, and shutdown events may arrive from different
threads. Two simultaneous toggle events must never start parallel recording lifecycles,
and readers must not observe a partially updated state.

## Decision

Use one in-process `ApplicationStateMachine` as the authoritative lifecycle owner. It
serializes transitions with a standard-library reentrant lock and exposes immutable typed
snapshots and results. Expected duplicate or illegal events return typed rejections without
mutating state or raising an exception.

The future application controller will perform slow audio, network, and delivery work
outside this lock and submit only lifecycle transitions to the state machine.

## Alternatives considered

- Rely on the Python GIL: rejected because compound state checks and updates are not a
  stable synchronization contract.
- Use an asyncio-only state machine: rejected because the Windows UI and platform adapters
  have not yet selected one shared event-loop model.
- Use a dedicated actor thread now: rejected as unnecessary infrastructure for the current
  domain milestone.

## Consequences

- Concurrent intent handling is deterministic and has no third-party dependency.
- State-machine critical sections must remain small and contain no blocking I/O.
- Cross-process single-instance enforcement remains a separate Windows-platform concern.

## Verification method

- Exhaustive legal and illegal transition tests.
- Concurrent toggle test proving exactly one start is accepted.
- Full Ruff, mypy, and pytest quality gates on supported Python versions.
