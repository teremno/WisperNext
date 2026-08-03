"""Typed, privacy-safe domain errors."""

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    """Stable error identifiers used across application boundaries."""

    INVALID_TRANSITION = "invalid_transition"
    NO_DEVICE = "no_device"
    PERMISSION_DENIED = "permission_denied"
    DEVICE_BUSY = "device_busy"
    DEVICE_DISCONNECTED = "device_disconnected"
    STREAM_ERROR = "stream_error"
    NO_AUDIO_FRAMES = "no_audio_frames"
    TOO_SHORT = "too_short"
    WEAK_SIGNAL = "weak_signal"
    CLIPPED_SIGNAL = "clipped_signal"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DELIVERY_FAILED = "delivery_failed"
    INVALID_SETTINGS = "invalid_settings"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True, slots=True)
class AppError:
    """Expected failure safe to pass between domain and presentation layers."""

    code: ErrorCode
    user_message: str
    recoverable: bool
    correlation_id: str | None = None
