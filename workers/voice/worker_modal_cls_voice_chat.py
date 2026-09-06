from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time

import modal
import numpy as np

from workers.voice._shared_voice_chat import (
    MAX_NEW_TOKENS,
    SUPPORTED_LANGUAGES,
    VoiceChatInput,
    _patch_torch_load,
    _rid,
    find_sentence_end,
    pcm_float_to_int16,
    resample_int16,
)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
APP_NAME = "voice-chat-worker"
LLM_REPO = "Qwen/Qwen3-8B"
VOICES_DIR = os.path.join(os.path.dirname(__file__), "voices", "reference_voices")
DEFAULT_VOICE = "GutAI"

app = modal.App(APP_NAME)

# Persistent model cache — models download once, reused across all deploys/containers.
volume = modal.Volume.from_name("model-cache", create_if_missing=True)
MODEL_MOUNT = "/models"


# --------------------------------------------------------------------------
# Image
# --------------------------------------------------------------------------
def _bake_models():
    """Download all models into the image so cold starts are fast (no GPU)."""
    _patch_torch_load()
    from huggingface_hub import snapshot_download

    snapshot_download(LLM_REPO)

    from faster_whisper import WhisperModel

    WhisperModel("small", device="cpu", compute_type="int8")

    from TTS.api import TTS

    TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "torch==2.9.1",
        "torchaudio==2.9.1",
        "transformers==4.57.6",
        "accelerate==1.14.0",
        "bitsandbytes==0.50.2",
        "faster-whisper==1.2.1",
        "coqui-tts==0.27.5",
        "soundfile==0.14.0",
        "numpy==2.5.2",
        "fastapi==0.141.1",
        "uvicorn==0.52.4",
        "hf_transfer==0.1.9",
    )
    .env(
        {
            # Model caches live on the persistent Volume mounted at MODEL_MOUNT.
            "HF_HOME": f"{MODEL_MOUNT}/hf",
            "HF_HUB_CACHE": f"{MODEL_MOUNT}/hf",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "XDG_DATA_HOME": f"{MODEL_MOUNT}/xdg",
            "TORCH_HOME": f"{MODEL_MOUNT}/torch",
            "COQUI_TOS_AGREED": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
    .add_local_dir(VOICES_DIR, "/voices/reference_voices")
    .add_local_python_source("workers.services", "workers.voice")
)


@app.function(
    image=image,
    volumes={MODEL_MOUNT: volume},
    cpu=4,
    memory=8192,
    timeout=3600,
)
def bake_models_to_volume():
    """One-shot: download all models into the persistent Volume (run once)."""
    _bake_models()
    print("All models baked into the 'model-cache' volume.")


@app.local_entrypoint()
def bake():
    """Pre-populate the model-cache Volume. Run: modal run worker_voice_chat.py::bake"""
    bake_models_to_volume.remote()


# --------------------------------------------------------------------------
# Model pipeline (plain class — testable without Modal serving)
# --------------------------------------------------------------------------
class VoiceChatPipeline:
    def __init__(self):
        # Lightweight: no torch models here. Voices are loaded eagerly in
        # @modal.enter() (just a JSON read) so session.created is instant;
        # the heavy LLM/whisper/TTS models load lazily on first use.
        self.voices: dict = {}
        self._models_loaded = False
        self._load_lock = threading.Lock()

    def load_models(self):
        _patch_torch_load()
        import torch
        import torch.distributed as dist

        dist.is_available = lambda: False

        print("[INIT] loading model Qwen/Qwen3-8B + Whisper + XTTS", flush=True)
        t0 = time.time()

        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TextIteratorStreamer,
        )

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )
        self.device = "cuda"
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_REPO)
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_REPO,
            torch_dtype=torch.bfloat16,
            quantization_config=bnb,
            device_map="auto",
        )
        self.model.eval()
        self.streamer_cls = TextIteratorStreamer

        from faster_whisper import WhisperModel

        self.asr = WhisperModel("small", device="cuda", compute_type="float16")

        from TTS.api import TTS

        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

        self.gpu_lock = threading.Lock()
        self._current_persona: str | None = None
        self._models_loaded = True
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    def _ensure_loaded(self):
        if self._models_loaded:
            return
        with self._load_lock:
            if not self._models_loaded:
                self.load_models()

    def _load_voices(self) -> dict:
        # Load reference voices as numpy arrays (resampled to 24 kHz, which XTTS
        # expects) via soundfile + torchaudio.functional. We deliberately avoid
        # torchaudio.load here because torchaudio>=2.9 routes WAV decoding
        # through torchcodec, which is not installed in the image.
        import soundfile as sf
        import torch
        import torchaudio.functional as taF

        with open(os.path.join("/voices/reference_voices", "voices.json")) as fh:
            data = json.load(fh)
        voices = {}
        for vid, meta in data["voices"].items():
            path = os.path.join("/voices/reference_voices", meta["file"])
            audio, sr = sf.read(path, dtype="float32", always_2d=False)
            if sr != 24000:
                audio = taF.resample(torch.from_numpy(audio).float(), sr, 24000).numpy()
            voices[vid] = {
                "file": path,
                "audio": audio,
                "persona": meta.get("persona"),
            }
        return voices

    def _build_inputs(self, persona: str | None, prompt: str):
        messages = []
        if persona:
            messages.append({"role": "system", "content": persona})
        messages.append({"role": "user", "content": prompt})
        try:
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
        except TypeError:
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        return self.tokenizer(text, return_tensors="pt").input_ids.to(self.device)

    def _transcribe(self, audio_int16_24k: np.ndarray) -> str:
        w16 = resample_int16(audio_int16_24k, 24000, 16000)
        # Pass VAD config as a plain dict — `VadParameters` is not exported from
        # the top-level `faster_whisper` package in all versions, and we already
        # run our own server-side VAD before calling this.
        segments, _ = self.asr.transcribe(
            w16, beam_size=5, vad_parameters={"threshold": 0.5}
        )
        return " ".join(s.text.strip() for s in segments).strip()

    def _tts(self, text: str, voice_audio: np.ndarray, language: str) -> bytes:
        with self.gpu_lock:
            wav = self.tts.tts(text=text, speaker_wav=voice_audio, language=language)
        return pcm_float_to_int16(wav)


