from __future__ import annotations

import io
import socket
import threading
import time

import httpx
import numpy as np
import soundfile as sf
import uvicorn
from shared.worker_voice_tts_audio_speech import build_app, encode_audio


def test_local_speech_request_returns_non_silent_wav():
    def local_tts(_request):
        samples = np.sin(np.linspace(0, 80, 9600, dtype=np.float32)) * 0.25
        return encode_audio(samples, 24_000)

    with socket.socket() as available_port:
        available_port.bind(("127.0.0.1", 0))
        port = available_port.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            build_app(generator=local_tts),
            host="127.0.0.1",
            port=port,
            log_level="error",
            access_log=False,
        )
    )
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        with httpx.Client(timeout=5) as client:
            ready_deadline = time.monotonic() + 15
            while True:
                try:
                    health = client.get(f"{base_url}/health")
                    break
                except httpx.ConnectError:
                    if time.monotonic() >= ready_deadline:
                        raise TimeoutError("local TTS service did not become ready")
                    time.sleep(0.1)
            response = client.post(
                f"{base_url}/v1/audio/speech",
                json={"model": "local-deterministic-tts", "input": "Say hello."},
            )
        samples, sample_rate = sf.read(io.BytesIO(response.content), dtype="float32")

        assert health.status_code == 200
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert sample_rate == 24_000
        assert samples.size > 0
        assert np.isfinite(samples).all()
        assert float(np.max(np.abs(samples))) >= 0.001
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)
