import base64
import io
import math
import struct
import wave

from dist.contract_tts_audio_speech import Input, Output

SAMPLE_RATE = 24_000


def _tone_wav_base64() -> str:
    frames = int(SAMPLE_RATE * 0.1)
    samples = [
        int(32767 * 0.5 * math.sin(2 * math.pi * 440 * index / SAMPLE_RATE))
        for index in range(frames)
    ]
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return base64.b64encode(buffer.getvalue()).decode("ascii")


TONE_WAV_BASE64 = _tone_wav_base64()


def tts_generator_stub(request: Input) -> Output:
    """Deterministic TTS stub returning non-silent WAV audio."""
    del request
    return Output(audio_base64=TONE_WAV_BASE64, format="wav", sample_rate=SAMPLE_RATE)
