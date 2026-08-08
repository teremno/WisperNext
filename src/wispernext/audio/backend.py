"""Audio backend protocols and the PortAudio/sounddevice adapter."""

from collections.abc import Callable
from typing import Any, Protocol

import sounddevice  # type: ignore[import-untyped]

from wispernext.audio.devices import InputDevice, build_stable_id, infer_connection_kind

FrameCallback = Callable[[bytes, int, str | None], bool]


class InputStream(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class AudioBackend(Protocol):
    def enumerate_input_devices(self) -> tuple[InputDevice, ...]: ...
    def default_input_runtime_index(self) -> int | None: ...

    def create_input_stream(
        self,
        *,
        runtime_index: int,
        sample_rate: int,
        callback: FrameCallback,
    ) -> InputStream: ...


class SoundDeviceBackend:
    """PortAudio adapter that never requests audio-configuration mutation."""

    def enumerate_input_devices(self) -> tuple[InputDevice, ...]:
        """Read metadata only; this method creates zero streams."""
        host_apis: Any = sounddevice.query_hostapis()
        devices: Any = sounddevice.query_devices()
        results: list[InputDevice] = []
        for index, metadata in enumerate(devices):
            channels = int(metadata["max_input_channels"])
            if channels <= 0:
                continue
            name = str(metadata["name"])
            host_api = str(host_apis[int(metadata["hostapi"])]["name"])
            sample_rate = round(float(metadata["default_samplerate"]))
            results.append(
                InputDevice(
                    runtime_index=index,
                    stable_id=build_stable_id(name, host_api, sample_rate, channels),
                    name=name,
                    host_api=host_api,
                    default_sample_rate=sample_rate,
                    max_input_channels=channels,
                    connection_kind=infer_connection_kind(name),
                )
            )
        return tuple(results)

    def default_input_runtime_index(self) -> int | None:
        """Return PortAudio's current default input index without changing it."""
        defaults: Any = sounddevice.default.device
        index = int(defaults[0])
        return index if index >= 0 else None

    def create_input_stream(
        self,
        *,
        runtime_index: int,
        sample_rate: int,
        callback: FrameCallback,
    ) -> InputStream:
        def on_frame(indata: Any, frames: int, _time: Any, status: Any) -> None:
            keep_running = callback(bytes(indata), frames, str(status) if status else None)
            if not keep_running:
                raise sounddevice.CallbackStop

        stream: InputStream = sounddevice.RawInputStream(
            samplerate=sample_rate,
            blocksize=0,
            device=runtime_index,
            channels=1,
            dtype="float32",
            callback=on_frame,
        )
        return stream
