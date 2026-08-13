"""Privacy-safe diagnostic events for intermittent runtime failures."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class DiagnosticEventName(StrEnum):
    TEXT_PROCESSING = "text_processing"
    DICTATION_COMPLETE = "dictation_complete"
    DICTATION_FAILURE = "dictation_failure"


class DiagnosticOutcome(StrEnum):
    SUCCESS = "success"
    FALLBACK = "fallback"
    FAILED = "failed"


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


class DiagnosticJournal(Protocol):
    def record(self, event: DiagnosticEvent) -> bool:
        """Persist one allowlisted event and report whether it succeeded."""
        ...


class NullDiagnosticJournal:
    """No-op journal used by isolated application tests."""

    def record(self, _event: DiagnosticEvent) -> bool:
        return True
