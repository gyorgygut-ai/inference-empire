from __future__ import annotations

import base64
import os
from dataclasses import dataclass

import httpx


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
        timeout: float = 30.0,
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
                os.environ.get("STT_AUDIO_TRANSCRIPTIONS_API_KEY"),
            ),
            llm=endpoint(
                "LLM Chat Completions",
                os.environ.get("LLM_CHAT_COMPLETIONS_API_URL"),
                os.environ.get("LLM_CHAT_COMPLETIONS_API_KEY"),
            ),
            tts=endpoint(
                "TTS Audio Speech",
                os.environ.get("TTS_AUDIO_SPEECH_API_URL"),
                os.environ.get("TTS_AUDIO_SPEECH_API_KEY"),
            ),
        )

    def _post(self, endpoint: InferenceEndpoint, path: str, **kwargs) -> httpx.Response:
        url = endpoint.url.rstrip("/")
        if not url.endswith(path):
            url += path
        try:
            with httpx.Client(
                timeout=self.timeout,
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

    def complete(self, transcript: str) -> str:
        response = self._post(
            self.llm,
            "/v1/chat/completions",
            json={
                "model": "configured",
                "messages": [
                    {"role": "system", "content": "You are a concise, helpful voice assistant."},
                    {"role": "user", "content": transcript},
                ],
            },
        )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Chat Completions returned an invalid response") from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Chat Completions returned an empty reply")
        return content.strip()

    def speak(self, text: str) -> tuple[bytes, int | None]:
        response = self._post(
            self.tts,
            "/v1/audio/speech",
            json={"model": "configured", "input": text, "response_format": "wav"},
        )
        audio = response.content
        if not audio:
            raise RuntimeError("Audio Speech returned empty audio")
        sample_rate = response.headers.get("x-audio-sample-rate")
        return audio, int(sample_rate) if sample_rate and sample_rate.isdigit() else None


def encode_audio(audio: bytes) -> str:
    return base64.b64encode(audio).decode("ascii")
