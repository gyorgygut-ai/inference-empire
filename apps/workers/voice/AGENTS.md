# Voice Realtime Session

Realtime voice worker. Client connects directly over WebRTC.

## Authentication

**Problem**: Authenticate client sessions without exposing Beam credentials.

**Approach**:
- Public Beam ingress allows the browser to connect directly to the worker.
- Trusted server authenticates to `POST /v1/realtime/client_secrets` with `SECRET_VOICE_WORKER_AUTH_TOKEN`, mapped from `GENERATED_VOICE_WORKER_AUTH_TOKEN` in `project.json`
- Worker issues an ephemeral session token, in-process, TTL `60s`; single instance (`max_containers=1`)
- Client authenticates `POST /v1/realtime/calls` with the session token

**Outcome**:
- Server credential stays server-side; ephemeral token browser receives only
- Client connects directly to the worker
- Token persistence is not claimed beyond the running instance

## Transport

**Problem**: Realtime media needs ICE, teardown and RTC config that browsers agree on.

**Approach**:
- `fastrtc.Stream` owns negotiation, teardown and RTC config; mount per FastRTC docs
- `rtc_configuration=get_cloudflare_turn_credentials_async`; TURN required, STUN alone insufficient
- Project-specific routes are exactly `POST /v1/realtime/client_secrets` + `POST /v1/realtime/calls`; both are ours, not OpenAI routes

**Outcome**:
- No hand-rolled SDP endpoints; no re-validation of FastRTC's normalized config
- One place to change if the transport moves

## Turn Detection

**Problem**: A single RMS threshold is not turn detection; it misfires on pauses and silence.

**Approach**:
- `ReplyOnPause` wraps the handler, passed at `Stream(handler=...)` construction, never assigned afterwards
- Tuning via `AlgoOptions` or `SileroVADOptions` (`fastrtc[vad]`); every constant named once in `shared/`
- `warmup()` only where a real model needs it; no stubs

**Outcome**:
- Turn boundary behaviour is a documented option, not a magic number
- No custom VAD classes

## Audio Contract

**Problem**: FastRTC exchanges `int16`; float buffers silently decode as near-silence.

**Approach**:
- Handler yields `(sample_rate, np.int16)`; float32 stays internal to processing
- `24 kHz` mono end to end; resample once, at the boundary
- Reject empty, silent or non-finite input before `stt`; reject silent `tts` output

**Outcome**:
- Reply audio is audible, proven by `output_rms` in acceptance
- One dtype and one sample rate across `stt` → `llm` → `tts`

## Concurrency

**Problem**: Sync inference or audio IO inside an async handler serializes every session.

**Approach**:
- No blocking calls on the event loop; sync inference runs off-loop
- `concurrent_requests` equals measured simultaneous turns, not a guess
- No shared mutable state without a per-session key

**Outcome**:
- Two clients talking at once both get replies
- Capacity claims are measured

## Session State

**Problem**: Conversation state keyed by anything but the session bleeds across clients.

**Approach**:
- Session identity from `get_current_context().webrtc_id` inside the handler
- History per session, bounded (`max_history`), dropped when the session ends
- `llm` is stateless; history never lives on the worker's server side beyond the session

**Outcome**:
- No cross-session history leak; no unbounded dict growth
- Reconnect starts a clean session

## Failure

**Problem**: One bad turn must not drop the call.

**Approach**:
- Empty transcript, empty reply, invalid or silent audio → error event for that turn only
- Session stays open; no `500` reaches the data channel
- Log the failing stage: `stt` | `llm` | `tts`

**Outcome**:
- Client retries the turn; stream survives
- Stage attribution in logs, no bare exceptions

## Acceptance Criteria

**Task**: `worker-voice:deploy-beam`

- `POST /v1/realtime/client_secrets` + missing or invalid server credential → rejects `401`
- `POST /v1/realtime/calls` + invalid or expired session token → rejects `401`
- `POST /v1/realtime/client_secrets` + trusted token → ephemeral token, `expires_at`, TURN `rtc_configuration`
- WebRTC call through TURN relay + fixture audio → non-silent `int16` reply audio after completed STT → LLM → TTS turn -> PROVEN
- two concurrent sessions → each reply reflects only its own history
- turn with silent input → error event, session remains usable
