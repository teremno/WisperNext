"""Privacy-safe diagnostic events for intermittent runtime failures."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class DiagnosticEventName(StrEnum):
    TEXT_PROCESSING = "text_processing"
    DICTATION_COMPLETE = "dictation_complete"
    DICTATION_FAILURE = "dictation_failure"
    FLOATING_BUTTON_RECOVERY = "floating_button_recovery"


class DiagnosticOutcome(StrEnum):
    SUCCESS = "success"
    FALLBACK = "fallback"
    FAILED = "failed"


class DiagnosticReason(StrEnum):
    BUTTON_MANUAL = "button_manual"
    BUTTON_DISPLAY_CHANGED = "button_display_changed"
    BUTTON_HIDDEN = "button_hidden"
    BUTTON_MINIMIZED = "button_minimized"
    BUTTON_OFF_SCREEN = "button_off_screen"
    BUTTON_NOT_TOPMOST = "button_not_topmost"
    BUTTON_NATIVE_STATE_ERROR = "button_native_state_error"


@dataclass(frozen=True, slots=True)
class DiagnosticEvent:
    """Allowlisted metadata that cannot carry dictated or translated text."""

    operation_id: str
    name: DiagnosticEventName
    outcome: DiagnosticOutcome
    input_language: str | None = None
    output_language: str | None = None
    failure: str | None = None
    attempts: int | None = None
    reason: DiagnosticReason | None = None


class DiagnosticJournal(Protocol):
    def record(self, event: DiagnosticEvent) -> bool:
        """Persist one allowlisted event and report whether it succeeded."""
        ...


class NullDiagnosticJournal:
    """No-op journal used by isolated application tests."""

    def record(self, _event: DiagnosticEvent) -> bool:
        return True
