import io
import math
import os
import struct
import wave

import httpx

BASE = os.environ["STT_AUDIO_TRANSCRIPTIONS_API_URL"].rstrip("/")
TOKEN = os.environ["GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def wav_fixture(sample_rate=24_000, channels=1, amplitude=12_000):
    frame_count = sample_rate // 4
    samples = [
        int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
        for index in range(frame_count)
    ]
    if channels == 2:
        samples = [sample for value in samples for sample in (value, value)]
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return audio.getvalue()


def main():
    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{BASE}/v1/audio/transcriptions",
            headers=HEADERS,
            files={"file": ("fixture.wav", wav_fixture(), "audio/wav")},
            data={"model": "faster_whisper_large_v3", "response_format": "json"},
        )
        assert response.status_code == 200, "valid audio request failed"
        text = response.json().get("text")
        assert isinstance(text, str) and text.strip(), "empty transcript"
        assert "presigned_url" not in response.json(), "transcript should be returned inline"


if __name__ == "__main__":
    main()
