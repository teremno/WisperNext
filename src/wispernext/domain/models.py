"""Shared typed values for user intent handling."""

from enum import StrEnum


class ApplicationIntent(StrEnum):
    """User-level commands accepted by the application controller."""

    TOGGLE_RECORDING = "toggle_recording"
    RETRY = "retry"
    SHUTDOWN = "shutdown"


class RejectionReason(StrEnum):
    """Expected reasons why an intent cannot be accepted now."""

    BUSY = "busy"
    ILLEGAL_TRANSITION = "illegal_transition"
    SHUTTING_DOWN = "shutting_down"


class MicrophoneSelectionMode(StrEnum):
    """Explicit policy for resolving the microphone used by a recording."""

    SYSTEM_DEFAULT = "system_default"
    MANUAL = "manual"