# --------------------------------------------------------------------------
# OpenAI Realtime API (beta) session handler — transport-agnostic
# --------------------------------------------------------------------------
class RealtimeSession:
    def __init__(self, pipeline: VoiceChatPipeline):
        self.pipeline = pipeline
        self.send = None  # async callable(event_dict); wired by the transport
        self.session = self._default_session()
        self.instructions: str | None = None
        self.voice_id: str = DEFAULT_VOICE
        self.language: str = "en"
        self.input_buffer = bytearray()
        self._vad_16k: np.ndarray | None = None
        # Dependency-free adaptive energy/silence VAD (no external VAD lib).
        self.vad_active = False
        self.vad_silence_samples = 0
        self.vad_noise_floor = 0.01
        self.speech_active = False
        self.response_active = False
        self.interrupted = False
        self._current_response_id: str | None = None
        self._current_item_id: str | None = None
        self._response_task: asyncio.Task | None = None

    # ---- helpers ---------------------------------------------------------
    def _default_session(self) -> dict:
        return {
            "id": _rid("sess"),
            "model": APP_NAME,
            "modalities": ["text", "audio"],
            "instructions": "You are a helpful, concise voice assistant. Respond naturally and briefly.",
            "voice": DEFAULT_VOICE,
            "language": "en",
            "available_voices": [{"id": v, "label": v} for v in self.pipeline.voices],
            "available_languages": [
                {"code": k, "label": lbl} for k, lbl in SUPPORTED_LANGUAGES.items()
            ],
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "whisper-1"},
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "silence_duration_ms": 500,
                "prefix_padding_ms": 200,
            },
            "tools": [],
            "tool_choice": "none",
            "temperature": 0.7,
        }

    def _schedule(self, coro):
        asyncio.get_event_loop().create_task(coro)

    async def _emit(self, event: dict):
        if self.send is not None:
            # The OpenAI Realtime SDK's RealtimeConversation.processEvent()
            # throws "Missing event_id" on EVERY event that lacks one, which
            # silently kills downstream conversation.updated dispatch. Always
            # stamp an event_id.
            event.setdefault("event_id", _rid("evt"))
            print(f"[WS] -> {event.get('type')}  id={event.get('event_id')}", flush=True)
            await self.send(event)

    # ---- lifecycle -------------------------------------------------------
    async def on_connect(self):
        print("[REQ] websocket connected", flush=True)
        await self._emit({"type": "session.created", "session": self.session})
        await self._emit(
            {
                "type": "conversation.created",
                "conversation": {"id": _rid("conv"), "item": [], "model": APP_NAME},
            }
        )

    async def handle_event(self, event: dict):
        try:
            etype = event.get("type")
            print(f"[WS] <- {etype}  keys={list(event.keys())}", flush=True)
            if etype == "session.update":
                self._apply_session(event.get("session", {}))
                await self._emit({"type": "session.updated", "session": self.session})
            elif etype == "input_audio_buffer.append":
                await self._on_audio(event.get("audio", ""))
            elif etype == "input_audio_buffer.commit":
                await self._on_speech_end()
            elif etype == "response.cancel":
                await self._cancel_response()
            # other event types (response.create, conversation.item.truncate, etc.)
            # are ignored; server-VAD drives the flow.
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise

    def _apply_session(self, sess: dict):
        self.session.update({k: v for k, v in sess.items()})
        if "instructions" in sess:
            self.instructions = sess["instructions"]
        if "voice" in sess:
            self.voice_id = sess["voice"]
        if "language" in sess:
            self.language = sess["language"]

    # ---- audio / VAD -----------------------------------------------------
    async def _on_audio(self, b64: str):
        try:
            audio = base64.b64decode(b64)
        except Exception:  # noqa: BLE001
            return
        if not audio:
            return
        self.input_buffer.extend(audio)
        print(f"[VAD] audio chunk: {len(audio)} bytes, buffer: {len(self.input_buffer)}", flush=True)
        self._feed_vad(np.frombuffer(audio, dtype=np.int16))

    def _feed_vad(self, chunk_int16_24k: np.ndarray):
        if len(chunk_int16_24k) == 0:
            return
        w16 = resample_int16(chunk_int16_24k, 24000, 16000)
        self._vad_16k = (
            np.concatenate([self._vad_16k, w16]) if self._vad_16k is not None else w16
        )
        while len(self._vad_16k) >= 512:
            # resample_int16 returns float32 already in [-1, 1]; do NOT
            # re-normalize by 32768 here or the VAD sees (near-)silence.
            frame = self._vad_16k[:512].astype(np.float32)
            self._vad_16k = self._vad_16k[512:]
            rms = float(np.sqrt(np.mean(frame * frame)))
            # Adaptive noise floor (slow tracking while not speaking).
            if not self.vad_active:
                self.vad_noise_floor = max(
                    1e-4, 0.995 * self.vad_noise_floor + 0.005 * rms
                )
            is_speech = rms > self.vad_noise_floor * 3.0
            if is_speech and not self.vad_active:
                self.vad_active = True
                self.vad_silence_samples = 0
                print(f"[VAD] SPEECH START  rms={rms:.4f} floor={self.vad_noise_floor:.4f}", flush=True)
                self._schedule(self._on_speech_start())
            elif is_speech:
                self.vad_silence_samples = 0
            elif self.vad_active:
                self.vad_silence_samples += 512
                if self.vad_silence_samples >= int(16000 * 0.5):  # 500ms silence
                    self.vad_active = False
                    print(f"[VAD] SPEECH END  silence_samples={self.vad_silence_samples}", flush=True)
                    self._schedule(self._on_speech_end())

    async def _on_speech_start(self):
        print(f"[VAD] on_speech_start  response_active={self.response_active}", flush=True)
        await self._emit(
            {"type": "input_audio_buffer.speech_started", "event_id": _rid("evt"), "item_id": _rid("item")}
        )
        if self.response_active:
            await self._cancel_response()

    async def _on_speech_end(self):
        await self._emit(
            {"type": "input_audio_buffer.speech_stopped", "event_id": _rid("evt"), "item_id": _rid("item")}
        )
        audio_24k = np.frombuffer(bytes(self.input_buffer), dtype=np.int16)
        self.input_buffer = bytearray()
        if len(audio_24k) == 0:
            return
        self.pipeline._ensure_loaded()
        transcript = await asyncio.get_event_loop().run_in_executor(
            None, self.pipeline._transcribe, audio_24k
        )
        if not transcript:
            return
        print(f"[STT] transcript: {transcript!r}", flush=True)

        user_item = _rid("item")
        await self._emit(
            {
                "type": "conversation.item.created",
                "item": {
                    "id": user_item,
                    "type": "message",
                    "role": "user",
                    "status": "completed",
                    "content": [{"type": "input_audio", "transcript": transcript}],
                },
            }
        )
        await self._emit(
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "item_id": user_item,
                "content_index": 0,
                "transcript": transcript,
            }
        )

        voice = self.pipeline.voices.get(self.voice_id, self.pipeline.voices[DEFAULT_VOICE])
        voice_audio = voice["audio"]
        persona = self.instructions or voice.get("persona")
        self._response_task = asyncio.create_task(
            self._stream_response(transcript, voice_audio, self.language, persona)
        )

    # ---- response (LLM + TTS) -------------------------------------------
    async def _stream_response(self, transcript: str, voice_file: str, language: str, persona):
        self.pipeline._ensure_loaded()
        self.response_active = True
        self.interrupted = False
        response_id = _rid("resp")
        item_id = _rid("item")
        self._current_response_id = response_id
        self._current_item_id = item_id

        await self._emit(
            {"type": "response.created", "response": {"id": response_id, "status": "in_progress", "output": []}}
        )
        await self._emit(
            {
                "type": "response.output_item.added",
                "response_id": response_id,
                "item": {
                    "id": item_id,
                    "role": "assistant",
                    "content": [{"type": "audio", "transcript": ""}, {"type": "text", "text": ""}],
                },
            }
        )
        # The SDK's RealtimeConversation only creates the item in its itemLookup
        # when it receives `conversation.item.created` — without it, every later
        # delta throws "Item not found" and is silently dropped.
        await self._emit(
            {
                "type": "conversation.item.created",
                "item": {
                    "id": item_id,
                    "type": "message",
                    "role": "assistant",
                    "status": "in_progress",
                    "content": [
                        {"type": "audio", "transcript": ""},
                        {"type": "text", "text": ""},
                    ],
                },
            }
        )

        loop = asyncio.get_event_loop()
        inputs = self.pipeline._build_inputs(persona, transcript)
        streamer = self.pipeline.streamer_cls(
            self.pipeline.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs = {
            "inputs": inputs,
            "max_new_tokens": MAX_NEW_TOKENS,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
            "streamer": streamer,
        }

        q: asyncio.Queue = asyncio.Queue()

        def _generate():
            self.pipeline.model.generate(**gen_kwargs)

        def _drain():
            try:
                for tok in streamer:
                    asyncio.run_coroutine_threadsafe(q.put(tok), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(None), loop)

        threading.Thread(target=_generate, daemon=True).start()
        threading.Thread(target=_drain, daemon=True).start()

        buf = ""
        spoken = ""
        while True:
            tok = await q.get()
            if tok is None or self.interrupted:
                break
            buf += tok
            print(f"[LLM] token: {tok!r}", flush=True)
            await self._emit(
                {"type": "response.text.delta", "response_id": response_id, "item_id": item_id, "content_index": 1, "delta": tok}
            )
            idx = find_sentence_end(buf)
            while idx != -1:
                sentence = buf[:idx].strip()
                buf = buf[idx:].lstrip()
                if sentence and not self.interrupted:
                    pcm = await loop.run_in_executor(None, self.pipeline._tts, sentence, voice_file, language)
                    b64 = base64.b64encode(pcm).decode()
                    print(f"[TTS] sentence: {sentence[:60]!r}  pcm={len(pcm)} bytes", flush=True)
                    await self._emit(
                        {"type": "response.audio.delta", "response_id": response_id, "item_id": item_id, "content_index": 0, "delta": b64}
                    )
                    await self._emit(
                        {
                            "type": "response.audio_transcript.delta",
                            "response_id": response_id,
                            "item_id": item_id,
                            "content_index": 0,
                            "delta": sentence,
                        }
                    )
                    spoken += sentence + " "
                idx = find_sentence_end(buf)

        if buf.strip() and not self.interrupted:
            pcm = await loop.run_in_executor(None, self.pipeline._tts, buf.strip(), voice_file, language)
            b64 = base64.b64encode(pcm).decode()
            await self._emit(
                {"type": "response.audio.delta", "response_id": response_id, "item_id": item_id, "content_index": 0, "delta": b64}
            )
            await self._emit(
                {
                    "type": "response.audio_transcript.delta",
                    "response_id": response_id,
                    "item_id": item_id,
                    "content_index": 0,
                    "delta": buf.strip(),
                }
            )
            spoken += buf.strip()

        await self._emit(
            {
                "type": "response.output_item.done",
                "response_id": response_id,
                "item": {
                    "id": item_id,
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "audio", "transcript": spoken.strip()}, {"type": "text", "text": spoken.strip()}],
                },
            }
        )
        print(f"[RESP] done: response_id={response_id}", flush=True)
        await self._emit(
            {
                "type": "response.done",
                "response": {"id": response_id, "status": "completed", "output": [{"id": item_id, "role": "assistant"}]},
            }
        )
        self.response_active = False

    async def _cancel_response(self):
        self.interrupted = True
        print("[RESP] cancel requested", flush=True)
        response_id = self._current_response_id
        item_id = self._current_item_id
        if self._response_task is not None:
            self._response_task.cancel()
        if response_id:
            await self._emit({"type": "response.cancelled", "response_id": response_id})
        if item_id:
            await self._emit(
                {"type": "conversation.item.truncated", "item_id": item_id, "audio_end_ms": 0}
            )
        await self._emit({"type": "input_audio_buffer.cleared"})
        self.response_active = False


