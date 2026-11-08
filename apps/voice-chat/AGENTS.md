# Voice Chat

NextJS app for realtime voice chat.

---

## Non-negotiables

- USE `@tanstack/ai/*`; utilize the library fully, no hand-rolling
- NO hand-rolled chat state; `@tanstack/ai` owns conversation state
- NO `useEffect`; `Draggable` may use `useRef` for transient pointer mechanics, voice UI may use `useOptimistic<RealtimeStatus>` for presentation only, and `VoiceChatView` may use `useState<VoiceProvider>` only for the adapter selector
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO API credentials or other secrets exposed to the browser

---

## Server ENV

- `SECRET_OPENAI_API_KEY`: server-side OpenAI credential
- `SECRET_ELEVENLABS_API_KEY`: server-side ElevenLabs credential
- `SECRET_ELEVENLABS_AGENT_ID`: ElevenLabs Conversational AI agent ID
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
- `./chat/realtime/VoiceChatView.tsx`: provider selection
- `./chat/realtime/RealtimeVoiceSession.tsx`: keyed realtime client session
- `./config.ts`: server-only validated application environment
- `./config.schema.ts`: Voice Chat application environment contract
- `./chat/realtime/fastRtcAdapter.ts`: voice worker adapter
- `./chat/options.ts`: chat UI `options` (append-only fetcher inline, no LLM transport)
- `./chat/parts/`: a `part factory` per file
- `./messages/`: vocabulary entrypoint (re-exports default locale)
- `./chat/vocabulary/`: `en.ts` (default)

---

## Adapters

**Problem**: Use one realtime voice UI with OpenAI Realtime, ElevenLabs, or the voice worker.

**Approach**:
- Use `useRealtimeChat` for both adapters
- `OPENAI`: use `openaiRealtime()` from `@tanstack/ai-openai`
- `ELEVENLABS`: use `elevenlabsRealtime()` from `@tanstack/ai-elevenlabs`
- `VOICE_FASTRTC`: use `fastRtcAdapter`
- Pass the matching token provider to `useRealtimeChat`
- Keep provider-specific connection handling inside each adapter
- Key the realtime session by provider so switching adapters creates a new TanStack realtime client

**Outcome**:
- Frontend flow stays the same when switching providers

---

## OpenAI Realtime

**Problem**: Connect to OpenAI Realtime without exposing the permanent API key.

**Approach**:
- Browser requests `/api/voice/openai-session`
- Server environment is read through `config.ts`, never directly from route handlers
- Server uses `OPENAI_API_KEY` to request an ephemeral token
- Browser sends its offer and ephemeral token directly to OpenAI `/v1/realtime/calls`

**Outcome**:
- Permanent API key stays server-side
- OpenAI handles the realtime conversation

---

## ElevenLabs Realtime

**Problem**: Connect to an ElevenLabs Conversational AI agent without exposing the permanent API key.

**Approach**:
- Configure the agent, voice, and prompt in the ElevenLabs dashboard
- Browser requests `/api/voice/elevenlabs-session`
- Server validates the key and agent ID through `config.ts`; the TanStack token adapter reads server-only `ELEVENLABS_API_KEY` and mints a signed URL token
- Browser connects using `elevenlabsRealtime()`; the signed URL is temporary and the permanent key stays server-side
- Treat agent configuration as fixed for the session; images and real time-domain waveform data are unsupported

**Outcome**:
- ElevenLabs agent handles realtime voice while the shared UI controls the session

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
- Select `ELEVENLABS`, `OPENAI`, or `VOICE_FASTRTC`; default to `ELEVENLABS`
- Read and validate Voice Chat server environment through `config.ts`; app routes must not access `process.env` directly
- Call `connect` to start a session and establish WebRTC
- Call `disconnect` to close the session
- Show connection status and conversation mode from adapter events
- Capture microphone audio and play received audio

**Outcome**:
- Same UI controls both providers
- Provider-specific capabilities remain in their adapters
