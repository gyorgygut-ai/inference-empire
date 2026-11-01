import asyncio
import math
import os
from pathlib import Path

import httpx
import numpy as np
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer

BASE = os.environ["VOICE_REALTIME_SESSION_API_URL"].rstrip("/")
SERVER_TOKEN = os.environ["GENERATED_VOICE_WORKER_AUTH_TOKEN"]
FIXTURES = Path(__file__).parent.parent / "fixtures"
MESSAGE_AUDIO = FIXTURES / "message.wav"


async def _complete_realtime_call() -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        secret_response = await client.post(
            f"{BASE}/v1/realtime/client_secrets",
            headers={"Authorization": f"Bearer {SERVER_TOKEN}"},
            json={"session": {}},
        )
        assert secret_response.status_code == 200, secret_response.text
        secret = secret_response.json()
        ice_servers = secret["rtc_configuration"]["iceServers"]
        configuration = RTCConfiguration(
            iceServers=[
                RTCIceServer(
                    urls=server["urls"],
                    username=server.get("username"),
                    credential=server.get("credential"),
                )
                for server in ice_servers
            ]
        )

        peer = RTCPeerConnection(configuration=configuration)
        player = MediaPlayer(str(MESSAGE_AUDIO), format="wav")
        assert player.audio is not None, "message fixture contains no audio"
        peer.addTrack(player.audio)
        peer.createDataChannel("text")
        received_audio = asyncio.Event()
        output_rms: list[float] = []

        @peer.on("track")
        async def on_track(track):
            while True:
                frame = await track.recv()
                samples = frame.to_ndarray()
                samples_float = samples.astype(np.float32)
                if np.issubdtype(samples.dtype, np.floating):
                    samples_float *= 32767
                rms = math.sqrt(float(np.mean(np.square(samples_float))))
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
                RTCSessionDescription(sdp=answer.text, type="answer")
            )
            await asyncio.wait_for(received_audio.wait(), timeout=120)
            assert max(output_rms, default=0) > 32, "worker returned silent audio"
        finally:
            await peer.close()
            player.audio.stop()


def test_local_worker_completes_realtime_voice_call() -> None:
    asyncio.run(_complete_realtime_call())
