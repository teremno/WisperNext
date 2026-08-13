import json
from datetime import UTC, datetime
from pathlib import Path

from wispernext.application import (
    DiagnosticEvent,
    DiagnosticEventName,
    DiagnosticOutcome,
)
from wispernext.infrastructure.diagnostics import RotatingDiagnosticJournal


def event(operation_id: str = "operation-1") -> DiagnosticEvent:
    return DiagnosticEvent(
        operation_id=operation_id,
        name=DiagnosticEventName.TEXT_PROCESSING,
        outcome=DiagnosticOutcome.FALLBACK,
        input_language="uk",
        output_language="ru",
        failure="unsafe_response",
        attempts=2,
    )


def test_journal_writes_only_allowlisted_privacy_safe_fields(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "diagnostics.jsonl"
    journal = RotatingDiagnosticJournal(
        path,
        clock=lambda: datetime(2026, 8, 13, 17, 0, tzinfo=UTC),
    )

    assert journal.record(event())

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "timestamp": "2026-08-13T17:00:00+00:00",
        "operation_id": "operation-1",
        "event": "text_processing",
        "outcome": "fallback",
        "input_language": "uk",
        "output_language": "ru",
        "failure": "unsafe_response",
        "attempts": 2,
    }
    serialized = path.read_text(encoding="utf-8").casefold()
    assert "transcript" not in serialized
    assert "api_key" not in serialized
    assert "clipboard" not in serialized
    assert "audio" not in serialized


def test_journal_rotation_bounds_file_count_and_size(tmp_path: Path) -> None:
    path = tmp_path / "diagnostics.jsonl"
    journal = RotatingDiagnosticJournal(path, max_bytes=300, backup_count=4)

    for index in range(20):
        assert journal.record(event(f"operation-{index}"))

    files = tuple(tmp_path.glob("diagnostics.jsonl*"))
    assert len(files) <= 5
    assert all(item.stat().st_size <= 300 for item in files)


def test_journal_failure_is_reported_without_raising(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("blocked", encoding="utf-8")
    journal = RotatingDiagnosticJournal(blocked_parent / "diagnostics.jsonl")

    assert not journal.record(event())
