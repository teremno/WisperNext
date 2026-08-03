"""Pure raw-audio analysis, validation, and resampling."""

import math
from dataclasses import dataclass
from enum import StrEnum


class AudioCategory(StrEnum):
    NO_AUDIO_FRAMES = "no_audio_frames"
    TOO_SHORT = "too_short"
    WEAK_SIGNAL = "weak_signal"
    CLIPPED_SIGNAL = "clipped_signal"
    VALID_AUDIO = "valid_audio"


@dataclass(frozen=True, slots=True)
class CapturedAudio:
    samples: tuple[float, ...]
    sample_rate: int
    callback_statuses: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AudioMetrics:
    duration_seconds: float
    rms: float
    peak: float
    clipping_ratio: float
    frame_count: int


@dataclass(frozen=True, slots=True)
class AudioValidation:
    category: AudioCategory
    metrics: AudioMetrics


def analyze_audio(audio: CapturedAudio) -> AudioMetrics:
    samples = audio.samples
    count = len(samples)
    if count == 0:
        return AudioMetrics(0.0, 0.0, 0.0, 0.0, 0)
    squares = math.fsum(sample * sample for sample in samples)
    peak = max(abs(sample) for sample in samples)
    clipped = sum(abs(sample) >= 0.999 for sample in samples)
    return AudioMetrics(
        duration_seconds=count / audio.sample_rate,
        rms=math.sqrt(squares / count),
        peak=peak,
        clipping_ratio=clipped / count,
        frame_count=count,
    )


def validate_audio(
    audio: CapturedAudio,
    *,
    minimum_duration_seconds: float = 0.25,
    minimum_rms: float = 0.003,
    maximum_clipping_ratio: float = 0.05,
) -> AudioValidation:
    metrics = analyze_audio(audio)
    if metrics.frame_count == 0:
        category = AudioCategory.NO_AUDIO_FRAMES
    elif metrics.duration_seconds < minimum_duration_seconds:
        category = AudioCategory.TOO_SHORT
    elif metrics.rms < minimum_rms:
        category = AudioCategory.WEAK_SIGNAL
    elif metrics.clipping_ratio > maximum_clipping_ratio:
        category = AudioCategory.CLIPPED_SIGNAL
    else:
        category = AudioCategory.VALID_AUDIO
    return AudioValidation(category, metrics)


def resample_mono(audio: CapturedAudio, target_sample_rate: int) -> CapturedAudio:
    """Linearly resample a copy while preserving the immutable raw capture."""
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be positive")
    if target_sample_rate == audio.sample_rate or not audio.samples:
        return CapturedAudio(tuple(audio.samples), target_sample_rate, audio.callback_statuses)
    output_count = max(1, round(len(audio.samples) * target_sample_rate / audio.sample_rate))
    if output_count == 1:
        output: tuple[float, ...] = (audio.samples[0],)
    else:
        scale = (len(audio.samples) - 1) / (output_count - 1)
        values: list[float] = []
        for output_index in range(output_count):
            source_position = output_index * scale
            left = int(source_position)
            right = min(left + 1, len(audio.samples) - 1)
            fraction = source_position - left
            values.append(audio.samples[left] * (1 - fraction) + audio.samples[right] * fraction)
        output = tuple(values)
    return CapturedAudio(output, target_sample_rate, audio.callback_statuses)
