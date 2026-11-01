# TTS Audio Speech

TTS Audio Speech worker. OpenAI-compatible Audio Speech API.

## SPECS

## Hugging Face authentication

Authenticate every Hugging Face Hub request with `SECRET_HUGGINGFACE_TOKEN`. Pass the token directly to Hub APIs and initialize Hub authentication before libraries perform internal downloads.

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

**Voice selection**:

- `voice` defaults to `alloy`; `null` is normalized to `alloy`.
- `alloy` synthesizes without a reference audio prompt.
- A named reference voice requires valid inline `reference_audio_base64` WAV data and synthesizes with that prompt.

**Health**:

- **Problem**: Deployment health checks must not trigger inference.
- **Acceptance**:
  - `GET /health` succeeds without triggering inference.
- **Outcome**: Health checks do not run synthesis.

## DEPLOY

**Task**: `worker-tts:deploy-beam`
