# Chat — assistant-ui direct handler + tool-call (both)

## Stack
- `@assistant-ui/react` + `@assistant-ui/react-ai-sdk` via `useLocalRuntime` / `useExternalStoreRuntime` for direct handler + `tool` / `frontendTools` + `AssistantChatTransport` for LLM tool-call
- Direct handler: `aui.thread.append`, `composer().send()` (`architecture.md:55-69`) vs LLM `tool-call` (`ToolCallMessagePart`)

## Entry
- Model selector dropdown (header/composer, `ModelContext` / `useAui().modelContext()`) — pick `vision|flux|krea|h3|h3-ref` then `composer.send()`
- Not a modal

## Handler
- Direct: maps `message.text -> inputs.prompt` (stem `model` from manifest gives contract) plus context boxes, `POST` via `src/app/api/chat/route.ts` proxy hiding keys (`AGENTS.md:13`)
- Tool-call: LLM emits `tool-call` with same `inputs` schema (stem `model` = contract key), `execute` `POST` same proxy
- Sync `eq/cls` (<5s) direct response, async `tq` 30-60s / `h3` 3600s poll `../workers/e2e_targets.py:70-82`, default `3600s` for all
- Result appended as `TextPart` / `ImagePart {image: presigned_url}` / `FilePart` -> chat + Artifacts `presigned_url`

## Workers — context-specific extra boxes (only when that model picked)

- `vision` `small_vision` — sync direct handler only — no extra boxes, image attachment → JSON inline (stem `small_vision`)
- `flux` `flux2_klein9b` — both: **(a)** direct context `flux` boxes + prompt **(b)** tool `flux2_klein9b` — stem `flux2_klein9b`
- `krea` `krea2_ref2img` — both: **(a)** direct context `krea` boxes + prompt **(b)** tool — stem `krea2_ref2img`
- `h3` `minimax_h3_fl2va` + `minimax_h3_comfy` — both: **(a)** direct context `h3` boxes: `first_frame/last_frame` **(b)** tool `h3_fl2va`/`h3_comfy` — stems `minimax_h3_fl2va`/`minimax_h3_comfy`
- `h3-ref` `minimax_h3_ref2va` + `minimax_h3_ref2va_comfy` — both: **(a)** direct context `h3-ref` boxes: `ref_images/ref_videos/ref_audios` **(b)** tool `h3_ref2va`/`h3_ref2va_comfy` — stems `minimax_h3_ref2va`/`minimax_h3_ref2va_comfy`
- `voice` `realtime_voice_*` — ASGI stream `audio.delta` (v2) — not in this cut

Boxes are context-specific: visible only when that `flux|krea|h3|h3-ref` picked in selector; switch model → boxes swap.

## Files
- deps `package.json`
- new `src/components/assistant-ui/thread.tsx` (registry)
- new `src/components/runtime/RuntimeProvider.tsx`
- edit `src/components/panels/Main.tsx:8-35` (`Chat UI placeholder` -> `<Thread />`)
- edit `src/components/layout/AppShell.tsx:26-48` wrap provider
- new `src/app/api/chat/route.ts` + `src/app/api/workers/[model]/route.ts`
- new `src/lib/chat/directHandlers.ts` + `src/lib/chat/tools.ts`
