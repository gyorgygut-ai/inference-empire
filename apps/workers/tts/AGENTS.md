# TTS Audio Speech

TTS Audio Speech worker. OpenAI-compatible Audio Speech API.

## SPECS

**Authentication**:

- **Problem**: Requests need authentication without exposing Beam credentials.
- **Acceptance**:
  - Require Bearer token `SECRET_TTS_AUDIO_SPEECH_API_KEY` on `POST /v1/audio/speech`.
  - Map it in `project.json` from `GENERATED_TTS_AUDIO_SPEECH_API_KEY`.
  - Reject missing or invalid tokens with `401`.
- **Outcome**: Only callers with the configured API key can request speech synthesis.

**Audio response**:

- **Problem**: Callers need usable speech audio in the response without an R2 artifact.
- **Acceptance**:
  - Return JSON containing inline `audio_base64` with WAV audio at `24 kHz` mono.
  - Reject unsupported `response_format` values with `422`.
  - For authenticated text requesting WAV, return non-silent audio.
  - Full-clip synthesis is acceptable until streaming is implemented.
- **Outcome**: Valid requests return non-silent WAV audio inline.

**Health**:

- **Problem**: Deployment health checks must not trigger inference.
- **Acceptance**:
  - `GET /health` succeeds without triggering inference.
- **Outcome**: Health checks do not run synthesis.

## DEPLOY

**Task**: `worker-tts:deploy-beam`
