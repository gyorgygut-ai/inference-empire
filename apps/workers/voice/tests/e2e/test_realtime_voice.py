import asyncio
import json
import math
import os
import time
import wave
from pathlib import Path

import httpx
import numpy as np
import pytest
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
from aiortc.mediastreams import MediaStreamError

BASE = os.environ["VOICE_REALTIME_SESSION_API_URL"].rstrip("/")
SERVER_TOKEN = os.environ.get("SECRET_VOICE_WORKER_AUTH_TOKEN") or os.environ[
    "GENERATED_VOICE_WORKER_AUTH_TOKEN"
]
FIXTURES = Path(__file__).parent.parent / "fixtures"
MESSAGE_AUDIO = FIXTURES / "message.wav"
CLIENT_TIMEOUT = httpx.Timeout(connect=2.0, read=30.0, write=5.0, pool=2.0)
UNSET = object()


def _output_rms(samples: np.ndarray) -> float:
    normalized = samples.astype(np.float32)
    if np.issubdtype(samples.dtype, np.floating):
        normalized *= 32767
    return math.sqrt(float(np.mean(np.square(normalized))))


def _run_async(coroutine):
    return asyncio.run(coroutine)


async def _client_secret(client: httpx.AsyncClient, voice: object = UNSET):
    session = {} if voice is UNSET else {"voice": voice}
    response = await client.post(
        f"{BASE}/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {SERVER_TOKEN}"},
        json={"session": session},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _start_call(
    voice: object = UNSET,
    audio_path: Path = MESSAGE_AUDIO,
):
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        secret = await _client_secret(client, voice)
        configuration = RTCConfiguration(
            iceServers=[
                RTCIceServer(
                    urls=server["urls"],
                    username=server.get("username"),
                    credential=server.get("credential"),
                )
                for server in secret["rtc_configuration"]["iceServers"]
            ]
        )
        peer = RTCPeerConnection(configuration=configuration)
        player = MediaPlayer(str(audio_path), format="wav")
        assert player.audio is not None, "audio input could not be sent"
        sender = peer.addTrack(player.audio)
        channel = peer.createDataChannel("text")
        received_audio = asyncio.Event()
        output_rms: list[float] = []
        channel_messages: list[str] = []

        @channel.on("message")
        def receive_message(message):
            if isinstance(message, str):
                channel_messages.append(message)

        @peer.on("track")
        async def receive_audio(track):
            while True:
                try:
                    frame = await track.recv()
                except MediaStreamError:
                    return
                rms = _output_rms(frame.to_ndarray())
                output_rms.append(rms)
                if rms > 32:
                    received_audio.set()

        try:
            offer = await peer.createOffer()
            await peer.setLocalDescription(offer)
            deadline = asyncio.get_running_loop().time() + 30
            while peer.iceGatheringState != "complete":
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError("ICE gathering timed out")
                await asyncio.sleep(0.1)
            answer = await client.post(
                f"{BASE}/v1/realtime/calls",
                headers={"Authorization": f"Bearer {secret['value']}"},
                data={"sdp": peer.localDescription.sdp},
            )
            assert answer.status_code == 200, answer.text
            assert answer.headers.get("content-type", "").startswith("application/sdp")
            await peer.setRemoteDescription(
                RTCSessionDescription(
                    sdp=answer.text, type="answer"
                )
            )
            return (
                peer,
                player,
                sender,
                received_audio,
                output_rms,
                channel_messages,
                secret,
            )
        except BaseException:
            await peer.close()
            player.audio.stop()
            raise


async def _wait_for_audio(received_audio: asyncio.Event, messages: list[str]) -> None:
    waiter = asyncio.create_task(received_audio.wait())
    try:
        deadline = asyncio.get_running_loop().time() + 120
        while not waiter.done():
            for message in messages:
                try:
                    event = json.loads(message)
                except ValueError:
                    continue
                if event.get("type") == "error":
                    raise AssertionError(f"realtime turn failed: {event}")
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("realtime audio response timed out")
            await asyncio.sleep(0.1)
    finally:
        if not waiter.done():
            waiter.cancel()


async def _run_audio_turn(voice: object = UNSET) -> tuple[float, str]:
    peer, player, _, received_audio, output_rms, messages, secret = await _start_call(voice)
    try:
        await _wait_for_audio(received_audio, messages)
        return max(output_rms, default=0), secret["session"]["voice"]
    finally:
        await peer.close()
        player.audio.stop()


