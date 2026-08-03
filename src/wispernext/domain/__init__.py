"""Platform-independent domain contracts for WisperNext."""

from wispernext.domain.errors import AppError, ErrorCode
from wispernext.domain.models import ApplicationIntent, RejectionReason
from wispernext.domain.state import (
    ALLOWED_TRANSITIONS,
    ApplicationState,
    ApplicationStateMachine,
    IntentResult,
    StateSnapshot,
    TransitionResult,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "AppError",
    "ApplicationIntent",
    "ApplicationState",
    "ApplicationStateMachine",
    "ErrorCode",
    "IntentResult",
    "RejectionReason",
    "StateSnapshot",
    "TransitionResult",
]