# --------------------------------------------------------------------------
# Modal worker (thin wrapper around the pipeline)
# --------------------------------------------------------------------------
def load_dependencies():
    """Load all dependencies for modal voice worker."""
    # Fast path: build the pipeline and load the voice manifest (JSON read
    # only) so session.created is sent immediately. The heavy LLM/whisper/
    # TTS models load lazily on the first utterance (_ensure_loaded).
    pipeline = VoiceChatPipeline()
    pipeline.voices = pipeline._load_voices()
    return (pipeline,)


def generate(pipeline: VoiceChatPipeline, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract.

    Sync entry point for the realtime session lifecycle: applies a
    `session.update` event to a fresh session and returns the emitted
    `session.updated` event. Audio/utterance turns stay on the realtime
    websocket path (they need the GPU pipeline); session state is pure
    metadata, nothing is written to storage.
    """
    req = VoiceChatInput(**kwargs)
    try:
        session = RealtimeSession(pipeline)
        events: list = []

        async def _send(event: dict) -> None:
            events.append(event)

        session.send = _send
        asyncio.run(session.handle_event({"type": req.type, "session": req.session}))
        for event in events:
            if event.get("type") == "session.updated":
                return event
        raise RuntimeError("no session.updated event emitted")
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@app.cls(
    image=image,
    gpu="L4",
    memory=32768,
    timeout=3600,
    scaledown_window=60,
    max_containers=1,
    volumes={MODEL_MOUNT: volume},
)
class VoiceChatWorker:
    @modal.enter()
    def load(self):
        self.pipeline, = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.pipeline, **kwargs)

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: VoiceChatInput) -> dict:
        return generate(self.pipeline, **item.model_dump())

    @modal.asgi_app()
    def app(self):
        return build_web_app(self.pipeline)


def build_web_app(pipeline: VoiceChatPipeline):
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect

    web = FastAPI()

    @web.websocket("/v1/realtime")
    async def ws_endpoint(websocket: WebSocket):
        # Select the `realtime` subprotocol so clients that request it (the
        # OpenAI Realtime SDK, Node >=22 global WebSocket) don't reject the
        # handshake with "Server sent no subprotocol".
        await websocket.accept(subprotocol="realtime")
        # Optional Bearer auth (Proxy + Bearer strategy)
        auth = websocket.headers.get("authorization", "")
        expected = os.environ.get("WORKER_TOKEN")
        if expected and not auth.endswith(expected):
            await websocket.close(code=1008)
            return

        session = RealtimeSession(pipeline)
        session.send = websocket.send_json
        try:
            await session.on_connect()
            while True:
                raw = await websocket.receive_text()
                try:
                    event = json.loads(raw)
                except Exception:  # noqa: BLE001, S112
                    continue
                await session.handle_event(event)
        except WebSocketDisconnect:
            print("[OK] websocket disconnected", flush=True)

    return web
