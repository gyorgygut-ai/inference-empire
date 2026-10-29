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
- NO hand-rolled ui; NO state management; `@tanstack/ai` does it
- NO `useEffect`, `useState`; state travels through the chat
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO worker URLs or other secrets exposed to the browser

---

## Structure

**{projectRoot} files**:

- `./app/page.tsx`: only `SplitLayout`
- `./chat/shell/SplitLayout.tsx`:
  - default: full width `chat/Client`
  - from md: 2/3 `aside > HeroImage` + 1/3 `chat/Client`
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
