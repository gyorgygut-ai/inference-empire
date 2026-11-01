
# STT Audio Transcriptions

STT Audio Transcriptions worker. OpenAI-compatible Audio Transcriptions API.

## SPECS

## Hugging Face authentication

Authenticate every Hugging Face Hub request with `SECRET_HUGGINGFACE_TOKEN`. Pass the token directly to Hub APIs and initialize Hub authentication before libraries perform internal downloads.

**Authentication**:

- **Problem**: Requests need authentication without exposing Beam credentials.
- **Acceptance**:
  - Require Bearer token `SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY` on `POST /v1/audio/transcriptions`.
  - Map it in `project.json` from `GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY`.
  - Reject missing or invalid tokens with `401`.
- **Outcome**: Only callers with the configured API key can submit transcriptions.

**Audio contract**:

- **Problem**: Realtime callers need to submit audio without unnecessary conversion and receive a transcript.
- **Acceptance**:
  - Accept `24 kHz` mono WAV as-is; do not re-encode it.
  - Reject empty or non-audio payloads with `422`.
  - Reject silent audio with `422`.
  - For authenticated audio, return non-empty `text` with no artifact upload.
- **Outcome**: Valid audio produces a transcript directly; invalid audio is rejected.

**Health**:

- **Problem**: Deployment health checks must not trigger inference.
- **Acceptance**:
  - `GET /health` succeeds without triggering inference.
- **Outcome**: Health checks do not run transcription.

## DEPLOY

**Task**: `worker-stt:deploy-beam`
apps/workers/tts/AGENTS.md
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
