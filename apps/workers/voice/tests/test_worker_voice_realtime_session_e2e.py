from __future__ import annotations

import asyncio
import io
import socket
import threading
import time
from fractions import Fraction
from pathlib import Path

import av
import httpx
import numpy as np
import soundfile as sf
import uvicorn
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import Response as FastAPIResponse
from shared.inference_client import InferenceClient, InferenceEndpoint
from shared.worker_voice import build_app

RATE = 48_000
FRAME = 960


class AudioFixtureTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, samples: np.ndarray):
        super().__init__()
        self.samples = samples
        self.offset = 0
        self.pts = 0
        self.started = time.monotonic()

    async def recv(self) -> av.AudioFrame:
        frame_samples = np.zeros(FRAME, dtype=np.int16)
        count = min(FRAME, len(self.samples) - self.offset)
        if count > 0:
            frame_samples[:count] = self.samples[self.offset : self.offset + count]
            self.offset += count
        delay = self.started + (self.pts + FRAME) / RATE - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        frame = av.AudioFrame(format="s16", layout="mono", samples=FRAME)
        frame.planes[0].update(frame_samples.tobytes())
        frame.sample_rate = RATE
        frame.pts = self.pts
        frame.time_base = Fraction(1, RATE)
        self.pts += FRAME
        return frame


class LocalServer:
    def __init__(self, app: FastAPI):
        self.server = None
        self.thread = None
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.app = app

    def __enter__(self):
        server = uvicorn.Server(
            uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="error")
        )
        self.server = server
        self.thread = threading.Thread(target=server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise TimeoutError("Local inference endpoint did not start")
        return f"http://127.0.0.1:{self.port}"

    def __exit__(self, *_):
        server = self.server
        thread = self.thread
        if server is None or thread is None:
            raise RuntimeError("Local inference endpoint was not started")
        server.should_exit = True
        thread.join(timeout=5)
        if thread.is_alive():
            raise TimeoutError("Local inference endpoint did not stop")


def build_inference_app(calls: list[str]) -> FastAPI:
    app = FastAPI()

    @app.post("/v1/audio/transcriptions")
    async def transcribe(request: Request, file: UploadFile = File(...)):
        assert request.headers.get("authorization") == "Bearer local-stt"
        assert file.filename == "audio.wav"
        assert (await file.read()).startswith(b"RIFF")
        assert file.headers.get("content-type") == "audio/wav"
        calls.append("stt")
        return {"text": "Tell me something useful."}

    @app.post("/v1/chat/completions")
    async def complete(request: dict, http_request: Request):
        assert http_request.headers.get("authorization") == "Bearer local-llm"
        assert request["messages"][-1]["content"] == "Tell me something useful."
        calls.append("llm")
        return {"choices": [{"message": {"content": "A complete local turn."}}]}

    @app.post("/v1/audio/speech")
    async def speak(request: dict, http_request: Request):
        assert http_request.headers.get("authorization") == "Bearer local-tts"
        assert request["input"] == "A complete local turn."
        calls.append("tts")
        buffer = io.BytesIO()
        sf.write(buffer, np.full(4800, 0.15, dtype=np.float32), 24_000, format="WAV")
        return FastAPIResponse(buffer.getvalue(), media_type="audio/wav")

    return app


def test_webrtc_turn_uses_local_stt_llm_tts_services():
    service_calls: list[str] = []
    source = Path(__file__).parents[1] / "references" / "gut.wav"
    samples, source_rate = sf.read(source, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = samples[: source_rate * 6]
    samples = np.interp(
        np.linspace(0, len(samples) - 1, round(len(samples) * RATE / source_rate)),
        np.arange(len(samples)),
        samples,
    )
    samples = np.clip(samples * 32767, -32768, 32767).astype(np.int16)

    with LocalServer(build_inference_app(service_calls)) as inference_url:
        inference = InferenceClient(
            stt=InferenceEndpoint(inference_url, "local-stt"),
            llm=InferenceEndpoint(inference_url, "local-llm"),
            tts=InferenceEndpoint(inference_url, "local-tts"),
            timeout=10,
        )
        realtime_app = build_app(
            inference_client=inference, client_secret_auth_token="local-server-token"
        )
        with LocalServer(realtime_app) as realtime_url:
            asyncio.run(
                _run_turn(realtime_url, samples, service_calls, realtime_app.state.pause_detector)
            )

    assert service_calls == ["stt", "llm", "tts"]


async def _run_turn(
    realtime_url: str,
    samples: np.ndarray,
    service_calls: list[str],
    pause_detector,
) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            f"{realtime_url}/v1/realtime/client_secrets",
            headers={"Authorization": "Bearer local-server-token"},
            json={"session": {"type": "realtime"}},
        )
        token_response.raise_for_status()
        token = token_response.json()["value"]

    peer = RTCPeerConnection()
    peer.addTrack(AudioFixtureTrack(samples))
    peer.createDataChannel("data")
    response_audio: list[np.ndarray] = []
    response_ready = asyncio.Event()
    connection_ready = asyncio.Event()
    connection_state = [peer.connectionState]
    consumers: list[asyncio.Task[None]] = []

    @peer.on("connectionstatechange")
    def on_connection_state_change():
        connection_state[0] = peer.connectionState
        if peer.connectionState == "connected":
            connection_ready.set()

    @peer.on("track")
    def on_track(track):
        async def receive():
            while True:
                try:
                    frame = await track.recv()
                except MediaStreamError:
                    return
                samples = np.frombuffer(bytes(frame.planes[0]), dtype=np.int16).copy()
                response_audio.append(samples)
                if np.sqrt(np.mean(samples.astype(np.float32) ** 2)) > 150:
                    response_ready.set()

        consumers.append(asyncio.create_task(receive()))

    try:
        await peer.setLocalDescription(await peer.createOffer())
        deadline = asyncio.get_running_loop().time() + 10
        while peer.iceGatheringState != "complete":
            if asyncio.get_running_loop().time() > deadline:
                raise TimeoutError("Client ICE gathering timed out")
            await asyncio.sleep(0.05)
        async with httpx.AsyncClient(timeout=15) as client:
            answer = await client.post(
                f"{realtime_url}/v1/realtime/calls",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "sdp": peer.localDescription.sdp,
                    "session": '{"type":"realtime"}',
                },
            )
            answer.raise_for_status()
        await peer.setRemoteDescription(RTCSessionDescription(sdp=answer.text, type="answer"))
        try:
            await asyncio.wait_for(connection_ready.wait(), timeout=10)
        except TimeoutError as error:
            raise TimeoutError(
                f"WebRTC did not connect; connection state={connection_state[0]}"
            ) from error
        try:
            await asyncio.wait_for(response_ready.wait(), timeout=20)
        except TimeoutError as error:
            assert service_calls == ["stt", "llm", "tts"], (
                "audio response timed out; "
                f"inference stages={service_calls}, "
                f"connection state={connection_state[0]}, "
                f"detector calls={pause_detector.calls}, "
                f"speech chunks={pause_detector.speech_chunks}"
            )
            raise TimeoutError(
                "Inference completed but WebRTC returned no non-silent audio"
            ) from error
        audio = np.concatenate(response_audio)
        assert audio.size > 0
        assert float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))) > 150
    finally:
        await peer.close()
        for consumer in consumers:
            consumer.cancel()
