from __future__ import annotations

import io
import time

import numpy as np
import pytest
import soundfile as sf
from dist.contract_voice import RealtimeSession, RealtimeTurn
from fastapi.testclient import TestClient
from shared import worker_voice


class DeterministicInferenceClient:
    def __init__(self):
        self.calls: list[str] = []

    def transcribe(self, audio: bytes, filename: str) -> str:
        assert audio.startswith(b"RIFF")
        assert filename == "audio.wav"
        self.calls.append("stt")
        return "What time is it?"

    def complete(self, transcript: str) -> str:
        assert transcript == "What time is it?"
        self.calls.append("llm")
        return "It is noon."

    def speak(self, text: str) -> tuple[bytes, int]:
        assert text == "It is noon."
        self.calls.append("tts")
        buffer = io.BytesIO()
        sf.write(buffer, np.full(2400, 0.1, dtype=np.float32), 24_000, format="WAV")
        return buffer.getvalue(), 24_000


def test_generated_session_and_turn_contracts():
    session = RealtimeSession()
    turn = RealtimeTurn(transcript="hello", response="hi")
    assert session.type == "realtime"
    assert turn.response == "hi"
    with pytest.raises(ValueError):
        RealtimeSession.model_validate({"unknown": True})


def test_token_expiry_is_enforced():
    tokens = worker_voice.SessionTokens(ttl_seconds=0)
    token, expires_at = tokens.create()
    assert expires_at <= int(time.time()) + 1
    assert not tokens.validate(token)


def test_model_free_pause_detector_distinguishes_speech_from_silence():
    detector = worker_voice.EnergyPauseDetector()
    speech = np.full(14_400, 0.1, dtype=np.float32)
    silence = np.zeros_like(speech)
    assert detector.vad((24_000, speech), None)[0] == pytest.approx(0.6)
    assert detector.vad((24_000, silence), None)[0] == 0.0
    assert detector.warmup() is None


def test_invalid_token_cannot_negotiate_a_call():
    app = worker_voice.build_app(inference_client=DeterministicInferenceClient())
    with TestClient(app) as client:
        response = client.post(
            "/v1/realtime/calls",
            headers={"Authorization": "Bearer invalid"},
            data={"sdp": "offer", "session": "{}"},
        )
    assert response.status_code == 401


def test_trusted_server_receives_ephemeral_client_secret():
    app = worker_voice.build_app(inference_client=DeterministicInferenceClient())
    with TestClient(app) as client:
        response = client.post(
            "/v1/realtime/client_secrets",
            json={"session": {"type": "realtime", "instructions": "Be brief."}},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["value"] and body["expires_at"] > int(time.time())
    assert body["session"]["instructions"] == "Be brief."


def test_turn_calls_stt_then_llm_then_tts_without_local_models():
    client = DeterministicInferenceClient()
    transcript, reply, audio = worker_voice.run_turn(
        np.full(2400, 0.1, dtype=np.float32), 24_000, client
    )
    assert (transcript, reply, client.calls) == (
        "What time is it?",
        "It is noon.",
        ["stt", "llm", "tts"],
    )
    assert audio.size > 0 and np.max(np.abs(audio)) > 0.001
    assert not hasattr(worker_voice, "load_models")
