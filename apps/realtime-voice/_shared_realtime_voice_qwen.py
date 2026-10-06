"""Shared business logic for realtime-voice-qwen (FastRTC/WebRTC). No platform imports."""

from __future__ import annotations

import base64
import threading
import time

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

SAMPLE_RATE_IN = 24000
SAMPLE_RATE_OUT = 24000
TTS_SR = 24000
DEFAULT_VOICE = "GutAI"
SUPPORTED_LANGUAGES = {"en": "English", "hu": "Hungarian"}

# Single source of truth for ALL provider image pip deps (beam/modal).
# Worker files must reference this list, never inline their own pins.
# chatterbox-tts rides --no-deps (see CHATTERBOX_TTS_NO_DEPS): its
# numpy<2 / gradio==6.8.0 metadata conflicts with fastrtc (numpy>=2
# relaxed in 0.0.34, gradio<6.0). Its real runtime deps are pinned below.
# Pre-deploy gate (python3.10 image):
# uv run python -c "from apps.realtime_voice._shared_realtime_voice_qwen import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.10 -
IMAGE_PIP_DEPS: list[str] = [
    "fastapi==0.141.1",
    "uvicorn[standard]==0.52.4",
    "numpy==1.26.4",
    "setuptools==84.0.0",
    "soundfile==0.14.0",
    "faster-whisper==1.2.1",
    "ctranslate2==4.4.0",
    "transformers==5.2.0",
    "torch==2.6.0",
    "torchaudio==2.6.0",
    "bitsandbytes==0.50.2",
    "librosa==0.11.0",
    "diffusers==0.29.0",
    "conformer==0.3.2",
    "safetensors==0.5.3",
    "pykakasi==2.3.0",
    "s3tokenizer==0.3.0",
    "resemble-perth==1.0.1",
    "spacy-pkuseg==1.0.1",
    "pyloudnorm==0.2.0",
    "omegaconf==2.3.1",
    "huggingface-hub[hf-transfer]==1.29.0",
    "hf_xet==1.6.0",
    "fastrtc==0.0.34",
]

# Installed --no-deps as a final image layer (beam/modal) after IMAGE_PIP_DEPS.
# Single-sourced here so worker files never inline the pin.
CHATTERBOX_TTS_NO_DEPS = "chatterbox-tts==0.1.7"


class RealtimeVoiceInput(BaseModel):
    model_config = ConfigDict(title="RealtimeVoiceInput")
    audio: str
    sample_rate: int = Field(default=24000)
    voice: str = Field(default="GutAI")
    language: str = Field(default="en")


class RealtimeVoiceOutput(BaseModel):
    model_config = ConfigDict(title="RealtimeVoiceOutput")
    audio: str
    transcript: str
    sample_rate: int = Field(default=24000)


def pcm16_to_float32(pcm16: bytes) -> np.ndarray:
    if not pcm16:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(pcm16, dtype="<i2").astype(np.float32) / 32768.0


def float_to_pcm16(samples: np.ndarray) -> bytes:
    arr = np.asarray(samples, dtype=np.float64)
    clipped = np.clip(arr, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def _resample(samples: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr or len(samples) == 0:
        return samples
    n = round(len(samples) * dst_sr / src_sr)
    if n == 0:
        return np.zeros(0, dtype=samples.dtype)
    x = np.linspace(0, len(samples) - 1, n)
    return np.interp(x, np.arange(len(samples)), samples)


def resample_pcm16(pcm16: bytes, src_sr: int, dst_sr: int) -> bytes:
    if src_sr == dst_sr:
        return pcm16
    samples = np.frombuffer(pcm16, dtype="<i2").astype(np.float64)
    return _resample(samples, src_sr, dst_sr).astype(np.int16).tobytes()


def _patch_torch_dist() -> None:
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    setattr(dist, "is_available", _dist_unavailable)


class WhisperSTT:
    def __init__(self, model_path: str, device: str = "cuda", compute_type: str = "int8") -> None:
        self.model_path = model_path
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.last_language: str | None = None
        self._lock = threading.Lock()

    def load(self) -> WhisperSTT:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            self.model_path, device=self.device, compute_type=self.compute_type
        )
        return self

    def transcribe(self, pcm16_24k: bytes, language: str | None = None) -> str:
        if self.model is None:
            raise RuntimeError("STT not loaded; call load() first")
        pcm16_16k = resample_pcm16(pcm16_24k, 24000, 16000)
        audio = np.frombuffer(pcm16_16k, dtype="<i2").astype(np.float32) / 32768.0
        with self._lock:
            segments, info = self.model.transcribe(audio, language=language, beam_size=5)
            self.last_language = getattr(info, "language", None)
            return "".join(seg.text for seg in segments).strip()


class QwenLLM:
    def __init__(self, model_path: str, device: str = "cuda", max_new_tokens: int = 256) -> None:
        self.model_path = model_path
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.model = None
        self.tokenizer = None
        self._lock = threading.Lock()

    def load(self) -> QwenLLM:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map="auto",
            quantization_config=quant_config,
            torch_dtype=torch.bfloat16,
        )
        return self

    def stream(self, messages: list[dict], cancel=None, max_new_tokens: int | None = None):
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("LLM not loaded; call load() first")
        import threading

        from transformers import TextIteratorStreamer

        max_tokens = max_new_tokens or self.max_new_tokens
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        gen_kwargs: dict = {"inputs": inputs, "streamer": streamer, "max_new_tokens": max_tokens}

        def generate():
            with self._lock:
                self.model.generate(**gen_kwargs)

        t = threading.Thread(target=generate)
        t.start()
        try:
            for token in streamer:
                if cancel is not None and cancel.is_set():
                    break
                yield token
        finally:
            t.join()


