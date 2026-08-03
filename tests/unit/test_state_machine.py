from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from wispernext.domain import (
    ALLOWED_TRANSITIONS,
    AppError,
    ApplicationIntent,
    ApplicationState,
    ApplicationStateMachine,
    ErrorCode,
    RejectionReason,
)


def advance(machine: ApplicationStateMachine, targets: Iterable[ApplicationState]) -> None:
    for target in targets:
        assert machine.transition_to(target).accepted


PATHS: dict[ApplicationState, tuple[ApplicationState, ...]] = {
    ApplicationState.STARTING: (),
    ApplicationState.IDLE: (ApplicationState.IDLE,),
    ApplicationState.OPENING_AUDIO: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
    ),
    ApplicationState.RECORDING: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
    ),
    ApplicationState.STOPPING_AUDIO: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
        ApplicationState.STOPPING_AUDIO,
    ),
    ApplicationState.VALIDATING_AUDIO: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
        ApplicationState.STOPPING_AUDIO,
        ApplicationState.VALIDATING_AUDIO,
    ),
    ApplicationState.TRANSCRIBING: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
        ApplicationState.STOPPING_AUDIO,
        ApplicationState.VALIDATING_AUDIO,
        ApplicationState.TRANSCRIBING,
    ),
    ApplicationState.FORMATTING_OR_TRANSLATING: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
        ApplicationState.STOPPING_AUDIO,
        ApplicationState.VALIDATING_AUDIO,
        ApplicationState.TRANSCRIBING,
        ApplicationState.FORMATTING_OR_TRANSLATING,
    ),
    ApplicationState.DELIVERING_TEXT: (
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
        ApplicationState.STOPPING_AUDIO,
        ApplicationState.VALIDATING_AUDIO,
        ApplicationState.TRANSCRIBING,
        ApplicationState.DELIVERING_TEXT,
    ),
    ApplicationState.RECOVERABLE_ERROR: (),
    ApplicationState.SHUTTING_DOWN: (),
    ApplicationState.TERMINATED: (),
}


def machine_at(state: ApplicationState) -> ApplicationStateMachine:
    machine = ApplicationStateMachine()
    if state is ApplicationState.RECOVERABLE_ERROR:
        assert machine.fail(AppError(ErrorCode.UNEXPECTED, "Operation failed.", True)).accepted
    elif state is ApplicationState.SHUTTING_DOWN:
        assert machine.handle_intent(ApplicationIntent.SHUTDOWN).accepted
    elif state is ApplicationState.TERMINATED:
        assert machine.handle_intent(ApplicationIntent.SHUTDOWN).accepted
        assert machine.transition_to(ApplicationState.TERMINATED).accepted
    else:
        advance(machine, PATHS[state])
    return machine


LEGAL_FLOW_EDGES = [
    (source, target)
    for source, targets in ALLOWED_TRANSITIONS.items()
    for target in targets
    if source not in {ApplicationState.RECOVERABLE_ERROR, ApplicationState.SHUTTING_DOWN}
]

DIRECT_LEGAL_TARGETS = {
    source: set(targets)
    | (
        {ApplicationState.SHUTTING_DOWN}
        if source not in {ApplicationState.SHUTTING_DOWN, ApplicationState.TERMINATED}
        else set()
    )
    for source, targets in ALLOWED_TRANSITIONS.items()
}

ILLEGAL_DIRECT_EDGES = [
    (source, target)
    for source in ApplicationState
    for target in ApplicationState
    if target not in DIRECT_LEGAL_TARGETS[source]
]


@pytest.mark.parametrize(("source", "target"), LEGAL_FLOW_EDGES)
def test_every_normal_flow_edge_is_accepted(
    source: ApplicationState, target: ApplicationState
) -> None:
    machine = machine_at(source)

    result = machine.transition_to(target)

    assert result.accepted
    assert result.previous_state is source
    assert result.current_state is target


def test_recoverable_error_can_return_to_idle() -> None:
    machine = ApplicationStateMachine()
    error = AppError(ErrorCode.STREAM_ERROR, "Microphone capture failed.", True)
    assert machine.fail(error).accepted

    result = machine.transition_to(ApplicationState.IDLE)

    assert result.accepted
    assert machine.snapshot().last_error is error


def test_shutting_down_can_terminate() -> None:
    machine = ApplicationStateMachine()
    assert machine.handle_intent(ApplicationIntent.SHUTDOWN).accepted

    result = machine.transition_to(ApplicationState.TERMINATED)

    assert result.accepted


