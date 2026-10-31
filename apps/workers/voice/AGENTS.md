# Voice

Realtime voice worker. Client connects directly over WebRTC.

---

## Authentication

**Problem**: Authenticate client sessions without exposing Beam credentials.

**Approach**:
- Public Beam ingress allows the browser to connect directly to the worker.
- Trusted server authenticates to `POST /v1/realtime/client_secrets` with `GENERATED_VOICE_WORKER_AUTH_TOKEN`.
- Worker issues an ephemeral session token
- Client authenticates `POST /v1/realtime/calls` with the session token

**Outcome**:
- Server credential stays server-side; ephemeral token browser receives only
- Client connects directly to the worker

---

## Turns

**Problem**: Handle realtime voice turns without coupling WebRTC to inference providers.

**Approach**:
- Worker handles WebRTC signaling and turn detection
- For each completed turn, call STT -> LLM -> TTS endpoints
- Return synthesized audio over the active WebRTC connection
- Client API stays unchanged when inference services change

**Outcome**:
- Speech in; spoken response out
- Realtime worker does not load inference models

---

## Inference APIs

**Problem**: Use external or self-hosted inference services without provider-specific worker adapters.

**Approach**:
- STT uses the OpenAI-compatible Audio Transcriptions contract
- LLM uses the OpenAI-compatible Chat Completions contract
- TTS uses the OpenAI-compatible Audio Speech contract
- Configure each stage with its endpoint URL and token
- Endpoint URL identifies a service with a configured model
- Keep provider credentials server-side
- Use a compatibility gateway for providers that do not support these contracts

**Outcome**:
- Switch compatible providers through configuration
- GPU-backed inference can run outside the realtime worker

---

## Environment

**Problem**: Configure inference services without provider-specific settings.

**Approach**:

- `SECRET_HUGGINGFACE_TOKEN`: for `get_cloudflare_turn_credentials_async` 
- `GENERATED_VOICE_WORKER_AUTH_TOKEN` server-to-worker credential for client session creation

- `GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY`: STT endpoint credential
- `STT_AUDIO_TRANSCRIPTIONS_API_URL`: STT endpoint URL resolved by `get-beam-url.ts` after

- `GENERATED_LLM_CHAT_COMPLETIONS_API_KEY`: LLM endpoint credential
- `LLM_CHAT_COMPLETIONS_API_URL`: LLM endpoint URL resolved by `get-beam-url.ts`

- `GENERATED_TTS_AUDIO_SPEECH_API_KEY`: TTS endpoint credential
- `TTS_AUDIO_SPEECH_API_URL`: TTS endpoint URL resolved by `get-beam-url.ts`

**Outcome**:
- Variable names follow the API contract, not the provider
- Change providers by changing endpoint URLs and credentials

---

## Endpoints

**Problem**: Provide OpenAI Realtime-compatible client endpoints and standard inference APIs.

**Client endpoints**:

| Endpoint | Purpose | GPU |
|---|---|---|
| `POST /v1/realtime/client_secrets` | Create an ephemeral session token. | No |
| `POST /v1/realtime/calls` | WebRTC signaling and audio turns; inference is sent to configured services. | No |
| `GET /health` | Report worker health. | No |

**Inference APIs**:

| Contract | Purpose | GPU |
|---|---|---|
| Audio Transcriptions | Transcribe input audio. | Depends on configured endpoint |
| Chat Completions | Generate reply text. | Depends on configured endpoint |
| Audio Speech | Generate reply audio. | Depends on configured endpoint |

**Outcome**:
- Client endpoint names and request/response shapes match OpenAI Realtime
- Inference services use OpenAI-compatible API contracts

---

## Structure

**{projectRoot} files**:

- `worker_voice_realtime_session_beam.py`: realtime session Beam wrapper
- `worker_voice_stt_audio_transcriptions_beam.py`: STT Beam wrapper
- `worker_voice_llm_chat_completions_beam.py`: LLM Beam wrapper
- `worker_voice_tts_audio_speech_beam.py`: TTS Beam wrapper
- `shared/worker_voice.py`: WebRTC and turn orchestration
- `shared/worker_voice_stt_audio_transcriptions.py`: STT service
- `shared/worker_voice_llm_chat_completions.py`: LLM service
- `shared/worker_voice_tts_audio_speech.py`: TTS service
- `shared/inference_client.py`: OpenAI-compatible API clients
- `dist/contract_voice.py`: generated realtime session and turn types
- `dist/contract_voice_llm_chat_completions.py`: generated LLM `Input` and `Output`
- `predeploy*`: generates contract per worker
- `tests/`: contract, local-flow, and inference endpoint tests

