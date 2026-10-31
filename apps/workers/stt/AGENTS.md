# STT Audio Transcriptions

STT Audio Transcriptions worker. OpenAI-compatible Audio Transcriptions API.

## Authentication

**Problem**: Authenticate requests without exposing Beam credentials.

**Approach**:
- Bearer token `SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY` required for `POST /v1/audio/transcriptions`; `project.json` maps it from `GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY`

**Outcome**:
- Unauthorized requests rejected

## Contract

- Realtime callers send `24 kHz` mono `wav`; accept it as-is, no re-encode
- Response is `text`; no artifact upload

## Acceptance Criteria

**Task**: `worker-stt:deploy-beam`

- `GET /health` → succeeds without triggering inference
- `POST /v1/audio/transcriptions` + missing or invalid token → rejects `401`
- `POST /v1/audio/transcriptions` + empty or non-audio payload → rejects `422`
- `POST /v1/audio/transcriptions` + silent audio → rejects `422`
- `POST /v1/audio/transcriptions` + authenticated audio fixture → non-empty `text`