@pytest.mark.parametrize("source", list(ApplicationState))
def test_shutdown_is_accepted_once_from_every_non_terminal_state(
    source: ApplicationState,
) -> None:
    machine = machine_at(source)

    result = machine.handle_intent(ApplicationIntent.SHUTDOWN)

    if source in {ApplicationState.SHUTTING_DOWN, ApplicationState.TERMINATED}:
        assert not result.accepted
        assert result.rejection_reason is RejectionReason.SHUTTING_DOWN
    else:
        assert result.accepted
        assert result.current_state is ApplicationState.SHUTTING_DOWN


def test_toggle_starts_only_from_idle_and_stops_only_from_recording() -> None:
    machine = ApplicationStateMachine()
    advance(machine, (ApplicationState.IDLE,))

    start = machine.handle_intent(ApplicationIntent.TOGGLE_RECORDING)
    duplicate_start = machine.handle_intent(ApplicationIntent.TOGGLE_RECORDING)
    assert machine.transition_to(ApplicationState.RECORDING).accepted
    stop = machine.handle_intent(ApplicationIntent.TOGGLE_RECORDING)
    duplicate_stop = machine.handle_intent(ApplicationIntent.TOGGLE_RECORDING)

    assert start.accepted
    assert start.current_state is ApplicationState.OPENING_AUDIO
    assert not duplicate_start.accepted
    assert duplicate_start.rejection_reason is RejectionReason.BUSY
    assert stop.accepted
    assert stop.current_state is ApplicationState.STOPPING_AUDIO
    assert not duplicate_stop.accepted
    assert duplicate_stop.rejection_reason is RejectionReason.BUSY


def test_concurrent_toggles_accept_exactly_one_start() -> None:
    machine = ApplicationStateMachine()
    advance(machine, (ApplicationState.IDLE,))
    barrier = Barrier(3)

    def toggle() -> bool:
        barrier.wait()
        return machine.handle_intent(ApplicationIntent.TOGGLE_RECORDING).accepted

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(toggle) for _ in range(2)]
        barrier.wait()
        accepted = [future.result() for future in futures]

    assert accepted.count(True) == 1
    assert accepted.count(False) == 1
    assert machine.snapshot().state is ApplicationState.OPENING_AUDIO


def test_illegal_transition_does_not_mutate_state_or_version() -> None:
    machine = ApplicationStateMachine()
    before = machine.snapshot()

    result = machine.transition_to(ApplicationState.RECORDING)

    assert not result.accepted
    assert result.rejection_reason is RejectionReason.ILLEGAL_TRANSITION
    assert machine.snapshot() == before


@pytest.mark.parametrize(("source", "target"), ILLEGAL_DIRECT_EDGES)
def test_every_illegal_direct_transition_is_rejected_without_mutation(
    source: ApplicationState, target: ApplicationState
) -> None:
    machine = machine_at(source)
    before = machine.snapshot()

    result = machine.transition_to(target)

    assert not result.accepted
    assert machine.snapshot() == before


@pytest.mark.parametrize(
    "source",
    [
        state
        for state in ApplicationState
        if state
        not in {
            ApplicationState.RECOVERABLE_ERROR,
            ApplicationState.SHUTTING_DOWN,
            ApplicationState.TERMINATED,
        }
    ],
)
def test_every_active_state_can_fail_recoverably(source: ApplicationState) -> None:
    machine = machine_at(source)
    error = AppError(ErrorCode.UNEXPECTED, "Operation failed.", True)

    result = machine.fail(error)

    assert result.accepted
    assert result.current_state is ApplicationState.RECOVERABLE_ERROR
    assert machine.snapshot().last_error is error


def test_failure_records_typed_error_and_rejects_duplicate_failure() -> None:
    machine = ApplicationStateMachine()
    advance(machine, (ApplicationState.IDLE, ApplicationState.OPENING_AUDIO))
    error = AppError(
        ErrorCode.DEVICE_BUSY,
        "The selected microphone is busy. Close the other app and retry.",
        True,
        "correlation-123",
    )

    first = machine.fail(error)
    duplicate = machine.fail(error)

    assert first.accepted
    assert not duplicate.accepted
    assert duplicate.rejection_reason is RejectionReason.ILLEGAL_TRANSITION
    assert machine.snapshot().last_error is error


def test_retry_is_accepted_only_after_recoverable_error() -> None:
    machine = ApplicationStateMachine()
    rejected = machine.handle_intent(ApplicationIntent.RETRY)
    machine.fail(AppError(ErrorCode.UNEXPECTED, "Operation failed.", True))

    accepted = machine.handle_intent(ApplicationIntent.RETRY)

    assert not rejected.accepted
    assert rejected.rejection_reason is RejectionReason.ILLEGAL_TRANSITION
    assert accepted.accepted
    assert accepted.current_state is ApplicationState.IDLE
