import base64
import threading
from types import SimpleNamespace

import pytest

numpy = pytest.importorskip("numpy")
np = numpy

import worker_modal_cls_voice_chat as w  # noqa: E402


class _FakeStreamer:
    def __init__(self, tokens, *args, **kwargs):
        self._tokens = list(tokens)

    def __iter__(self):
        return iter(self._tokens)


TOKENS = ["Hello", ". ", "How", " are", " you", "?"]
DUMMY_PCM = np.ones(20, dtype=np.float32).tobytes()


@pytest.fixture
def pipeline():
    p = w.VoiceChatPipeline()
    p.voices = {"GutAI": {"file": "x.wav", "persona": "You are GutAI."}}
    p.gpu_lock = threading.Lock()
    p.tokenizer = None
    p.vad_model = None
    p.streamer_cls = lambda *a, **k: _FakeStreamer(TOKENS)
    p.model = SimpleNamespace(generate=lambda **k: None)
    p._build_inputs = lambda persona, prompt: None
    p._transcribe = lambda audio: "Hello. How are you"
    p._tts = lambda text, vf, lang: DUMMY_PCM
    return p


def test_ws_realtime_protocol(pipeline):
    from fastapi.testclient import TestClient

    app = w.build_web_app(pipeline)
    client = TestClient(app)

    with client.websocket_connect("/v1/realtime") as ws:
        hello = base64.b64encode(np.ones(480, dtype=np.int16).tobytes()).decode()
        ws.send_json({"type": "session.update", "session": {"voice": "GutAI", "language": "en"}})
        ws.send_json({"type": "input_audio_buffer.append", "audio": hello})
        ws.send_json({"type": "input_audio_buffer.commit"})

        types = []
        for _ in range(50):
            msg = ws.receive_json()
            types.append(msg["type"])
            if msg["type"] == "response.done":
                break

    assert "session.created" in types
    assert "input_audio_buffer.speech_stopped" in types
    assert "conversation.item.input_audio_transcription.completed" in types
    assert types.count("response.audio.delta") == 2
    assert "response.audio_transcript.delta" in types
    assert "response.done" in types
