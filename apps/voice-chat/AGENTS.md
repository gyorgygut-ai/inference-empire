# Voice Chat

NextJS app for realtime voice chat.

---

## Dev ENV

**env**:
  - `PORT`: `${VOICE_CHAT_PORT}`
  - `WORKER_URL`: `${get-beam-url.ts(workers-voice)}`

**NX**:
  - **Cmd**: `next dev` directly
  - **Depends**: `predev`, `workers-voice:deploy-beam`
  - **Types**: `predev` -> `prebuild` -> `^prebuild`

## Deploy ENV

**dotenv**:
  - `WORKER_URL`: `${get-beam-url.ts(workers-voice)}`

**NX**:
  - **Cmd**: `npx vercel deploy`, with `VOICE_CHAT_VERCEL_{TOKEN|ORG_ID|PROJECT_ID}`
  - **Depends**: `build`, `workers-voice:deploy-beam`
  - **Types**: `build` -> `prebuild` -> `^prebuild`
  - **WORKER_URL**: get directly `get-beam-url.ts(workers-voice)`

---

## UI Flow (Flow-agnostic shell)

**Non-negotiables**:

- USE `@tanstack/ai/*`; utilize the library fully, no hand-rolling
- NO hand-rolled chat state; `@tanstack/ai` owns conversation state
- NO `useEffect` or `useState`; `Draggable` may use `useRef` for transient pointer mechanics, and voice UI may use `useOptimistic<RealtimeStatus>` for presentation only
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO worker URLs or other secrets exposed to the browser

---

## Structure

**{projectRoot} files**:

- `./app/page.tsx`: only `CenteredLayout`
- `./chat/shell/CenteredLayout.tsx`: full-width centered voice-chat content
- `./chat/components/Draggable.tsx`: generic draggable and activatable wrapper
- `./chat/shell/HeroImage.tsx`: hero image fills space
- `./chat/client.tsx`: `chat.AppChat`
- `./chat/options.ts`: chat ui `options` (append-only fetcher inline, no LLM transport)
- `./chat/parts/`: a `part factory` per file
- `./messages/`: vocabulary entrypoint (re-exports default locale)
- `./chat/vocabulary/`: `en.ts` (default)

---

## UI Flow

Realtime voice conversation, with TanStack AI managing the chat and WebRTC carrying live audio.

**Voice Chat**:

- Url: `WORKER_URL`
- Client: use `@tanstack/ai/*` to manage the realtime chat
- Voice: use WebRTC for live audio between the browser and voice worker
- Action: `./app/actions/generate-image` returns a dummy response for now

**1. Start a Voice Conversation**:

- Trigger: user starts a conversation
- Browser requests microphone access
- Establish a realtime voice connection

**2. Speak**:

- User speaks into the microphone
- Send voice input through the realtime connection

**3. Hear the Response**:

- Show the assistant's response in the chat
- Play the assistant's voice response
- Keep the conversation open for the next turn

---

## Beam Session Lifecycle

**Beam**:

- **Autoscaler**: `QueueDepthAutoscaler(max_containers=1, min_containers=0)`
- **Keep Warm**: `keep_warm_seconds=10`
- **Authorization**: `authorized=True`

**Heartbeat**:

- While WebRTC is open, send an authenticated worker `/health` request every second
- Proxy heartbeat through a same-origin Next.js route; never expose `WORKER_URL` or Beam credentials to the browser
- Heartbeats keep Beam's idle timer refreshed while the WebRTC media session is active

**Lifecycle**:

- Browser-side voice detection keeps the WebRTC session open while the user speaks, the assistant replies, and during pauses
- After 10 seconds with no user speech or assistant playback, close WebRTC and stop heartbeats
- Beam may keep the worker warm for up to 10 more seconds after the final heartbeat, then scales it to zero
- Continue local voice detection; on new speech, open a new WebRTC session and buffer audio while it connects
