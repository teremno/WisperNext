"""Authoritative, thread-safe application state machine."""

from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Final

from wispernext.domain.errors import AppError
from wispernext.domain.models import ApplicationIntent, RejectionReason


class ApplicationState(StrEnum):
    """All lifecycle states defined by the product specification."""

    STARTING = "starting"
    IDLE = "idle"
    OPENING_AUDIO = "opening_audio"
    RECORDING = "recording"
    STOPPING_AUDIO = "stopping_audio"
    VALIDATING_AUDIO = "validating_audio"
    TRANSCRIBING = "transcribing"
    FORMATTING_OR_TRANSLATING = "formatting_or_translating"
    DELIVERING_TEXT = "delivering_text"
    RECOVERABLE_ERROR = "recoverable_error"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


_FLOW_TRANSITIONS: Final[dict[ApplicationState, frozenset[ApplicationState]]] = {
    ApplicationState.STARTING: frozenset({ApplicationState.IDLE}),
    ApplicationState.IDLE: frozenset({ApplicationState.OPENING_AUDIO}),
    ApplicationState.OPENING_AUDIO: frozenset({ApplicationState.RECORDING}),
    ApplicationState.RECORDING: frozenset({ApplicationState.STOPPING_AUDIO}),
    ApplicationState.STOPPING_AUDIO: frozenset({ApplicationState.VALIDATING_AUDIO}),
    ApplicationState.VALIDATING_AUDIO: frozenset({ApplicationState.TRANSCRIBING}),
    ApplicationState.TRANSCRIBING: frozenset(
        {
            ApplicationState.FORMATTING_OR_TRANSLATING,
            ApplicationState.DELIVERING_TEXT,
        }
    ),
    ApplicationState.FORMATTING_OR_TRANSLATING: frozenset({ApplicationState.DELIVERING_TEXT}),
    ApplicationState.DELIVERING_TEXT: frozenset({ApplicationState.IDLE}),
    ApplicationState.RECOVERABLE_ERROR: frozenset({ApplicationState.IDLE}),
    ApplicationState.SHUTTING_DOWN: frozenset({ApplicationState.TERMINATED}),
    ApplicationState.TERMINATED: frozenset(),
}

ALLOWED_TRANSITIONS = MappingProxyType(_FLOW_TRANSITIONS)

_FAILABLE_STATES: Final[frozenset[ApplicationState]] = frozenset(
    state
    for state in ApplicationState
    if state
    not in {
        ApplicationState.RECOVERABLE_ERROR,
        ApplicationState.SHUTTING_DOWN,
        ApplicationState.TERMINATED,
    }
)


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    """Immutable view rendered by callers without owning state."""

    state: ApplicationState
    version: int
    last_error: AppError | None


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Caller-visible result of processing an application intent."""

    intent: ApplicationIntent
    accepted: bool
    previous_state: ApplicationState
    current_state: ApplicationState
    rejection_reason: RejectionReason | None = None


@dataclass(frozen=True, slots=True)
class TransitionResult:
    """Result of a requested state transition."""

    accepted: bool
    previous_state: ApplicationState
    current_state: ApplicationState
    version: int
    rejection_reason: RejectionReason | None = None


class ApplicationStateMachine:
    """Validate and serialize all application lifecycle transitions."""

    def __init__(self) -> None:
        self._state = ApplicationState.STARTING
        self._version = 0
        self._last_error: AppError | None = None
        self._lock = RLock()

    def snapshot(self) -> StateSnapshot:
        """Return an immutable, consistent view of current state."""
        with self._lock:
            return StateSnapshot(self._state, self._version, self._last_error)

    def transition_to(self, target: ApplicationState) -> TransitionResult:
        """Apply a legal flow transition or return a typed rejection."""
        with self._lock:
            return self._transition_locked(target)

    def handle_intent(self, intent: ApplicationIntent) -> IntentResult:
        """Translate a user intent into one validated lifecycle transition."""
        with self._lock:
            previous = self._state
            if intent is ApplicationIntent.TOGGLE_RECORDING:
                target = self._toggle_target_locked()
                if target is None:
                    reason = self._intent_rejection_reason_locked()
                    return IntentResult(
                        intent=intent,
                        accepted=False,
                        previous_state=previous,
                        current_state=self._state,
                        rejection_reason=reason,
                    )
            elif intent is ApplicationIntent.RETRY:
                if self._state is not ApplicationState.RECOVERABLE_ERROR:
                    return IntentResult(
                        intent=intent,
                        accepted=False,
                        previous_state=previous,
                        current_state=self._state,
                        rejection_reason=self._intent_rejection_reason_locked(),
                    )
                target = ApplicationState.IDLE
            else:
                target = ApplicationState.SHUTTING_DOWN

            transition = self._transition_locked(target)
            return IntentResult(
                intent=intent,
                accepted=transition.accepted,
                previous_state=transition.previous_state,
                current_state=transition.current_state,
                rejection_reason=transition.rejection_reason,
            )

    def fail(self, error: AppError) -> TransitionResult:
        """Enter recoverable error state while retaining a safe diagnostic error."""
        with self._lock:
            previous = self._state
            if previous not in _FAILABLE_STATES:
                return self._rejected_locked(previous, RejectionReason.ILLEGAL_TRANSITION)
            self._last_error = error
            return self._accept_locked(previous, ApplicationState.RECOVERABLE_ERROR)

    def _transition_locked(self, target: ApplicationState) -> TransitionResult:
        previous = self._state
        if target is ApplicationState.SHUTTING_DOWN:
            if previous in {ApplicationState.SHUTTING_DOWN, ApplicationState.TERMINATED}:
                return self._rejected_locked(previous, RejectionReason.SHUTTING_DOWN)
            return self._accept_locked(previous, target)

        if target not in ALLOWED_TRANSITIONS[previous]:
            return self._rejected_locked(previous, self._intent_rejection_reason_locked())
        return self._accept_locked(previous, target)

    def _toggle_target_locked(self) -> ApplicationState | None:
        if self._state is ApplicationState.IDLE:
            return ApplicationState.OPENING_AUDIO
        if self._state is ApplicationState.RECORDING:
            return ApplicationState.STOPPING_AUDIO
        return None

    def _intent_rejection_reason_locked(self) -> RejectionReason:
        if self._state in {ApplicationState.SHUTTING_DOWN, ApplicationState.TERMINATED}:
            return RejectionReason.SHUTTING_DOWN
        if self._state in {ApplicationState.STARTING, ApplicationState.RECOVERABLE_ERROR}:
            return RejectionReason.ILLEGAL_TRANSITION
        return RejectionReason.BUSY

    def _accept_locked(
        self, previous: ApplicationState, target: ApplicationState
    ) -> TransitionResult:
        self._state = target
        self._version += 1
        return TransitionResult(True, previous, target, self._version)

    def _rejected_locked(
        self, previous: ApplicationState, reason: RejectionReason
    ) -> TransitionResult:
        return TransitionResult(False, previous, self._state, self._version, reason)
