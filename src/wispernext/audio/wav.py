"""Deterministic in-memory encoding for provider-ready mono PCM WAV."""

import io
import sys
import wave
from array import array

from wispernext.audio.signal import CapturedAudio


def encode_pcm16_wav(audio: CapturedAudio) -> bytes:
    """Encode finite mono float samples as little-endian signed 16-bit PCM."""
    if audio.sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    pcm = array("h", (_to_pcm16(sample) for sample in audio.samples))
    if sys.byteorder != "little":
        pcm.byteswap()

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(audio.sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return output.getvalue()


def _to_pcm16(sample: float) -> int:
    if not -1.0 <= sample <= 1.0:
        sample = min(1.0, max(-1.0, sample))
    if sample <= -1.0:
        return -32_768
    return round(sample * 32_767)