---

## Acceptance Criteria

**Task**: `workers-voice:deploy-stt-audio-transcriptions-beam`

- `GET /health` → succeeds without triggering inference
- `POST /v1/audio/transcriptions` + missing or invalid token → rejects `401`
- `POST /v1/audio/transcriptions` + empty or non-audio payload → rejects `422`
- `POST /v1/audio/transcriptions` + authenticated audio fixture → non-empty `text`

**Task**: `workers-voice:deploy-llm-chat-completions-beam`

- `GET /health` → succeeds without triggering inference
- `POST /v1/chat/completions` + missing or invalid token → rejects `401`
- `POST /v1/chat/completions` + malformed request body → rejects `422`
- `POST /v1/chat/completions` + authenticated messages → non-empty `choices[0].message.content`

**Task**: `workers-voice:deploy-tts-audio-speech-beam`

- `GET /health` → succeeds without triggering inference
- `POST /v1/audio/speech` + missing or invalid token → rejects `401`
- `POST /v1/audio/speech` + unsupported `response_format` → rejects `422`
- `POST /v1/audio/speech` + authenticated text requesting `wav` → non-silent WAV audio

**Task**: `workers-voice:deploy-realtime-session-beam`

- `POST /v1/realtime/client_secrets` + missing or invalid `GENERATED_VOICE_WORKER_AUTH_TOKEN` → rejects `401`
- `POST /v1/realtime/calls` + invalid or expired session token → rejects `401`
- `POST /v1/realtime/client_secrets` + trusted token → ephemeral token, `expires_at`, TURN `rtc_configuration`
- WebRTC call through TURN relay + fixture audio → non-silent reply audio after completed STT → LLM → TTS turn -> PROVEN

---

## Verification

**Audit**

-> No model downloads, provider calls, or GPU

| Worker | Unit proof |
|---|---|
| `realtime-session` | Session/token contracts and turn orchestration |
| `stt-audio-transcriptions` | OpenAI-compatible transcription request/response contract |
| `llm-chat-completions` | OpenAI-compatible Chat Completions request/response contract |
| `tts-audio-speech` | OpenAI-compatible speech request/response contract |

**local**:

-> Run local services with deterministic OpenAI-compatible endpoints; no GPU

| Worker | Local proof |
|---|---|
| `realtime-session` | WebRTC negotiation and a complete audio turn using local STT, LLM, and TTS fakes |
| `stt-audio-transcriptions` | Audio fixture returns a non-empty transcript |
| `llm-chat-completions` | Messages return non-empty reply text |
| `tts-audio-speech` | Text returns valid, non-silent audio |

---

**deployed**

-> Test already-deployed services; verification does not deploy them

| Worker | Deployed proof |
|---|---|
| `stt-audio-transcriptions` | Authenticated transcription request returns a transcript |
| `llm-chat-completions` | Authenticated completion request returns reply text |
| `tts-audio-speech` | Authenticated speech request returns non-silent audio |
| `realtime-session` | Client uses short-lived TURN credentials, establishes ICE through a relay, sends fixture audio, and receives non-silent reply audio after a completed STT -> LLM -> TTS turn |

**Deployment order**: deploy STT, LLM, and TTS independently, then deploy `realtime-session`

---

## Deployment

**Problem**: Keep voice components together and deploy each service independently.

**Approach**:
- Keep voice code in the `workers-voice` Nx project
- `deploy-realtime-session-beam`: deploy `worker_voice_realtime_session_beam.py`
- `deploy-stt-audio-transcriptions-beam`: deploy `worker_voice_stt_audio_transcriptions_beam.py`
- `deploy-llm-chat-completions-beam`: deploy `worker_voice_llm_chat_completions_beam.py`
- `deploy-tts-audio-speech-beam`: deploy `worker_voice_tts_audio_speech_beam.py`
- Each target deploys only its matching Beam service
- `deploy-realtime-session-beam` depends on the STT, LLM, and TTS deploy targets so their URLs are available before lookup; Nx may deploy those three prerequisites in parallel
- Configure inference URLs to point to external or self-hosted compatible services
- Deploy directly from `{projectRoot}`

**Outcome**:
- Voice services stay in one Nx project; inference workers deploy before the dependent realtime session
- Inference provider is a configuration choice

---

## Beam Entrypoint

**Problem**: Expose the realtime FastAPI app through Beam.

**Approach**:
- `worker_voice_realtime_session_beam.py:generate` returns the realtime ASGI app
- FastAPI routes define the public HTTP endpoints

**Outcome**:
- `generate` is the Beam entrypoint, not an HTTP endpoint
