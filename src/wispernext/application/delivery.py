"""Verified clipboard delivery and conservative auto-paste policy."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from wispernext.domain import ApplicationState


class ClipboardAdapterError(RuntimeError):
    """Privacy-safe clipboard adapter failure."""


class ClipboardPort(Protocol):
    def read_text(self) -> str | None: ...

    def write_text(self, text: str) -> None: ...


class ClipboardDeliveryStatus(StrEnum):
    VERIFIED = "verified"
    INVALID_TEXT = "invalid_text"
    CLIPBOARD_UNAVAILABLE = "clipboard_unavailable"
    VERIFICATION_FAILED = "verification_failed"
    RESTORE_FAILED = "restore_failed"


@dataclass(frozen=True, slots=True)
class ClipboardDeliveryResult:
    status: ClipboardDeliveryStatus
    attempts: int
    previous_text_restored: bool

    @property
    def verified(self) -> bool:
        return self.status is ClipboardDeliveryStatus.VERIFIED


class ClipboardDeliveryService:
    """Write, read back, and verify text without unbounded clipboard retries."""

    def __init__(
        self,
        clipboard: ClipboardPort,
        *,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.05,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must not be negative")
        self._clipboard = clipboard
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._sleeper = sleeper

    def deliver(self, text: str) -> ClipboardDeliveryResult:
        if not text:
            return ClipboardDeliveryResult(ClipboardDeliveryStatus.INVALID_TEXT, 0, False)
        try:
            previous_text = self._clipboard.read_text()
        except ClipboardAdapterError:
            return ClipboardDeliveryResult(ClipboardDeliveryStatus.CLIPBOARD_UNAVAILABLE, 0, False)

        for attempt in range(1, self._max_attempts + 1):
            try:
                self._clipboard.write_text(text)
                if self._clipboard.read_text() == text:
                    return ClipboardDeliveryResult(
                        ClipboardDeliveryStatus.VERIFIED,
                        attempt,
                        False,
                    )
            except ClipboardAdapterError:
                pass
            if attempt < self._max_attempts:
                self._sleeper(self._retry_delay_seconds)

        restored = self._restore(previous_text)
        status = (
            ClipboardDeliveryStatus.VERIFICATION_FAILED
            if restored
            else ClipboardDeliveryStatus.RESTORE_FAILED
        )
        return ClipboardDeliveryResult(status, self._max_attempts, restored)

    def _restore(self, previous_text: str | None) -> bool:
        if previous_text is None:
            return False
        try:
            self._clipboard.write_text(previous_text)
            return self._clipboard.read_text() == previous_text
        except ClipboardAdapterError:
            return False


@dataclass(frozen=True, slots=True)
class FocusContext:
    window_handle: int
    process_id: int
    thread_id: int


class PastePort(Protocol):
    def current_focus(self) -> FocusContext | None: ...

    def paste_once(self, expected_window_handle: int) -> bool: ...


class AutoPasteStatus(StrEnum):
    PASTED = "pasted"
    DISABLED = "disabled"
    CLIPBOARD_NOT_VERIFIED = "clipboard_not_verified"
    PROCESSING_ACTIVE = "processing_active"
    TARGET_UNAVAILABLE = "target_unavailable"
    WISPER_HAS_FOCUS = "wisper_has_focus"
    TARGET_CHANGED = "target_changed"
    INPUT_REJECTED = "input_rejected"


@dataclass(frozen=True, slots=True)
class AutoPasteResult:
    status: AutoPasteStatus

    @property
    def pasted(self) -> bool:
        return self.status is AutoPasteStatus.PASTED


class AutoPasteService:
    """Send at most one paste only when the original foreground context is unchanged."""

    def __init__(self, paste_port: PastePort, *, wisper_process_id: int) -> None:
        self._paste_port = paste_port
        self._wisper_process_id = wisper_process_id

    def try_paste(
        self,
        *,
        enabled: bool,
        clipboard_delivery: ClipboardDeliveryResult,
        recording_context: FocusContext | None,
        application_state: ApplicationState,
    ) -> AutoPasteResult:
        if not enabled:
            return AutoPasteResult(AutoPasteStatus.DISABLED)
        if not clipboard_delivery.verified:
            return AutoPasteResult(AutoPasteStatus.CLIPBOARD_NOT_VERIFIED)
        if application_state is not ApplicationState.IDLE:
            return AutoPasteResult(AutoPasteStatus.PROCESSING_ACTIVE)
        current = self._paste_port.current_focus()
        if current is None or recording_context is None:
            return AutoPasteResult(AutoPasteStatus.TARGET_UNAVAILABLE)
        if current.process_id == self._wisper_process_id:
            return AutoPasteResult(AutoPasteStatus.WISPER_HAS_FOCUS)
        if current != recording_context:
            return AutoPasteResult(AutoPasteStatus.TARGET_CHANGED)
        if not self._paste_port.paste_once(current.window_handle):
            return AutoPasteResult(AutoPasteStatus.INPUT_REJECTED)
        return AutoPasteResult(AutoPasteStatus.PASTED)
