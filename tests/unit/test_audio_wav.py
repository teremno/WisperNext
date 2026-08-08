import io
import wave

from wispernext.audio.signal import CapturedAudio
from wispernext.audio.wav import encode_pcm16_wav


def test_pcm16_wav_is_mono_in_memory_and_clamps_samples() -> None:
    encoded = encode_pcm16_wav(CapturedAudio((-2.0, -1.0, 0.0, 1.0, 2.0), 16_000))

    with wave.open(io.BytesIO(encoded), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16_000
        assert wav_file.getnframes() == 5
        frames = wav_file.readframes(5)

    assert int.from_bytes(frames[:2], "little", signed=True) == -32_768
    assert int.from_bytes(frames[-2:], "little", signed=True) == 32_767
