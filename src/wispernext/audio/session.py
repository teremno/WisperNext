"""Single-owner, bounded microphone capture lifecycle."""

from array import array
from dataclasses import dataclass
from threading import RLock
from uuid import uuid4

from wispernext.audio.backend import AudioBackend, InputStream
from wispernext.audio.devices import InputDevice
from wispernext.audio.signal import CapturedAudio


class AudioSessionError(RuntimeError):
    """Raised when capture lifecycle invariants cannot be satisfied."""


@dataclass(frozen=True, slots=True)
class CaptureStart:
    capture_id: str
    sample_rate: int


class AudioSessionService:
    """The only service allowed to create, stop, or close capture streams."""

    def __init__(self, backend: AudioBackend, *, max_duration_seconds: int = 300) -> None:
        if max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")
        self._backend = backend
        self._max_duration_seconds = max_duration_seconds
        self._lock = RLock()
        self._stream: InputStream | None = None
        self._closing = False
        self._capture_id: str | None = None
        self._sample_rate = 0
        self._samples = array("f")
        self._statuses: list[str] = []
        self._accepting = False

    def start(self, device: InputDevice) -> CaptureStart:
        with self._lock:
            if self._stream is not None or self._closing:
                raise AudioSessionError("A capture stream is already owned.")
            capture_id = uuid4().hex
            self._capture_id = capture_id
            self._sample_rate = device.default_sample_rate
            self._samples = array("f")
            self._statuses = []
            self._accepting = True
            stream: InputStream | None = None
            try:
                stream = self._backend.create_input_stream(
                    runtime_index=device.runtime_index,
                    sample_rate=device.default_sample_rate,
                    callback=lambda data, frames, status: self._accept_frame(
                        capture_id, data, frames, status
                    ),
                )
                self._stream = stream
                stream.start()
            except Exception as exc:
                self._accepting = False
                self._capture_id = None
                self._stream = None
                if stream is not None:
                    try:
                        stream.close()
                    except Exception as close_exc:
                        raise AudioSessionError(
                            "Capture open and cleanup both failed."
                        ) from close_exc
                raise AudioSessionError("Could not start the selected microphone.") from exc
            return CaptureStart(capture_id, device.default_sample_rate)

    def stop(self) -> CapturedAudio:
        with self._lock:
            stream = self._stream
            if stream is None:
                return CapturedAudio(tuple(self._samples), self._sample_rate, tuple(self._statuses))
            self._accepting = False
            self._closing = True
            self._stream = None
            self._capture_id = None
        error: Exception | None = None
        try:
            stream.stop()
        except Exception as exc:
            error = exc
        finally:
            try:
                stream.close()
            except Exception as exc:
                error = error or exc
            with self._lock:
                self._stream = None
                self._closing = False
        with self._lock:
            captured = CapturedAudio(tuple(self._samples), self._sample_rate, tuple(self._statuses))
        if error is not None:
            raise AudioSessionError("Could not stop the microphone cleanly.") from error
        return captured

    def _accept_frame(self, capture_id: str, data: bytes, frames: int, status: str | None) -> bool:
        with self._lock:
            if not self._accepting or capture_id != self._capture_id:
                return False
            if status:
                self._statuses.append(status)
            values = array("f")
            values.frombytes(data)
            if len(values) != frames:
                self._statuses.append("frame_count_mismatch")
                return False
            remaining = self._sample_rate * self._max_duration_seconds - len(self._samples)
            if remaining <= 0:
                return False
            self._samples.extend(values[:remaining])
            return len(self._samples) < self._sample_rate * self._max_duration_seconds
