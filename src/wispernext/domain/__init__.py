"""Platform-independent domain contracts for WisperNext."""

from wispernext.domain.errors import AppError, ErrorCode
from wispernext.domain.hotkeys import (
    HotkeyModifier,
    HotkeySpec,
    HotkeyValidationError,
    parse_hotkey,
)
from wispernext.domain.models import ApplicationIntent, MicrophoneSelectionMode, RejectionReason
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
    "HotkeyModifier",
    "HotkeySpec",
    "HotkeyValidationError",
    "IntentResult",
    "MicrophoneSelectionMode",
    "RejectionReason",
    "StateSnapshot",
    "TransitionResult",
    "parse_hotkey",
]
