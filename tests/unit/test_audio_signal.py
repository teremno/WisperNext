import math

import pytest

from wispernext.audio.signal import (
    AudioCategory,
    CapturedAudio,
    analyze_audio,
    resample_mono,
    validate_audio,
)


def test_metrics_are_computed_from_raw_samples() -> None:
    audio = CapturedAudio((0.0, 0.5, -0.5, 1.0), 4)

    metrics = analyze_audio(audio)

    assert metrics.duration_seconds == 1.0
    assert metrics.rms == pytest.approx(math.sqrt(1.5 / 4))
    assert metrics.peak == 1.0
    assert metrics.clipping_ratio == 0.25
    assert metrics.frame_count == 4


@pytest.mark.parametrize(
    ("audio", "expected"),
    [
        (CapturedAudio((), 16_000), AudioCategory.NO_AUDIO_FRAMES),
        (CapturedAudio((0.1,) * 100, 16_000), AudioCategory.TOO_SHORT),
        (CapturedAudio((0.0001,) * 8_000, 16_000), AudioCategory.WEAK_SIGNAL),
        (CapturedAudio((1.0,) * 8_000, 16_000), AudioCategory.CLIPPED_SIGNAL),
        (CapturedAudio((0.1,) * 8_000, 16_000), AudioCategory.VALID_AUDIO),
    ],
)
def test_validation_categories_remain_distinct(
    audio: CapturedAudio, expected: AudioCategory
) -> None:
    assert validate_audio(audio).category is expected


def test_resampling_does_not_mutate_raw_audio() -> None:
    raw = CapturedAudio((0.0, 1.0, 0.0), 3, ("overflow",))

    processed = resample_mono(raw, 6)

    assert raw.samples == (0.0, 1.0, 0.0)
    assert processed is not raw
    assert processed.sample_rate == 6
    assert len(processed.samples) == 6
    assert processed.callback_statuses == raw.callback_statuses
