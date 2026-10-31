# Voice Chat

NextJS app for realtime voice chat.

---

## Non-negotiables

- USE `@tanstack/ai/*`; utilize the library fully, no hand-rolling
- NO hand-rolled chat state; `@tanstack/ai` owns conversation state
- NO `useEffect` or `useState`; `Draggable` may use `useRef` for transient pointer mechanics, and voice UI may use `useOptimistic<RealtimeStatus>` for presentation only
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO API credentials or other secrets exposed to the browser

---

## Server ENV

- `SECRET_OPENAI_API_KEY`: server-side OpenAI credential
- `SECRET_WORKER_URL`: server-side voice worker URL; used to request ephemeral sessions
- `SECRET_BEAM_TOKEN`: workspace secret used by deployment tooling to resolve the worker URL
- `GENERATED_VOICE_WORKER_AUTH_TOKEN`: shared server-to-worker credential used to request an ephemeral session token

---

## Structure

**{projectRoot} files**:

- `./app/page.tsx`: only `CenteredLayout`
- `./chat/shell/CenteredLayout.tsx`: full-width centered voice-chat content
- `./chat/components/Draggable.tsx`: generic draggable and activatable wrapper
- `./chat/client.tsx`: `chat.AppChat`
- `./chat/realtime/VoiceChatView.tsx`: provider selection and `useRealtimeChat`
- `./chat/realtime/fastRtcAdapter.ts`: voice worker adapter
- `./chat/options.ts`: chat UI `options` (append-only fetcher inline, no LLM transport)
- `./chat/parts/`: a `part factory` per file
- `./messages/`: vocabulary entrypoint (re-exports default locale)
- `./chat/vocabulary/`: `en.ts` (default)

---

## Adapters

**Problem**: Use one realtime voice UI with OpenAI Realtime or the voice worker.

**Approach**:
- Use `useRealtimeChat` for both providers
- OpenAI: use `openaiRealtime()` from `@tanstack/ai-openai`
- Worker: use `fastRtcAdapter`
- Pass the matching token provider to `useRealtimeChat`
- Keep provider-specific connection handling inside each adapter

**Outcome**:
- Frontend flow stays the same when switching providers

---

## OpenAI Realtime

**Problem**: Connect to OpenAI Realtime without exposing the permanent API key.

**Approach**:
- Browser requests `/api/voice/openai-session`
- Server uses `OPENAI_API_KEY` to request an ephemeral token
- Browser sends its offer and ephemeral token directly to OpenAI `/v1/realtime/calls`

**Outcome**:
- Permanent API key stays server-side
- OpenAI handles the realtime conversation

---

## Voice Worker

**Problem**: Connect the browser directly to the realtime-session worker without exposing Beam credentials.

**Approach**:
- Browser requests `/api/voice/session`
- Server requests token from `POST /v1/realtime/client_secrets` using `GENERATED_VOICE_WORKER_AUTH_TOKEN`
- Server returns the ephemeral token, worker URL, and short-lived TURN credentials to the browser
- Browser sends its offer directly to the worker URL from the server response at `/v1/realtime/calls`
- Browser configures `RTCPeerConnection` with the returned TURN configuration; fail closed if it is missing
- The temporary TURN credentials are browser-visible by design; `SECRET_HUGGINGFACE_TOKEN` and permanent credentials remain server-side
- Worker handles WebRTC and routes completed turns to configured STT -> LLM -> TTS endpoints
- Inference endpoint URLs and credentials stay server-side
- Text, image, and tool input are unsupported; interruption and session updates are unsupported

**Outcome**:
- Browser connects directly to the worker
- Inference providers can change without changing the client adapter

---

## Frontend Flow

**Problem**: Start and control a realtime voice conversation.

**Approach**:
- Select `openai` or `workers` adapter
- Call `connect` to start a session and establish WebRTC
- Call `disconnect` to close the session
- Show connection status and conversation mode from adapter events
- Capture microphone audio and play received audio

**Outcome**:
- Same UI controls both providers
- Provider-specific capabilities remain in their adapters