class ChatterboxTTS:
    def __init__(
        self, reference_dir: str = "/volumes/models/reference_voices", device: str = "cuda"
    ) -> None:
        self.reference_dir = reference_dir
        self.device = device
        self.model = None
        self._lock = threading.Lock()

    def load(self) -> ChatterboxTTS:
        import importlib

        perth = importlib.import_module("perth")
        if getattr(perth, "PerthImplicitWatermarker", None) is None:
            perth.PerthImplicitWatermarker = perth.DummyWatermarker
        tts_mod = importlib.import_module("chatterbox.tts")
        self.model = tts_mod.ChatterboxTTS.from_pretrained(device=self.device)
        return self

    def _voice_path(self, voice: str) -> str:
        import os

        path = os.path.join(self.reference_dir, f"{voice}.wav")
        if not os.path.exists(path):
            raise KeyError(f"unknown voice: {voice}")
        return path

    def generate(self, text: str, voice: str = "GutAI") -> bytes:
        if self.model is None:
            raise RuntimeError("Chatterbox not loaded; call load() first")
        ref = self._voice_path(voice)
        with self._lock:
            wav = self.model.generate(text, audio_prompt_path=ref)
        arr = np.asarray(wav.squeeze().cpu().numpy(), dtype=np.float32)
        return float_to_pcm16(arr)

    def stream(self, text: str, voice: str = "GutAI", cancel=None, chunk_size: int = 4096):
        pcm = self.generate(text, voice=voice)
        for i in range(0, len(pcm), chunk_size):
            if cancel is not None and cancel.is_set():
                break
            yield pcm[i : i + chunk_size]


def do_inference(models: dict, req: RealtimeVoiceInput) -> RealtimeVoiceOutput:
    """Run one voice turn: STT -> LLM -> TTS. Testable via DI."""
    t_req = time.time()
    print(f"[REQ] voice={req.voice} lang={req.language} sr={req.sample_rate}", flush=True)
    try:
        pcm_in = base64.b64decode(req.audio)
        if req.sample_rate != SAMPLE_RATE_IN:
            pcm_in = resample_pcm16(pcm_in, req.sample_rate, SAMPLE_RATE_IN)
        print("[GEN] stt->llm->tts starting", flush=True)
        text = models["stt"].transcribe(pcm_in)
        if not text.strip():
            raise RuntimeError("empty transcription")
        messages = [
            {
                "role": "system",
                "content": "You are a helpful, concise voice assistant. Keep replies short.",
            },
            {"role": "user", "content": text},
        ]
        parts = list(models["llm"].stream(messages))
        transcript = "".join(parts).strip()
        if not transcript:
            raise RuntimeError("empty llm reply")
        pcm_out = b"".join(models["tts"].stream(transcript, req.voice))
        out = RealtimeVoiceOutput(
            audio=base64.b64encode(pcm_out).decode("ascii"),
            transcript=transcript,
            sample_rate=SAMPLE_RATE_OUT,
        )
        print(f"[OK] turn done in {time.time() - t_req:.1f}s", flush=True)
        return out
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise


def handle_webrtc_audio(
    models: dict, sample_rate: int, audio: np.ndarray, voice: str = "GutAI"
) -> tuple[int, np.ndarray]:
    """FastRTC ReplyOnPause handler: (sr, ndarray) -> (24k, ndarray)."""
    print(f"[REQ] webrtc sr={sample_rate} n={len(audio)}", flush=True)
    try:
        import asyncio

        if asyncio.iscoroutine(audio):
            raise RuntimeError("unexpected coroutine audio")
        arr = np.asarray(audio)
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32)
        arr = np.clip(arr, -1.0, 1.0)
        pcm24 = (
            float_to_pcm16(arr)
            if sample_rate == SAMPLE_RATE_IN
            else float_to_pcm16(_resample(arr, sample_rate, SAMPLE_RATE_IN))
        )
        req = RealtimeVoiceInput(
            audio=base64.b64encode(pcm24).decode("ascii"),
            sample_rate=SAMPLE_RATE_IN,
            voice=voice,
        )
        out = do_inference(models, req)
        reply_pcm = base64.b64decode(out.audio)
        reply_float = pcm16_to_float32(reply_pcm)
        print("[OK] webrtc turn done", flush=True)
        return (SAMPLE_RATE_OUT, reply_float)
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise


def build_app(models: dict, default_voice: str = "GutAI"):
    """Build FastAPI app with contract POST + headless FastRTC WebRTC mount."""
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    def health():
        return {"status": "ok", "voice": default_voice}

    @app.post("/v1/voice:turn")
    def voice_turn(item: RealtimeVoiceInput):
        return do_inference(models, item).model_dump()

    try:
        from fastrtc import ReplyOnPause, Stream

        def _reply(audio):
            sr, arr = audio
            return handle_webrtc_audio(models, sr, arr, default_voice)

        stream = Stream(
            handler=ReplyOnPause(_reply),
            modality="audio",
            mode="send-receive",
        )
        stream.mount(app)
    except Exception as e:
        print(f"[ERR] fastrtc mount skipped: {type(e).__name__}: {e}", flush=True)
    return app


def load_dependencies():
    """Load all dependencies (mocked in unit tests)."""
    _patch_torch_dist()
    return {}
