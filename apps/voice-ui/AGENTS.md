# Voice UI

Next.js app with assistant-ui, voice-first chat via OpenAI Realtime protocol.

## Golden Rules

- Use conventional commits
- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

---

## Architecture

- `src/voice-ui/` — Core voice library: `OpenAIRealtimeVoiceAdapter` (WS client), `VoiceChat` (UI with voice/language picker), `transport` (proxy/relay/direct resolver)
- `src/voice-ui/audio/wavtools/` — Audio recording/playback helpers (WavRecorder, WavStreamPlayer) from OpenAI Realtime Console
- `src/components/assistant-ui/` — Full Thread UI with rich message rendering (markdown, tool calls, reasoning blocks, file/image display)
- `src/app/page.tsx` — Single page entry, renders `<VoiceChat />`
- `server.mjs` — Custom Next.js server with WebSocket proxy to `REALTIME_WORKER_URL`

## Running

```bash
npx nx run voice-ui:dev           # dev server with WS proxy
pnpm nx run voice-ui:build        # production build
```

## Environment

Copy `.env.example` to `.env.local`:

```env
REALTIME_WORKER_URL=wss://your-modal-app/v1/realtime
WORKER_TOKEN=your-token
```

## Testing

Voice workers are unit-only (no e2e). This app has no tests of its own.
