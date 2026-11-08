import base64
import io
import os
import struct
import wave

import httpx

BASE = os.environ["TTS_AUDIO_SPEECH_API_URL"].rstrip("/")
TOKEN = os.environ["TTS_AUDIO_SPEECH_API_KEY"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def main():
    with httpx.Client(timeout=120) as client:
        response = client.post(
            f"{BASE}/v1/audio/speech",
            headers=HEADERS,
            json={"model": "resembleai_chatterbox_tts", "input": "Say hello.", "response_format": "wav"},
        )
        assert response.status_code == 200, "valid speech request failed"
        payload = response.json()
        assert payload.get("format") == "wav", "response format is not WAV"
        assert "presigned_url" not in payload, "audio should be returned inline"
        audio = base64.b64decode(payload["audio_base64"], validate=True)
        with wave.open(io.BytesIO(audio), "rb") as wav:
            assert wav.getframerate() == 24_000, "wrong sample rate"
            assert wav.getnchannels() == 1, "audio is not mono"
            samples = wav.readframes(wav.getnframes())
        decoded = struct.unpack(f"<{len(samples) // 2}h", samples)
        assert decoded and max(abs(sample) for sample in decoded) > 32, "audio is silent"


if __name__ == "__main__":
    main()
