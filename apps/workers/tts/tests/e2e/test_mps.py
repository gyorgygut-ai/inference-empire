import base64
import io
import json
import os
import urllib.request
import wave


def main() -> None:
    request = urllib.request.Request(
        f"{os.environ['TTS_AUDIO_SPEECH_API_URL'].rstrip('/')}/v1/audio/speech",
        data=json.dumps(
            {
                "model": "resembleai_chatterbox_tts",
                "input": "This is a local Apple Silicon MPS speech test.",
                "response_format": "wav",
                "voice": "alloy",
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['TTS_AUDIO_SPEECH_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        assert response.status == 200, f"TTS returned HTTP {response.status}"
        output = json.load(response)

    audio = base64.b64decode(output["audio_base64"], validate=True)
    with wave.open(io.BytesIO(audio), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
        assert wav.getframerate() == 24_000, "TTS sample rate was not 24 kHz"
        assert wav.getnchannels() == 1, "TTS output was not mono"
        assert wav.getsampwidth() == 2, "TTS output was not 16-bit PCM"
        assert frames and any(frames), "TTS output was empty or silent"

    print(f"PASS: local MPS TTS returned non-silent 24 kHz mono WAV ({len(audio)} bytes)")


if __name__ == "__main__":
    main()