async def _valid_client_secret() -> bool:
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        secret = await _client_secret(client)
        now = int(time.time())
    servers = secret["rtc_configuration"].get("iceServers", [])
    urls = [server["urls"] for server in servers]
    urls = [url for group in urls for url in (group if isinstance(group, list) else [group])]

    return (
        secret["value"] != SERVER_TOKEN
        and 0 < secret["expires_at"] - now <= 60
        and any("turn:" in url for url in urls)
    )


def test_client_secrets_with_valid_server_token_returns_ephemeral_token_expiry_and_turn_config():
    assert _run_async(_valid_client_secret())


async def _client_secret_rejects(authorization: str | None) -> bool:
    headers = {} if authorization is None else {"Authorization": authorization}
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        response = await client.post(
            f"{BASE}/v1/realtime/client_secrets", headers=headers, json={"session": {}}
        )
    return response.status_code == 401


@pytest.mark.parametrize("authorization", [None, "Bearer invalid"])
def test_client_secrets_with_missing_or_invalid_server_token_returns_401(authorization):
    assert _run_async(_client_secret_rejects(authorization))


async def _call_rejects_missing_and_invalid_tokens() -> bool:
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        responses = [
            await client.post(
                f"{BASE}/v1/realtime/calls", headers=headers, data={"sdp": "invalid"}
            )
            for headers in ({}, {"Authorization": "Bearer invalid"})
        ]
    return all(response.status_code == 401 for response in responses)


def test_call_with_missing_or_invalid_session_token_returns_401():
    assert _run_async(_call_rejects_missing_and_invalid_tokens())


async def _call_returns_audio() -> bool:
    peer, player, _, received_audio, output_rms, messages, _ = await _start_call()
    try:
        await _wait_for_audio(received_audio, messages)
        return (
            peer.connectionState == "connected"
            and max(output_rms, default=0) > 32
        )
    finally:
        await peer.close()
        player.audio.stop()


def test_call_with_valid_session_token_returns_audible_audio():
    assert _run_async(_call_returns_audio())


async def _voice_input_returns_audio(voice: object, expected: str) -> bool:
    rms, selected_voice = await _run_audio_turn(voice)
    return selected_voice == expected and rms > 32


@pytest.mark.parametrize(
    ("voice", "expected"),
    [(UNSET, "alloy"), (None, "alloy"), ("alloy", "alloy"), ("GUT", "GUT")],
    ids=["omitted", "null", "alloy", "reference"],
)
def test_turn_with_voice_input_returns_audible_audio(voice, expected):
    assert _run_async(_voice_input_returns_audio(voice, expected))


async def _silent_turn_recovers(tmp_path: Path) -> bool:
    silence_path = tmp_path / "silence.wav"
    with wave.open(str(silence_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24_000)
        wav.writeframes(bytes(int(24_000 * 2.4 * 2)))

    peer, player, sender, received_audio, output_rms, messages, _ = await _start_call(
        "alloy", silence_path
    )
    valid_player = None
    try:
        deadline = asyncio.get_running_loop().time() + 30
        while asyncio.get_running_loop().time() < deadline:
            if any(
                json.loads(message).get("type") == "error"
                for message in messages
                if message.startswith("{")
            ):
                break
            await asyncio.sleep(0.1)
        else:
            return False

        valid_player = MediaPlayer(str(MESSAGE_AUDIO), format="wav")
        if valid_player.audio is None:
            return False
        sender.replaceTrack(valid_player.audio)
        await asyncio.wait_for(received_audio.wait(), timeout=120)
        return max(output_rms, default=0) > 32
    finally:
        await peer.close()
        player.audio.stop()
        if valid_player and valid_player.audio:
            valid_player.audio.stop()


def test_turn_with_silent_audio_emits_error_and_same_call_recovers(tmp_path):
    assert _run_async(_silent_turn_recovers(tmp_path))


async def _concurrent_turns_return_audio() -> bool:
    results = await asyncio.gather(
        _run_audio_turn("alloy"),
        _run_audio_turn("GUT"),
    )
    return [(voice, rms > 32) for rms, voice in results] == [("alloy", True), ("GUT", True)]


def test_turns_with_two_concurrent_clients_both_return_audible_audio():
    assert _run_async(_concurrent_turns_return_audio())
