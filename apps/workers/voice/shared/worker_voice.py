"""Lazy-loaded Qwen voice-turn pipeline and FastRTC app."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = Path(os.getenv("HF_HOME", "./hf-cache"))
REFERENCE_ROOT = CACHE_ROOT / "reference_voices"
VOICE_MANIFEST = REFERENCE_ROOT / "voices.json"
MODEL_CACHES = {
    "qwen2_5_3b_instruct": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct",
        "path": "./model-cache/qwen2_5_3b_instruct",
    },
    "faster_whisper_large_v3": {
        "url": "https://huggingface.co/Systran/faster-whisper-large-v3",
        "path": "./model-cache/faster_whisper_large_v3",
    },
    "resembleai_chatterbox_tts": {
        "url": "https://huggingface.co/ResembleAI/chatterbox",
        "path": "./model-cache/resembleai_chatterbox_tts",
    },
}
QWEN_CACHE_NAME = "qwen2_5_3b_instruct"
WHISPER_CACHE_NAME = "faster_whisper_large_v3"
CHATTERBOX_CACHE_NAME = "resembleai_chatterbox_tts"
QWEN_MODEL = urlparse(MODEL_CACHES[QWEN_CACHE_NAME]["url"]).path.strip("/")
WHISPER_MODEL = urlparse(MODEL_CACHES[WHISPER_CACHE_NAME]["url"]).path.strip("/")
CHATTERBOX_MODEL = urlparse(MODEL_CACHES[CHATTERBOX_CACHE_NAME]["url"]).path.strip("/")
QWEN_CACHE_PATH = MODEL_CACHES[QWEN_CACHE_NAME]["path"]
WHISPER_CACHE_PATH = MODEL_CACHES[WHISPER_CACHE_NAME]["path"]
CHATTERBOX_CACHE_PATH = MODEL_CACHES[CHATTERBOX_CACHE_NAME]["path"]
SAMPLE_RATE = 24_000
VOICE_LOCK = threading.RLock()
MODELS: dict[str, Any] | None = None
logger = logging.getLogger(__name__)

IMAGE_PIP_DEPS = [
    "aiortc==1.15.0", "av==17.1.0", "fastapi==0.141.1", "fastrtc[vad]==0.0.34",
    "faster-whisper==1.2.1", "httpx==0.28.1", "numpy==2.4.3", "soundfile==0.14.0",
    "torch==2.6.0", "torchaudio==2.6.0", "transformers==5.2.0", "uvicorn[standard]==0.52.4",
    "huggingface-hub[hf-transfer]==1.29.0", "hf_xet==1.6.0", "bitsandbytes==0.50.2",
    "librosa==0.11.0", "diffusers==0.29.0", "conformer==0.3.2", "safetensors==0.5.3",
    "pykakasi==2.3.0", "s3tokenizer==0.3.0", "resemble-perth==1.0.1",
    "spacy-pkuseg==1.0.1", "pyloudnorm==0.2.0", "omegaconf==2.3.1",
]
CHATTERBOX_TTS_NO_DEPS = "chatterbox-tts==0.1.7"


def model_volumes():
    from beam import Volume

    return [
        Volume(name=f"model-cache-{name}", mount_path=model["path"])
        for name, model in MODEL_CACHES.items()
    ]


def download_models() -> dict[str, Path]:
    """Download declared models into their mounted cache paths."""
    from huggingface_hub import snapshot_download

    return {
        name: Path(
            snapshot_download(
                repo_id=urlparse(model["url"]).path.strip("/"),
                cache_dir=model["path"],
            )
        )
        for name, model in MODEL_CACHES.items()
    }


def available_reference_voices() -> dict[str, Path]:
    """Return valid mounted WAVs keyed by configured voice name."""
    voices: dict[str, Path] = {}
    if not REFERENCE_ROOT.is_dir():
        return voices
    if VOICE_MANIFEST.is_file():
        entries = json.loads(VOICE_MANIFEST.read_text(encoding="utf-8"))
    else:
        entries = [{"name": path.stem, "path": path.name} for path in REFERENCE_ROOT.glob("*.wav")]
    for entry in entries:
        name = entry.get("name")
        filename = entry.get("path")
        if not isinstance(name, str) or not isinstance(filename, str) or Path(filename).name != filename:
            continue
        path = REFERENCE_ROOT / filename
        if path.is_file() and path.suffix.casefold() == ".wav" and path.stat().st_size:
            voices[name] = path
    return voices


def resolve_voice(voice_id: str | None) -> tuple[str, Path | None]:
    """Select a mounted reference WAV by name, or safely fall back to builtin."""
    if not voice_id or voice_id.casefold() == "builtin":
        return "builtin", None
    for name, path in available_reference_voices().items():
        if name.casefold() == voice_id.casefold():
            return name, path
    return "builtin", None


def voice_persona(voice_id: str) -> str:
    if VOICE_MANIFEST.is_file():
        entries = json.loads(VOICE_MANIFEST.read_text(encoding="utf-8"))
        for entry in entries:
            if entry.get("name", "").casefold() == voice_id.casefold():
                return entry.get("prompt", "You are a concise, helpful voice assistant.")
    return "You are a concise, helpful voice assistant."


def load_models() -> dict[str, Any]:
    """Download/load inference models on first actual turn, then reuse the cache."""
    global MODELS
    with VOICE_LOCK:
        if MODELS is not None:
            return MODELS
        logger.info("loading cached voice inference models")
        import torch
        from faster_whisper import WhisperModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        cuda = torch.cuda.is_available()
        mps = getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
        device = "cuda" if cuda else "mps" if mps else "cpu"
        import hf_xet  # noqa: F401

        model_dirs = download_models()
        whisper_dir = model_dirs[WHISPER_CACHE_NAME]
        qwen_dir = model_dirs[QWEN_CACHE_NAME]
        whisper = WhisperModel(
            str(whisper_dir), device="cuda" if cuda else "cpu",
            compute_type="float16" if cuda else "int8",
        )
        tokenizer = AutoTokenizer.from_pretrained(str(qwen_dir))
        qwen_options: dict[str, Any] = {"device_map": "auto", "torch_dtype": torch.float32}
        if cuda:
            qwen_options["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16
            )
            qwen_options["torch_dtype"] = torch.bfloat16
        qwen = AutoModelForCausalLM.from_pretrained(str(qwen_dir), **qwen_options)
        import importlib

        hub_constants = importlib.import_module("huggingface_hub.constants")
        chatterbox_cache_dir = hub_constants.HF_HUB_CACHE
        hub_constants.HF_HUB_CACHE = CHATTERBOX_CACHE_PATH
        perth = importlib.import_module("perth")
        if getattr(perth, "PerthImplicitWatermarker", None) is None:
            setattr(perth, "PerthImplicitWatermarker", perth.DummyWatermarker)
        chatterbox_module = importlib.import_module("chatterbox.tts")
        if chatterbox_module.REPO_ID != CHATTERBOX_MODEL:
            raise RuntimeError("Chatterbox package repo differs from the declared model cache")
        try:
            chatterbox = chatterbox_module.ChatterboxTTS.from_pretrained(device=device)
        finally:
            hub_constants.HF_HUB_CACHE = chatterbox_cache_dir
        MODELS = {
            "whisper": whisper, "tokenizer": tokenizer, "qwen": qwen,
            "chatterbox": chatterbox,
        }
        logger.info("voice inference models loaded on %s", device)
        return MODELS


def _resample(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    values = np.asarray(audio, dtype=np.float32).reshape(-1)
    if source_rate == target_rate:
        return values
    count = round(len(values) * target_rate / source_rate)
    return np.interp(
        np.linspace(0, max(len(values) - 1, 0), count), np.arange(len(values)), values,
    ).astype(np.float32)


def _normalize_audio(audio: np.ndarray) -> np.ndarray:
    samples = np.asarray(audio).reshape(-1)
    if np.issubdtype(samples.dtype, np.integer):
        return samples.astype(np.float32) / 32768.0
    return samples.astype(np.float32)


def run_turn(
    audio: np.ndarray, sample_rate: int, voice_id: str | None, language: str = "en"
) -> tuple[str, str, np.ndarray]:
    audio = _normalize_audio(audio)
    if audio.size == 0 or not np.isfinite(audio).all() or float(np.max(np.abs(audio))) < 0.005:
        raise ValueError("speech input is empty or silent")
    voice_id, voice_path = resolve_voice(voice_id)
    models = load_models()
    audio_24k = _resample(audio, sample_rate, SAMPLE_RATE)
    with VOICE_LOCK:
        segments, _ = models["whisper"].transcribe(audio_24k, language=language, beam_size=5)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        if not transcript:
            raise ValueError("Whisper returned an empty transcript")
        tokenizer = models["tokenizer"]
        persona = voice_persona(voice_id)
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": persona},
             {"role": "user", "content": transcript}],
            tokenize=False, add_generation_prompt=True,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(models["qwen"].device)
        generated = models["qwen"].generate(**inputs, max_new_tokens=128, do_sample=True,
                                             temperature=0.7)
        reply = tokenizer.decode(generated[0][inputs.input_ids.shape[-1]:],
                                 skip_special_tokens=True).strip()
        if not reply:
            raise ValueError("Qwen returned an empty response")
        speech = (
            models["chatterbox"].generate(reply)
            if voice_path is None
            else models["chatterbox"].generate(reply, audio_prompt_path=str(voice_path))
        )
    output = np.asarray(speech.squeeze().detach().cpu(), dtype=np.float32).reshape(-1)
    output = _resample(output, int(getattr(models["chatterbox"], "sr", SAMPLE_RATE)), SAMPLE_RATE)
    if output.size == 0 or float(np.max(np.abs(output))) < 0.001:
        raise ValueError("Chatterbox returned silent audio")
    return transcript, reply, output


def build_app():
    from fastapi import FastAPI
    from fastrtc import ReplyOnPause, Stream

    app = FastAPI(title="workers-voice")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    default_voice = "builtin"

    def on_turn(audio: tuple[int, np.ndarray]):
        rate, samples = audio
        logger.info("speech turn started voice=%s sample_rate=%s", default_voice, rate)
        try:
            transcript, reply, response = run_turn(np.asarray(samples), rate, default_voice)
        except Exception:
            logger.exception("speech turn failed voice=%s", default_voice)
            raise
        logger.info(
            "speech turn completed voice=%s transcript_chars=%d response_chars=%d",
            default_voice, len(transcript), len(reply),
        )
        yield SAMPLE_RATE, response

    rtc_configuration = _rtc_configuration()
    app.state.rtc_configuration = rtc_configuration
    Stream(
        handler=ReplyOnPause(on_turn), modality="audio", mode="send-receive",
        rtc_configuration=rtc_configuration,
        server_rtc_configuration=rtc_configuration,
    ).mount(app)

    @app.get("/v1/voice-assets")
    def voice_assets() -> dict[str, dict[str, str]]:
        assets = {"builtin": {"sha256": "builtin", "loaded": "builtin"}}
        for voice_id, path in available_reference_voices().items():
            assets[voice_id] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "loaded": str(path),
            }
        return assets

    @app.get("/v1/rtc-configuration")
    def rtc_configuration_endpoint() -> dict:
        return app.state.rtc_configuration

    return app


def _rtc_configuration():
    """Use FastRTC's documented TURN relay credentials for restrictive networks."""
    import httpx
    servers = [{"urls": ["stun:stun.l.google.com:19302"]}]
    token = os.getenv("HF_TOKEN")
    if token:
        response = httpx.get(
            "https://fastrtc-turn-service.hf.space/credentials",
            headers={"Authorization": f"Bearer {token}"}, timeout=20,
        )
        response.raise_for_status()
        servers.extend(response.json().get("iceServers", []))
    return {"iceServers": servers}
