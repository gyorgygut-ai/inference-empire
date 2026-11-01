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
FIXTURE_AUDIO = (
    Path(__file__).parents[3]
    / "realtime_voice"
    / "tests"
    / "fixtures"
    / "hello.wav"
)


async def verify_realtime_voice_call() -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        unauthorized = await client.post(
            f"{BASE}/v1/realtime/client_secrets",
            headers={"Authorization": "Bearer invalid"},
            json={"session": {}},
        )
        assert unauthorized.status_code == 401, "invalid server token was accepted"

        secret_response = await client.post(
            f"{BASE}/v1/realtime/client_secrets",
            headers={"Authorization": f"Bearer {SERVER_TOKEN}"},
            json={"session": {}},
        )
        assert secret_response.status_code == 200, "session token request failed"
        secret = secret_response.json()
        assert secret.get("value"), "ephemeral token missing"
        assert secret.get("expires_at"), "token expiration missing"
        ice_servers = secret["rtc_configuration"].get("iceServers", [])
        assert ice_servers, "TURN configuration missing"
        rtc_configuration = RTCConfiguration(
            iceServers=[
                RTCIceServer(
                    urls=server["urls"],
                    username=server.get("username"),
                    credential=server.get("credential"),
                )
                for server in ice_servers
            ]
        )

        peer = RTCPeerConnection(configuration=rtc_configuration)
        player = MediaPlayer(str(FIXTURE_AUDIO), format="wav")
        assert player.audio is not None, "fixture has no audio track"
        sender = peer.addTrack(player.audio)
        peer.createDataChannel("text")
        audio_received = asyncio.Event()
        rms_values: list[float] = []

        @peer.on("track")
        async def receive_audio(track):
            while True:
                frame = await track.recv()
                samples = frame.to_ndarray()
                normalized = samples.astype(np.float32)
                if np.issubdtype(samples.dtype, np.floating):
                    normalized *= 32767
                rms_values.append(float(math.sqrt(float(np.mean(np.square(normalized))))))
                if rms_values[-1] > 32:
                    audio_received.set()

        try:
            offer = await peer.createOffer()
            await peer.setLocalDescription(offer)
            deadline = asyncio.get_running_loop().time() + 30
            while peer.iceGatheringState != "complete":
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError("ICE gathering timed out")
                await asyncio.sleep(0.1)

            answer_response = await client.post(
                f"{BASE}/v1/realtime/calls",
                headers={"Authorization": f"Bearer {secret['value']}"},
                data={"sdp": peer.localDescription.sdp},
            )
            assert answer_response.status_code == 200, "worker rejected WebRTC offer"
            assert answer_response.headers.get("content-type", "").startswith(
                "application/sdp"
            ), "worker returned an invalid SDP answer"
            await peer.setRemoteDescription(
                RTCSessionDescription(sdp=answer_response.text, type="answer")
            )
            await asyncio.wait_for(audio_received.wait(), timeout=120)

            ice_transports = {
                transceiver.receiver.transport.transport
                for transceiver in peer.getTransceivers()
            }
            if peer.sctp is not None:
                ice_transports.add(peer.sctp.transport.transport)
            nominated_pairs = [
                pair
                for transport in ice_transports
                for pair in transport._connection._nominated.values()
            ]
            assert peer.iceConnectionState == "completed", "ICE did not complete"
            assert peer.connectionState == "connected", "WebRTC peer did not connect"
            assert any(
                pair.local_candidate.type == "relay"
                and pair.remote_candidate.type in {"host", "srflx", "prflx", "relay"}
                for pair in nominated_pairs
            ), "nominated WebRTC pair did not use client TURN relay"
            sender_stats = await sender.getStats()
            assert any(
                getattr(stat, "type", None) == "outbound-rtp"
                and getattr(stat, "packetsSent", 0) > 0
                for stat in sender_stats.values()
            ), "fixture audio was not sent"
            assert max(rms_values, default=0) > 32, "worker returned silent audio"
        finally:
            await peer.close()
            player.audio.stop()


def main() -> None:
    asyncio.run(verify_realtime_voice_call())


if __name__ == "__main__":
    main()
