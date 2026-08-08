from dataclasses import dataclass

import pytest

from wispernext.application import (
    AutoPasteService,
    AutoPasteStatus,
    ClipboardAdapterError,
    ClipboardDeliveryResult,
    ClipboardDeliveryService,
    ClipboardDeliveryStatus,
    FocusContext,
)
from wispernext.domain import ApplicationState


class MemoryClipboard:
    def __init__(
        self,
        text: str | None,
        *,
        corrupt_target_writes: int = 0,
        fail_initial_read: bool = False,
        fail_restore: bool = False,
    ) -> None:
        self.text = text
        self.corrupt_target_writes = corrupt_target_writes
        self.fail_initial_read = fail_initial_read
        self.fail_restore = fail_restore
        self.read_count = 0
        self.write_count = 0

    def read_text(self) -> str | None:
        self.read_count += 1
        if self.fail_initial_read and self.read_count == 1:
            raise ClipboardAdapterError("unavailable")
        return self.text

    def write_text(self, text: str) -> None:
        self.write_count += 1
        if text == "new" and self.corrupt_target_writes > 0:
            self.corrupt_target_writes -= 1
            self.text = "corrupt"
            return
        if text == "old" and self.fail_restore:
            raise ClipboardAdapterError("restore failed")
        self.text = text


def test_delivery_writes_reads_back_and_verifies_exact_text() -> None:
    clipboard = MemoryClipboard("old")
    result = ClipboardDeliveryService(clipboard).deliver("new")

    assert result.status is ClipboardDeliveryStatus.VERIFIED
    assert result.attempts == 1
    assert clipboard.text == "new"


def test_delivery_retries_only_within_bound_then_succeeds() -> None:
    clipboard = MemoryClipboard("old", corrupt_target_writes=1)
    delays: list[float] = []
    service = ClipboardDeliveryService(clipboard, sleeper=delays.append)

    result = service.deliver("new")

    assert result.status is ClipboardDeliveryStatus.VERIFIED
    assert result.attempts == 2
    assert delays == [0.05]


def test_failed_verification_restores_previous_text() -> None:
    clipboard = MemoryClipboard("old", corrupt_target_writes=3)

    result = ClipboardDeliveryService(clipboard).deliver("new")

    assert result.status is ClipboardDeliveryStatus.VERIFICATION_FAILED
    assert result.previous_text_restored
    assert clipboard.text == "old"


def test_restore_failure_is_explicit_and_never_reported_as_verified() -> None:
    clipboard = MemoryClipboard("old", corrupt_target_writes=3, fail_restore=True)

    result = ClipboardDeliveryService(clipboard).deliver("new")

    assert result.status is ClipboardDeliveryStatus.RESTORE_FAILED
    assert not result.verified
    assert not result.previous_text_restored


def test_unavailable_clipboard_is_not_written() -> None:
    clipboard = MemoryClipboard("old", fail_initial_read=True)

    result = ClipboardDeliveryService(clipboard).deliver("new")

    assert result.status is ClipboardDeliveryStatus.CLIPBOARD_UNAVAILABLE
    assert clipboard.write_count == 0
    assert clipboard.text == "old"


def test_empty_text_is_rejected_without_touching_clipboard() -> None:
    clipboard = MemoryClipboard("old")

    result = ClipboardDeliveryService(clipboard).deliver("")

    assert result.status is ClipboardDeliveryStatus.INVALID_TEXT
    assert clipboard.read_count == 0
    assert clipboard.write_count == 0


@dataclass
class FakePastePort:
    focus: FocusContext | None
    accepts_input: bool = True
    paste_calls: int = 0

    def current_focus(self) -> FocusContext | None:
        return self.focus

    def paste_once(self, expected_window_handle: int) -> bool:
        self.paste_calls += 1
        assert self.focus is not None
        assert expected_window_handle == self.focus.window_handle
        return self.accepts_input


VERIFIED = ClipboardDeliveryResult(ClipboardDeliveryStatus.VERIFIED, 1, False)
FAILED = ClipboardDeliveryResult(ClipboardDeliveryStatus.VERIFICATION_FAILED, 3, True)
TARGET = FocusContext(100, 200, 300)


@pytest.mark.parametrize(
    "enabled, delivery, state, recording, current, own_pid, expected",
    [
        (False, VERIFIED, ApplicationState.IDLE, TARGET, TARGET, 999, AutoPasteStatus.DISABLED),
        (
            True,
            FAILED,
            ApplicationState.IDLE,
            TARGET,
            TARGET,
            999,
            AutoPasteStatus.CLIPBOARD_NOT_VERIFIED,
        ),
        (
            True,
            VERIFIED,
            ApplicationState.TRANSCRIBING,
            TARGET,
            TARGET,
            999,
            AutoPasteStatus.PROCESSING_ACTIVE,
        ),
        (
            True,
            VERIFIED,
            ApplicationState.IDLE,
            None,
            TARGET,
            999,
            AutoPasteStatus.TARGET_UNAVAILABLE,
        ),
        (
            True,
            VERIFIED,
            ApplicationState.IDLE,
            TARGET,
            FocusContext(101, 200, 300),
            999,
            AutoPasteStatus.TARGET_CHANGED,
        ),
        (
            True,
            VERIFIED,
            ApplicationState.IDLE,
            TARGET,
            TARGET,
            200,
            AutoPasteStatus.WISPER_HAS_FOCUS,
        ),
    ],
)
def test_auto_paste_policy_denies_unsafe_contexts_without_sending_input(
    enabled: bool,
    delivery: ClipboardDeliveryResult,
    state: ApplicationState,
    recording: FocusContext | None,
    current: FocusContext | None,
    own_pid: int,
    expected: AutoPasteStatus,
) -> None:
    port = FakePastePort(current)
    service = AutoPasteService(port, wisper_process_id=own_pid)

    result = service.try_paste(
        enabled=enabled,
        clipboard_delivery=delivery,
        recording_context=recording,
        application_state=state,
    )

    assert result.status is expected
    assert port.paste_calls == 0


@pytest.mark.parametrize(
    "accepts_input, expected",
    [(True, AutoPasteStatus.PASTED), (False, AutoPasteStatus.INPUT_REJECTED)],
)
def test_safe_auto_paste_sends_exactly_one_input_attempt(
    accepts_input: bool, expected: AutoPasteStatus
) -> None:
    port = FakePastePort(TARGET, accepts_input=accepts_input)
    service = AutoPasteService(port, wisper_process_id=999)

    result = service.try_paste(
        enabled=True,
        clipboard_delivery=VERIFIED,
        recording_context=TARGET,
        application_state=ApplicationState.IDLE,
    )

    assert result.status is expected
    assert port.paste_calls == 1
