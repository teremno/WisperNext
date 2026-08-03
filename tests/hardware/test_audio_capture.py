"""Opt-in real microphone checks; never run on shared CI."""

import os
import time

import pytest

from wispernext.audio.backend import SoundDeviceBackend
from wispernext.audio.session import AudioSessionService
from wispernext.audio.signal import AudioCategory, validate_audio


@pytest.mark.hardware
def test_explicit_microphone_repeated_capture() -> None:
    stable_id = os.environ.get("WISPER_TEST_MIC_STABLE_ID", "").strip()
    if not stable_id:
        pytest.skip("Set WISPER_TEST_MIC_STABLE_ID after explicit microphone selection.")
    repeats = int(os.environ.get("WISPER_HARDWARE_REPEATS", "1"))
    duration = float(os.environ.get("WISPER_HARDWARE_SECONDS", "1.0"))
    if not 1 <= repeats <= 100 or not 0.5 <= duration <= 5.0:
        pytest.fail("Hardware repeat/duration values are outside safe test bounds.")

    backend = SoundDeviceBackend()
    matches = tuple(
        device for device in backend.enumerate_input_devices() if device.stable_id == stable_id
    )
    if len(matches) != 1:
        pytest.fail("Selected stable microphone identity is missing or ambiguous.")
    device = matches[0]
    service = AudioSessionService(backend, max_duration_seconds=6)

    results = []
    for _ in range(repeats):
        service.start(device)
        time.sleep(duration)
        results.append(validate_audio(service.stop()))

    assert all(result.category is not AudioCategory.NO_AUDIO_FRAMES for result in results)
