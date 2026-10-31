from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def find_workspace_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "nx.json").is_file() and (candidate / "package.json").is_file():
            return candidate
    raise RuntimeError(f"could not find Nx workspace root from {start}")


ROOT = find_workspace_root(Path(__file__).resolve().parent)
SERVICE = "workers-voice-stt-audio-transcriptions"


def deployed_url() -> str:
    result = subprocess.run(
        ["npx", "tsx", "tools/get-beam-url.ts", SERVICE],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout.strip().rstrip("/")


def multipart_body(audio: bytes, boundary: str) -> bytes:
    parts = [
        ("model", "whisper-1"),
        ("language", "en"),
        ("temperature", "0"),
        ("response_format", "json"),
    ]
    body = bytearray()
    for name, value in parts:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        b'Content-Disposition: form-data; name="file"; filename="gut.wav"\r\n'
        b"Content-Type: audio/wav\r\n\r\n"
    )
    body.extend(audio)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return bytes(body)


def main() -> None:
    token = os.environ["SECRET_BEAM_TOKEN"]
    audio = (ROOT / "apps/workers/voice/references/gut.wav").read_bytes()
    boundary = f"voice-{uuid.uuid4().hex}"
    request = Request(
        f"{deployed_url()}/v1/audio/transcriptions",
        data=multipart_body(audio, boundary),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    responses: queue.Queue[tuple[dict[str, object] | None, Exception | None]] = queue.Queue()

    def send_request() -> None:
        try:
            with urlopen(request, timeout=300) as response:
                responses.put((json.load(response), None))
        except HTTPError as error:
            responses.put((None, RuntimeError(
                f"deployed Audio Transcriptions request failed with HTTP {error.code}"
            )))
        except Exception as error:
            responses.put((None, error))

    threading.Thread(target=send_request, daemon=True).start()
    deadline = time.monotonic() + 300
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("deployed Audio Transcriptions request timed out")
        try:
            body, error = responses.get(timeout=min(15, remaining))
            break
        except queue.Empty:
            print("🐣 STT acceptance request is still running; Beam logs are flowing.", flush=True)
    if error is not None:
        raise error
    if body is None:
        raise RuntimeError("deployed Audio Transcriptions request returned no response")
    transcript = body.get("text")
    if not isinstance(transcript, str) or not transcript.strip():
        raise AssertionError("deployed Audio Transcriptions response has no transcript")
    print(json.dumps({"service": SERVICE, "transcript_chars": len(transcript)}))


if __name__ == "__main__":
    main()
