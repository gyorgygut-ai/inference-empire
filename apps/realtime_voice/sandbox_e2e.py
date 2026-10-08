"""GPU sandbox verification for realtime-voice-qwen. No deploy, no endpoint.

Usage: npx nx run realtime-voice:e2e-sandbox
Exit 0 + E2E_PASS on a full voice turn, exit 1 otherwise (incl. timeout).
Honours SANDBOX_TIMEOUT (seconds, exec budget) and SANDBOX_GPU env vars.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    import modal

    from apps.realtime_voice.worker_modal_cls_realtime_voice_qwen import (
        MODEL_MOUNT,
        hf_cache_vol,
        image,
    )

    timeout_s = int(os.environ.get("SANDBOX_TIMEOUT", "600"))
    gpu = os.environ.get("SANDBOX_GPU", "L4")
    app = modal.App.lookup("realtime-voice-sandbox", create_if_missing=True)
    img = image.add_local_file(
        "apps/realtime_voice/tests/fixtures/hello.wav", "/tmp/hello.wav"
    )
    sb = modal.Sandbox.create(
        image=img,
        gpu=gpu,
        volumes={MODEL_MOUNT: hf_cache_vol},
        cpu=4,
        memory=32768,
        timeout=timeout_s * 2,
        app=app,
    )
    try:
        print("GPU sandbox up", flush=True)
        code = "\n".join(
            [
                "import base64, wave",
                "import numpy as np",
                "from apps.realtime_voice import _shared_realtime_voice_qwen as shared",
                "from apps.realtime_voice._shared_realtime_voice_qwen import float_to_pcm16",
                "with wave.open('/tmp/hello.wav', 'rb') as wf:",
                "    assert (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) == (1, 2, 24000)",
                "    frames = wf.readframes(wf.getnframes())",
                "arr = np.frombuffer(frames, dtype='<i2').astype(np.float32) / 32768.0",
                "audio = base64.b64encode(float_to_pcm16(arr)).decode('ascii')",
                "print('payload pcm bytes:', len(frames), flush=True)",
                "models = shared.load_dependencies()",
                "req = shared.RealtimeVoiceInput(audio=audio, voice='gyorgy')",
                "out = shared.do_inference(models, req)",
                "assert out.transcript.strip(), 'empty transcript'",
                "pcm = base64.b64decode(out.audio)",
                "assert len(pcm) > 0 and any(pcm), 'silent reply'",
                "assert out.sample_rate == 24000",
                "print('TRANSCRIPT:', out.transcript[:200], flush=True)",
                "print('AUDIO_B64_LEN:', len(out.audio), flush=True)",
                "print('SAMPLE_RATE:', out.sample_rate, flush=True)",
                "print('E2E_PASS', flush=True)",
            ]
        )
        env = {
            "WHISPER_PATH": f"{MODEL_MOUNT}/whisper-fw",
            "QWEN_PATH": f"{MODEL_MOUNT}/qwen25-3b",
            "REFERENCE_VOICES_DIR": f"{MODEL_MOUNT}/reference_voices",
        }
        proc = sb.exec("python", "-c", code, env=env, timeout=timeout_s)
        out = proc.stdout.read()
        print(out, flush=True)
        print(proc.stderr.read(), flush=True)
        return 0 if "E2E_PASS" in out else 1
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}", flush=True)
        return 1
    finally:
        sb.terminate()
        print("GPU_SANDBOX_DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
