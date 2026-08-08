from array import array

import pytest

from wispernext.audio.backend import FrameCallback
from wispernext.audio.devices import ConnectionKind, InputDevice
from wispernext.audio.session import AudioSessionError, AudioSessionService


class FakeStream:
    def __init__(self, callback: FrameCallback, *, fail_start: bool = False) -> None:
        self.callback = callback
        self.fail_start = fail_start
        self.start_count = 0
        self.stop_count = 0
        self.close_count = 0

    def start(self) -> None:
        self.start_count += 1
        if self.fail_start:
            raise OSError("start failed")

    def stop(self) -> None:
        self.stop_count += 1

    def close(self) -> None:
        self.close_count += 1

    def emit(self, samples: tuple[float, ...], status: str | None = None) -> bool:
        return self.callback(array("f", samples).tobytes(), len(samples), status)


class FakeBackend:
    def __init__(self, *, fail_start: bool = False) -> None:
        self.fail_start = fail_start
        self.create_count = 0
        self.streams: list[FakeStream] = []

    def enumerate_input_devices(self) -> tuple[InputDevice, ...]:
        return ()

    def default_input_runtime_index(self) -> int | None:
        return None

    def create_input_stream(
        self, *, runtime_index: int, sample_rate: int, callback: FrameCallback
    ) -> FakeStream:
        self.create_count += 1
        stream = FakeStream(callback, fail_start=self.fail_start)
        self.streams.append(stream)
        return stream


DEVICE = InputDevice(7, "stable", "Mic", "WASAPI", 10, 1, ConnectionKind.UNKNOWN)


def test_one_start_creates_one_stream_and_stop_closes_exactly_once() -> None:
    backend = FakeBackend()
    service = AudioSessionService(backend, max_duration_seconds=2)

    service.start(DEVICE)
    stream = backend.streams[0]
    assert stream.emit((0.1, 0.2), "overflow")
    captured = service.stop()
    second_stop = service.stop()

    assert backend.create_count == 1
    assert stream.start_count == 1
    assert stream.stop_count == 1
    assert stream.close_count == 1
    assert captured.samples == pytest.approx((0.1, 0.2))
    assert captured.callback_statuses == ("overflow",)
    assert second_stop == captured
    assert not stream.emit((0.9,))


def test_duplicate_start_is_rejected_without_creating_another_stream() -> None:
    backend = FakeBackend()
    service = AudioSessionService(backend)
    service.start(DEVICE)

    with pytest.raises(AudioSessionError):
        service.start(DEVICE)

    assert backend.create_count == 1
    service.stop()


def test_partial_start_failure_closes_stream_and_detaches_owner() -> None:
    backend = FakeBackend(fail_start=True)
    service = AudioSessionService(backend)

    with pytest.raises(AudioSessionError):
        service.start(DEVICE)

    assert backend.streams[0].close_count == 1
    assert service.stop().samples == ()


def test_maximum_duration_bounds_samples_and_stops_callback() -> None:
    backend = FakeBackend()
    service = AudioSessionService(backend, max_duration_seconds=1)
    service.start(DEVICE)
    stream = backend.streams[0]

    keep_running = stream.emit((0.1,) * 12)
    captured = service.stop()

    assert not keep_running
    assert len(captured.samples) == DEVICE.default_sample_rate
