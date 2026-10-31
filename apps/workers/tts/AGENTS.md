# TTS Audio Speech

TTS Audio Speech worker. OpenAI-compatible Audio Speech API.

## Authentication

**Problem**: Authenticate requests without exposing Beam credentials.

**Approach**:
- Bearer token `SECRET_TTS_AUDIO_SPEECH_API_KEY` required for `POST /v1/audio/speech`; `project.json` maps it from `GENERATED_TTS_AUDIO_SPEECH_API_KEY`

**Outcome**:
- Unauthorized requests rejected

## Contract

- Response is `json` with inline `audio_base64` (`wav`, `24 kHz` mono); not `R2` `presigned_url`
- Response audio must be non-silent; full-clip synthesis accepted until streaming lands

## Acceptance Criteria

**Task**: `worker-tts:deploy-beam`

- `GET /health` → succeeds without triggering inference
- `POST /v1/audio/speech` + missing or invalid token → rejects `401`
- `POST /v1/audio/speech` + unsupported `response_format` → rejects `422`
- `POST /v1/audio/speech` + authenticated text requesting `wav` → non-silent WAV audio
