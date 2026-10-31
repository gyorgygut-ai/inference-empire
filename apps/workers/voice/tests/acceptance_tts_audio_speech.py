from __future__ import annotations

import io
import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import soundfile as sf


def find_workspace_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "nx.json").is_file() and (candidate / "package.json").is_file():
            return candidate
    raise RuntimeError(f"could not find Nx workspace root from {start}")


ROOT = Path(os.getenv("NX_WORKSPACE_ROOT", find_workspace_root(Path(__file__).resolve().parent)))
BEAM_SERVICE = "workers-voice-tts-audio-speech"


def main() -> None:
    token = os.environ["GENERATED_TTS_AUDIO_SPEECH_API_KEY"]
    lookup = subprocess.run(
        ["npx", "tsx", "tools/get-beam-url.ts", BEAM_SERVICE],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    request = Request(
        f"{lookup.stdout.strip().rstrip('/')}/v1/audio/speech",
        data=json.dumps(
            {
                "model": "ResembleAI/chatterbox",
                "input": "A short test of synthesized speech.",
                "response_format": "wav",
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    responses: queue.Queue[tuple[bytes | None, Exception | None]] = queue.Queue()

    def send_request() -> None:
        try:
            with urlopen(request, timeout=180) as response:
                responses.put((response.read(), None))
        except HTTPError as error:
            responses.put(
                (None, RuntimeError(f"deployed Audio Speech request failed with HTTP {error.code}"))
            )
        except Exception as error:
            responses.put((None, error))

    threading.Thread(target=send_request, daemon=True).start()
    while True:
        try:
            audio, error = responses.get(timeout=15)
            break
        except queue.Empty:
            print(
                "🐣 TTS acceptance request is still running; Beam logs should be flowing.",
                flush=True,
            )
    if error is not None:
        raise error
    if not audio:
        raise RuntimeError("deployed Audio Speech request returned no audio")
    samples, sample_rate = sf.read(io.BytesIO(audio), dtype="float32")
    if (
        samples.size == 0
        or not np.isfinite(samples).all()
        or float(np.max(np.abs(samples))) < 0.001
    ):
        raise AssertionError("deployed Audio Speech response is empty or silent")

    rejected_request = Request(
        request.full_url,
        data=request.data,
        headers={
            "Authorization": "Bearer invalid-voice-api-key",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(rejected_request, timeout=30):
            raise AssertionError("Audio Speech accepted an invalid API key")
    except HTTPError as error:
        if error.code != 401:
            raise AssertionError(
                f"Audio Speech rejected an invalid API key with HTTP {error.code}, not 401"
            ) from error

    print(
        json.dumps(
            {"service": BEAM_SERVICE, "sample_rate": sample_rate, "samples": int(samples.size)}
        )
    )


if __name__ == "__main__":
    main()
