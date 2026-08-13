"""Bounded rotating JSONL persistence for privacy-safe diagnostic events."""

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from wispernext.application.diagnostics import DiagnosticEvent


class RotatingDiagnosticJournal:
    """Append allowlisted events while bounding disk use and failing open."""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int = 1_048_576,
        backup_count: int = 4,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_bytes < 256:
            raise ValueError("max_bytes must leave room for one diagnostic event.")
        if not 0 <= backup_count <= 20:
            raise ValueError("backup_count must be from 0 to 20.")
        self._path = path
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record(self, event: DiagnosticEvent) -> bool:
        payload = {
            "timestamp": self._clock().astimezone(UTC).isoformat(),
            "operation_id": event.operation_id,
            "event": event.name.value,
            "outcome": event.outcome.value,
            "input_language": event.input_language,
            "output_language": event.output_language,
            "failure": event.failure,
            "attempts": event.attempts,
        }
        encoded = (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        if len(encoded) > self._max_bytes:
            return False
        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                current_size = self._path.stat().st_size if self._path.exists() else 0
                if current_size + len(encoded) > self._max_bytes:
                    self._rotate()
                with self._path.open("ab") as stream:
                    stream.write(encoded)
                    stream.flush()
            except OSError:
                return False
        return True

    def _rotate(self) -> None:
        if self._backup_count == 0:
            self._path.unlink(missing_ok=True)
            return
        oldest = self._backup_path(self._backup_count)
        oldest.unlink(missing_ok=True)
        for index in range(self._backup_count - 1, 0, -1):
            source = self._backup_path(index)
            if source.exists():
                os.replace(source, self._backup_path(index + 1))
        if self._path.exists():
            os.replace(self._path, self._backup_path(1))

    def _backup_path(self, index: int) -> Path:
        return self._path.with_name(f"{self._path.name}.{index}")
