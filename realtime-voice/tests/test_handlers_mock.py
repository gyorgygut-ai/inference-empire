"""Mocked unit tests for the model handlers (no GPU / no real models).

These exercise the *plumbing* of each handler — resampling, message building,
token/cancel handling, and PCM16 encoding — using ``unittest.mock`` fakes for
``.model`` / ``.tokenizer``. They run in the lightweight ``verify`` venv
(ruff + pytest + numpy only) without pulling in torch/transformers.
"""

from __future__ import annotations

import sys
import threading
import types
import unittest
from unittest.mock import MagicMock

import numpy as np

from handlers.llm import QwenLLM
from handlers.stt import WhisperSTT

try:
    from handlers.tts import QwenTTS
except ImportError:
    QwenTTS = None  # faster-qwen3-tts not installed (dropped from the image)


class _FakeStreamer:
    def __init__(self, tokens):
        self._tokens = tokens

    def __iter__(self):
        return iter(self._tokens)


class TestSTT(unittest.TestCase):
    def test_transcribe_resamples_and_joins_segments(self):
        stt = WhisperSTT(model_path="/tmp/fake", device="cpu")
        stt.model = MagicMock()
        stt.model.transcribe.return_value = (
            [MagicMock(text=" hello "), MagicMock(text="world")],
            None,
        )

        out = stt.transcribe(b"\x00\x01" * 1000, language="en")

        # segments joined + stripped
        self.assertEqual(out, "hello world")
        # transcribed on 16k float audio derived from the 24k input
        args, kwargs = stt.model.transcribe.call_args
        audio = args[0]
        self.assertIsInstance(audio, np.ndarray)
        self.assertEqual(audio.dtype, np.float32)
        self.assertEqual(kwargs["language"], "en")


class TestLLM(unittest.TestCase):
    def _make_llm(self, tokens):
        llm = QwenLLM(model_path="/tmp/fake", device="cpu")
        llm.tokenizer = MagicMock()
        llm.tokenizer.apply_chat_template.return_value = MagicMock()
        llm.tokenizer.apply_chat_template.return_value.to.return_value = "INPUTS"
        llm.model = MagicMock()
        llm.model.device = "cpu"
        return llm, tokens

    def _with_fake_transformers(self, tokens):
        """Inject a stub `transformers` module so `from transformers import
        TextIteratorStreamer` resolves without the real (heavy) package."""
        fake = types.ModuleType("transformers")

        def streamer_cls(*a, **k):
            return _FakeStreamer(tokens)

        fake.TextIteratorStreamer = streamer_cls
        prev = sys.modules.get("transformers")
        sys.modules["transformers"] = fake
        self.addCleanup(lambda: sys.modules.__setitem__("transformers", prev) if prev else sys.modules.pop("transformers", None))

    def test_stream_yields_tokens(self):
        llm, tokens = self._make_llm(["Hello", " world"])
        self._with_fake_transformers(tokens)
        messages = [{"role": "user", "content": "hi"}]
        out = list(llm.stream(messages))
        self.assertEqual(out, ["Hello", " world"])
        # generation invoked with the chat-template inputs + streamer
        llm.model.generate.assert_called_once()
        gen_kwargs = llm.model.generate.call_args.kwargs
        self.assertEqual(gen_kwargs["inputs"], "INPUTS")
        self.assertIn("streamer", gen_kwargs)

    def test_stream_honors_cancel(self):
        llm, tokens = self._make_llm(["a", "b", "c"])
        self._with_fake_transformers(tokens)
        cancel = threading.Event()
        cancel.set()  # already cancelled before streaming
        out = list(llm.stream([{"role": "user", "content": "hi"}], cancel=cancel))
        # cancel is checked before each yield -> nothing emitted
        self.assertEqual(out, [])


@unittest.skipIf(QwenTTS is None, "faster-qwen3-tts not installed (dropped from image)")
class TestTTS(unittest.TestCase):
    def _make_tts(self, chunks, sr=24000):
        tts = QwenTTS(model_path="/tmp/fake", device="cpu")
        tts.model = MagicMock()

        def gen(*a, **k):
            for c in chunks:
                yield np.asarray(c, dtype=np.float32), sr, None

        tts.model.generate_custom_voice_streaming.side_effect = gen
        return tts

    def test_stream_yields_pcm16_bytes(self):
        chunks = [np.full(100, 0.5, dtype=np.float32), np.full(50, -0.5, dtype=np.float32)]
        tts = self._make_tts(chunks, sr=24000)
        out = list(tts.stream("hello", cancel=None))
        self.assertEqual(len(out), 2)
        for chunk in out:
            self.assertIsInstance(chunk, bytes)
            self.assertEqual(len(chunk) % 2, 0)  # 16-bit = 2 bytes/sample

    def test_stream_resamples_to_target_sr(self):
        # 48k input should be resampled down to 24k before encoding
        chunks = [np.ones(480, dtype=np.float32)]
        tts = self._make_tts(chunks, sr=48000)
        out = list(tts.stream("hello", cancel=None))
        # 480 samples @48k -> 240 samples @24k -> 480 bytes PCM16
        self.assertEqual(len(out[0]), 240 * 2)

    def test_stream_honors_cancel(self):
        chunks = [np.ones(10, dtype=np.float32)] * 5
        tts = self._make_tts(chunks, sr=24000)
        cancel = threading.Event()
        cancel.set()
        out = list(tts.stream("hello", cancel=cancel))
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
