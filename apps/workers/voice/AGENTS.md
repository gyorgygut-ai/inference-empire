# Voice Realtime Session

Realtime voice worker. Client connects directly over WebRTC.

## SPECS

**Authentication**:

- **Problem**: Browser clients need worker access without receiving the trusted server credential.
- **Acceptance**:
  - Public Beam ingress allows the browser to connect directly to the worker.
  - Require `SECRET_VOICE_WORKER_AUTH_TOKEN` on `POST /v1/realtime/client_secrets`.
  - Map it in `project.json` from `GENERATED_VOICE_WORKER_AUTH_TOKEN`.
  - Issue an in-process ephemeral session token with a `60s` TTL.
  - Run one instance (`max_containers=1`); token persistence is not guaranteed beyond that running instance.
  - Require the session token on `POST /v1/realtime/calls`.
  - Reject missing or invalid server credentials with `401`.
  - Reject invalid or expired session tokens with `401`.
  - With a trusted token, return an ephemeral token, `expires_at`, and TURN `rtc_configuration`.
- **Outcome**: The trusted credential stays server-side; the browser receives only a short-lived session token.

**Transport**:

- **Problem**: Realtime media needs browser-compatible ICE configuration, negotiation, and teardown.
- **Acceptance**:
  - Use `fastrtc.Stream` for negotiation, teardown, and RTC configuration, following the documented API for the pinned FastRTC revision.
  - Set `rtc_configuration=get_cloudflare_turn_credentials_async`; TURN is required, STUN alone is insufficient.
  - The worker API contract owns exactly `POST /v1/realtime/client_secrets` and `POST /v1/realtime/calls`; these are not OpenAI routes. The authenticated `/calls` route delegates negotiation to FastRTC's `Stream.offer()`.
  - FastRTC owns SDP negotiation; the route may authenticate and adapt the request/response but must not implement SDP negotiation, add a second negotiation route, or re-validate FastRTC’s normalized config.
  - `Stream.mount()` registers FastRTC's default routes, including `/webrtc/offer`, so do not use it when it would add routes or change the required `/v1/realtime/calls` contract. Verify the `Stream.offer()` API against the pinned FastRTC revision.
  - Prove a WebRTC call through TURN relay using fixture audio.
- **Outcome**: FastRTC owns transport negotiation, teardown, and configuration.

**Turn detection**:

- **Problem**: A single RMS threshold cannot reliably distinguish turns from pauses and silence.
- **Acceptance**:
  - Pass `ReplyOnPause` to `Stream(handler=...)` at construction; do not assign it afterward.
  - Tune turn detection through `AlgoOptions` or `SileroVADOptions` (`fastrtc[vad]`).
  - Name each turn-detection constant once in `shared/`.
  - Use `warmup()` only when a real model requires it.
  - Do not add custom VAD classes.
- **Outcome**: Turn boundaries use a documented, configurable detector.

**Audio contract**:

- **Problem**: Incorrect audio dtype or sample rate can silently produce near-silence.
- **Acceptance**:
  - Yield `(sample_rate, np.int16)` from the handler; keep float32 internal to processing.
  - Use `24 kHz` mono end to end and resample once at the boundary.
  - Reject empty, silent, or non-finite input before STT.
  - Reject silent TTS output.
  - After a completed STT → LLM → TTS turn, produce non-silent `int16` reply audio, proven with `output_rms`.
- **Outcome**: Each completed turn returns audible audio under a consistent contract.

**Concurrency**:

- **Problem**: Blocking inference or audio I/O in an async handler can serialize sessions.
- **Acceptance**:
  - Run synchronous inference off the event loop.
  - Set `concurrent_requests` to the measured number of simultaneous turns.
  - Do not share mutable state without a per-session key.
  - Prove two clients talking at once both receive replies.
- **Outcome**: Concurrent sessions make progress without unkeyed shared mutable state.

**Session state**:

- **Problem**: Conversation state must not leak between clients or grow without bound.
- **Acceptance**:
  - Get session identity from `get_current_context().webrtc_id` inside the handler.
  - Keep history per session, bound it with `max_history`, and drop it when the session ends.
  - Keep the LLM stateless; history must not live on the worker beyond the session.
  - Prove concurrent sessions receive replies reflecting only their own history.
- **Outcome**: Session history is bounded and isolated; reconnects start clean.

**Failure handling**:

- **Problem**: A failed turn must not terminate the call.
- **Acceptance**:
  - Treat empty transcript, empty reply, invalid audio, or silent audio as an error event for that turn.
  - Keep the session open; do not send `500` errors over the data channel.
  - Log the failing stage as `stt`, `llm`, or `tts`; do not log bare exceptions.
  - Prove silent input produces an error event and leaves the session usable.
- **Outcome**: Clients can retry failed turns; the stream remains usable and logs identify the failing stage.

## DEPLOY

**Task**: `worker-voice:deploy-beam`
