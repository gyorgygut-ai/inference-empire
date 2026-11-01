from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterator

INFERENCE_TIMEOUT = httpx.Timeout(connect=2.0, read=30.0, write=2.0, pool=1.0)
LLM_TIMEOUT = httpx.Timeout(connect=2.0, read=120.0, write=2.0, pool=1.0)
TTS_TIMEOUT = httpx.Timeout(connect=2.0, read=120.0, write=2.0, pool=1.0)


@dataclass(frozen=True)
class InferenceEndpoint:
    url: str
    api_key: str


class InferenceClient:
    def __init__(
        self,
        stt: InferenceEndpoint,
        llm: InferenceEndpoint,
        tts: InferenceEndpoint,
        timeout: httpx.Timeout | float = INFERENCE_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.timeout = timeout
        self.transport = transport

    @classmethod
    def from_env(cls) -> InferenceClient:
        def endpoint(name: str, url: str | None, api_key: str | None) -> InferenceEndpoint:
            resolved_url = (url or "").strip()
            resolved_key = (api_key or "").strip()
            if not resolved_url or not resolved_key:
                raise RuntimeError(f"{name} endpoint URL and credential must be configured")
            return InferenceEndpoint(url=resolved_url, api_key=resolved_key)

        return cls(
            stt=endpoint(
                "STT Audio Transcriptions",
                os.environ.get("STT_AUDIO_TRANSCRIPTIONS_API_URL"),
                os.environ.get("SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY"),
            ),
            llm=endpoint(
                "LLM Chat Completions",
                os.environ.get("LLM_CHAT_COMPLETIONS_API_URL"),
                os.environ.get("SECRET_LLM_CHAT_COMPLETIONS_API_KEY"),
            ),
            tts=endpoint(
                "TTS Audio Speech",
                os.environ.get("TTS_AUDIO_SPEECH_API_URL"),
                os.environ.get("SECRET_TTS_AUDIO_SPEECH_API_KEY"),
            ),
        )

    def _post(
        self,
        endpoint: InferenceEndpoint,
        path: str,
        timeout: httpx.Timeout | float | None = None,
        **kwargs,
    ) -> httpx.Response:
        url = endpoint.url.rstrip("/")
        if not url.endswith(path):
            url += path
        try:
            with httpx.Client(
                timeout=self.timeout if timeout is None else timeout,
                transport=self.transport,
                headers={"Authorization": f"Bearer {endpoint.api_key}"},
            ) as client:
                response = client.post(url, **kwargs)
                response.raise_for_status()
                return response
        except httpx.TimeoutException as error:
            raise RuntimeError("Inference endpoint timed out") from error
        except httpx.HTTPStatusError as error:
            raise RuntimeError(
                f"Inference endpoint returned HTTP {error.response.status_code}"
            ) from error
        except httpx.RequestError as error:
            raise RuntimeError("Inference endpoint request failed") from error

    def transcribe(self, audio: bytes, filename: str) -> str:
        response = self._post(
            self.stt,
            "/v1/audio/transcriptions",
            files={"file": (filename, audio, "audio/wav")},
            data={"model": "configured", "response_format": "json"},
        )
        try:
            text = response.json()["text"]
        except (ValueError, KeyError, TypeError) as error:
            raise RuntimeError("Audio Transcriptions returned an invalid response") from error
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Audio Transcriptions returned an empty transcript")
        return text.strip()

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self._post(
            self.llm,
            "/v1/chat/completions",
            timeout=LLM_TIMEOUT,
            json={
                "model": "configured",
                "messages": messages,
            },
        )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Chat Completions returned an invalid response") from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Chat Completions returned an empty reply")
        return content.strip()

    def stream_speak(
        self,
        text: str,
        voice: str,
        reference_audio: bytes | None = None,
    ) -> Iterator[np.ndarray]:
        request = {
            "model": "configured",
            "input": text,
            "response_format": "wav",
            "voice": voice,
        }
        if reference_audio is not None:
            request["reference_audio_base64"] = base64.b64encode(
                reference_audio
            ).decode("ascii")
        url = self.tts.url.rstrip("/")
        path = "/v1/audio/speech/stream"
        if not url.endswith(path):
            url += path
        try:
            with httpx.Client(
                timeout=TTS_TIMEOUT,
                transport=self.transport,
                headers={"Authorization": f"Bearer {self.tts.api_key}"},
            ) as client:
                with client.stream("POST", url, json=request) as response:
                    response.raise_for_status()
                    try:
                        sample_rate = int(response.headers["x-sample-rate"])
                    except (KeyError, ValueError) as error:
                        raise RuntimeError(
                            "Audio Speech stream returned an invalid sample rate"
                        ) from error
                    if sample_rate != 24_000:
                        raise RuntimeError(
                            "Audio Speech stream returned an unsupported sample rate"
                        )
                    pending = bytearray()
                    for data in response.iter_bytes():
                        pending.extend(data)
                        complete_bytes = len(pending) & ~1
                        if complete_bytes:
                            samples = bytes(pending[:complete_bytes])
                            del pending[:complete_bytes]
                            yield np.frombuffer(samples, dtype="<i2").copy()
                    if pending:
                        raise RuntimeError(
                            "Audio Speech stream ended with an incomplete PCM sample"
                        )
        except httpx.TimeoutException as error:
            raise RuntimeError("Inference endpoint timed out") from error
        except httpx.HTTPStatusError as error:
            raise RuntimeError(
                f"Inference endpoint returned HTTP {error.response.status_code}"
            ) from error
        except httpx.RequestError as error:
            raise RuntimeError("Inference endpoint request failed") from error


def encode_audio(audio: bytes) -> str:
    return base64.b64encode(audio).decode("ascii")
