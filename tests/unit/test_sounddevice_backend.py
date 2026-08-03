from typing import Any

import pytest

from wispernext.audio.backend import SoundDeviceBackend


def test_enumeration_reads_metadata_and_opens_zero_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream_calls = 0

    def forbidden_stream(**_kwargs: Any) -> None:
        nonlocal stream_calls
        stream_calls += 1

    monkeypatch.setattr(
        "wispernext.audio.backend.sounddevice.query_hostapis",
        lambda: ({"name": "Windows WASAPI"},),
    )
    monkeypatch.setattr(
        "wispernext.audio.backend.sounddevice.query_devices",
        lambda: (
            {
                "name": "USB Mic",
                "hostapi": 0,
                "max_input_channels": 1,
                "default_samplerate": 48_000.0,
            },
            {
                "name": "Speakers",
                "hostapi": 0,
                "max_input_channels": 0,
                "default_samplerate": 48_000.0,
            },
        ),
    )
    monkeypatch.setattr("wispernext.audio.backend.sounddevice.RawInputStream", forbidden_stream)

    devices = SoundDeviceBackend().enumerate_input_devices()

    assert len(devices) == 1
    assert devices[0].runtime_index == 0
    assert devices[0].host_api == "Windows WASAPI"
    assert stream_calls == 0
