import asyncio
import base64
import threading
from types import SimpleNamespace

import numpy as np
import pytest

import worker_modal_cls_voice_chat as w


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------
def test_find_sentence_end_basic():
    assert w.find_sentence_end("Hello. How are you") == 6
    assert w.find_sentence_end("Hi there") == -1
    assert w.find_sentence_end("Done!") == 5
    assert w.find_sentence_end("A? B. C!") == 8


def test_pcm_float_to_int16():
    out = w.pcm_float_to_int16(np.array([0.0, 1.0, -1.0], dtype=np.float32))
    assert isinstance(out, bytes)
    assert np.frombuffer(out, dtype=np.int16).tolist() == [0, 32767, -32767]


def test_module_exports():
    assert w.app is not None
    assert w.image is not None
    assert w.VoiceChatWorker is not None
    assert w.RealtimeSession is not None
    assert w.VoiceChatPipeline is not None


# --------------------------------------------------------------------------
# RealtimeSession with fully mocked models (no GPU / network)
# --------------------------------------------------------------------------
class _FakeStreamer:
    def __init__(self, tokens, *args, **kwargs):
        self._tokens = list(tokens)

    def __iter__(self):
        return iter(self._tokens)


TOKENS = ["Hello", ". ", "How", " are", " you", "?"]
DUMMY_PCM = np.ones(20, dtype=np.float32).tobytes()


def _make_session():
    p = w.VoiceChatPipeline()
    p.voices = {"GutAI": {"file": "x.wav", "persona": "You are GutAI."}}
    p.gpu_lock = threading.Lock()
    p.tokenizer = None
    p.vad_model = None  # skip real VAD in tests
    p.streamer_cls = lambda *a, **k: _FakeStreamer(TOKENS)
    p.model = SimpleNamespace(generate=lambda **k: None)
    p._build_inputs = lambda persona, prompt: None
    p._transcribe = lambda audio: "Hello. How are you"
    p._tts = lambda text, vf, lang: DUMMY_PCM

    session = w.RealtimeSession(p)
    sent = []
    async def collect(ev):
        sent.append(ev)
    session.send = collect
    return session, sent


@pytest.fixture
def session():
    return _make_session()


def test_session_created_has_server_vad(session):
    s, sent = session
    asyncio.run(s.on_connect())
    types = [e["type"] for e in sent]
    assert "session.created" in types
    created = next(e for e in sent if e["type"] == "session.created")
    assert created["session"]["turn_detection"]["type"] == "server_vad"
    assert created["session"]["modalities"] == ["text", "audio"]
    assert created["session"]["output_audio_format"] == "pcm16"


def test_full_utterance_event_sequence(session):
    s, sent = session
    asyncio.run(s.on_connect())

    async def run():
        await s.handle_event(
            {"type": "session.update", "session": {"instructions": "be brief", "voice": "GutAI", "language": "en"}}
        )
        # fill input buffer with dummy 24k PCM and force speech end
        s.input_buffer.extend(np.ones(480, dtype=np.int16).tobytes())
        await s._on_speech_end()
        if s._response_task is not None:
            await s._response_task

    asyncio.run(run())

    types = [e["type"] for e in sent]
    assert "session.updated" in types
    assert "input_audio_buffer.speech_stopped" in types
    assert "conversation.item.created" in types
    assert "conversation.item.input_audio_transcription.completed" in types
    assert "response.created" in types
    assert "response.output_item.added" in types
    assert types.count("response.audio.delta") == 2  # "Hello." + "How are you?"
    assert "response.text.delta" in types
    assert "response.audio_transcript.delta" in types
    assert "response.output_item.done" in types
    assert "response.done" in types

    # transcript wiring
    tr = next(e for e in sent if e["type"] == "conversation.item.input_audio_transcription.completed")
    assert tr["transcript"] == "Hello. How are you"


def test_barge_in_cancels_response(session):
    s, sent = session

    async def run():
        await s.on_connect()
        # Simulate an in-flight assistant response that gets interrupted.
        s.response_active = True
        s._current_response_id = "resp_x"
        s._current_item_id = "item_x"
        s._response_task = asyncio.create_task(asyncio.sleep(10))
        await s._on_speech_start()  # user interrupts -> barge-in
        if s._response_task is not None:
            s._response_task.cancel()
            try:
                await s._response_task
            except asyncio.CancelledError:
                pass

    asyncio.run(run())

    types = [e["type"] for e in sent]
    assert "response.cancelled" in types
    assert "conversation.item.truncated" in types
    assert "input_audio_buffer.cleared" in types
    assert "input_audio_buffer.speech_started" in types
    assert s.interrupted is True
