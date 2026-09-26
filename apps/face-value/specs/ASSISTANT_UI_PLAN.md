# Assistant-UI Implementation Plan

> Face-Value modern chat UI built on `@assistant-ui/react` — LLM-free flow for image generation.

## Current State Analysis

### Working Components
- `requestOutcome` Server Action exists in `app/actions.ts` (image processing, inference call)
- Basic assistant-ui structure: `chat-client.tsx`, `thread.tsx`, `composer.tsx`
- Outcome loading via `getPublicOutcomes()`
- Server online/offline detection via `pingInference()`
- Chat context for `selectedOutcomeId` and `hasAttachment`

### Broken / Missing
1. **Mock adapter** in `chat-client.tsx` (lines 6-17) — returns static text + 1x1 pixel GIF, never calls `requestOutcome`
2. **Plain `<button>` elements** for outcomes in `thread.tsx` (lines 24-31) instead of `SuggestionPrimitive`
3. **Custom image renderer** in `thread.tsx` (lines 42-45) instead of registry `Image` component with `Image.Actions`
4. **No server-offline system message** in thread
5. **No error/loading states** as system messages
6. **No attachment persistence** across turns
7. **No `SuggestionPrimitive`** — outcomes are plain buttons with no aui integration
8. **No registry components** — `npx assistant-ui@latest add thread/image` never run

---

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Primary interaction model | Chat interface, no LLM. Pure form-like flow wrapped in chat UI. |
| 2 | Image upload pattern | `AttachmentPrimitive` in composer after outcome selection. |
| 3 | Outcome selection UI | `SuggestionPrimitive` items inside the chat thread. |
| 4 | Generated image rendering | `ImageMessagePart` directly in assistant message. No tool-call chrome. |
| 5 | Multi-turn support | Yes. Re-select outcomes, re-upload, same or different outcome. |
| 6 | BE contract location | Canonical in `inference-tooling`. Runtime bridge uses `useLocalRuntime` calling `requestOutcome`. |
| A | Server offline state | Disabled composer. System message `❌ Server offline` in thread. |
| B | Error/loading states | Status messages in chat (system messages for errors, running status for loading). |
| C | Pre-send validation | Send button disabled until outcome selected + image attached. |
| D | Previous image persistence | Keep last attachment visible in composer between turns. |
| E | Model fallback | Handled by external Cloudflare gateway proxy. This app calls gateway; no fallback logic here. |
| F | Download option | `Image.Actions` from registry provides native download button. No custom `<a download>`. |
| G | Styling approach | Use assistant-ui registry components. Tailwind v4 already configured. |
| H | Layout | Full-width chat by default. At `lg` breakpoint → 2-column: left 2/3 (hero img), right 1/3 (chat). |

---

## Files to Modify

### `app/components/assistant-ui/chat-client.tsx`
Replace mock adapter (lines 6-17) with real `useLocalRuntime` bridge to `requestOutcome` Server Action:
- Extract last user message (text + attachments)
- Get selected outcome ID from chat context
- Call `requestOutcome` Server Action with FormData (image + outcome ID)
- Convert result to assistant-ui message parts: `{ type: "text", text: "..." }` or `{ type: "image", image: "presigned_url" }`

### `app/components/assistant-ui/thread.tsx`
- Replace plain `<button>` elements (lines 24-31) with `SuggestionPrimitive` items
- Run `npx assistant-ui@latest add thread` and integrate registry Thread component
- Replace custom `Image` component (lines 42-45) with registry Image component + `Image.Actions` for download
- Add server-offline system message when `!serverOnline` and thread is empty
- Implement error/loading states as system/running messages in thread

### `app/components/assistant-ui/composer.tsx`
- Implement attachment persistence across turns (keep last image visible)
- Verify pre-send validation: Send disabled until `selectedOutcomeId !== null && hasAttachment`
- Wire `SuggestionPrimitive` selection to update chat context

---

## Files to Create (via assistant-ui registry)

```bash
cd apps/face-value
npx assistant-ui@latest add thread
npx assistant-ui@latest add image
```

These commands scaffold registry components that provide:
- Pre-styled `Thread` component with `ThreadPrimitive` + `MessagePrimitive`
- Pre-styled `Image` component with `Image.Actions` (download button)

---

## Files to Delete (legacy form components — if they exist)

- `app/components/ImageGenerationForm.tsx`
- `app/components/ImageUpload.tsx`
- `app/components/OutcomePicker.tsx`
- `app/components/ResultDisplay.tsx`

---

## Test Cases

### TC-1: Outcome suggestions render
- Verify `SuggestionPrimitive` items appear in thread when no outcome selected
- Verify outcomes display correct titles from `getPublicOutcomes()`

### TC-2: Outcome selection updates composer
- Click a suggestion → outcome id stored in chat context
- Composer transitions to show `AttachmentPrimitive` as ready
- Send button becomes enabled only after attachment added

### TC-3: Attachment upload and persistence
- Upload image via `AttachmentPrimitive` → appears in composer
- Send message → image attaches to user message
- After generation completes, new turn opens with same image still attached

### TC-4: Composer disabled when server offline
- `serverOnline = false` → composer disabled
- System message `❌ Server offline` appears in thread
- No sends possible

### TC-5: Send button disabled until valid
- No outcome selected → disabled
- Outcome selected, no image → disabled
- Outcome selected + image attached → enabled

### TC-6: Image rendering with download
- Successful generation → assistant message contains `ImageMessagePart`
- Image displayed via registry `Image` component
- `Image.Actions` provides download button (no custom `<a download>`)
- No base64 encoding in URL (uses `presigned_url`)

### TC-7: Error state as system message
- Server Action returns error (timeout, invalid outcome, etc.)
- Error rendered as system message in thread
- No image rendered

### TC-8: Loading state
- After send, assistant message shows running/pending status
- Loading indicator replaces completed state

### TC-9: Multi-turn re-generation
- Select outcome, upload image, generate
- In next turn, select different outcome with same image → new image generated
- In next turn, upload new image (previous image replaced) → new image generated

### TC-10: Server Action contract
- `requestOutcome` returns `{ imageUrl: string }` not `{ imageBase64: string }`
- `schema.ts` `artifact` is `{ presigned_url: string }` not `string`
- Response from gateway matches canonical `inference-tooling` contract

---

## Next 6 Todos

| # | Task | File | Description |
|---|------|------|-------------|
| 1 | Scaffold assistant-ui registry components | — | `cd apps/face-value && npx assistant-ui@latest add thread` + `npx assistant-ui@latest add image` |
| 2 | Replace mock adapter with real Server Action bridge | `chat-client.tsx` | Remove mock adapter (lines 6-17). Implement `useLocalRuntime` adapter that calls `requestOutcome` with FormData |
| 3 | Replace plain buttons with `SuggestionPrimitive` | `thread.tsx` | Replace outcome `<button>` elements (lines 24-31) with `SuggestionPrimitive` items wired to chat context |
| 4 | Replace custom image with registry `Image` component | `thread.tsx` | Replace custom `Image` component (lines 42-45) with registry Image + `Image.Actions` for download |
| 5 | Add server-offline system message | `chat-client.tsx` / `thread.tsx` | When `!serverOnline`, show system message `❌ Server offline` in thread + disable composer |
| 6 | Implement error/loading as system messages | `chat-client.tsx` / `thread.tsx` | Server Action errors → system messages in thread; loading → running status during generation |

---

## Key Dependencies

- **`requestOutcome` Server Action** — must exist in `app/actions.ts` (already present)
- **Assistant-ui registry components** — scaffolded via `npx assistant-ui@latest add thread/image`
- **Tailwind v4** — already configured per package.json
- **Worker router / inference backend** — needed for live testing, but UI logic is fully testable without it

## Testing Notes

- Focus on UI/behavior tests: component rendering, state transitions, primitive interactions
- Use Vitest + React Testing Library (per TODO.md)
- Test each component in isolation: thread (empty/with-messages/offline), composer (disabled/enabled), adapter (success/error)
- Server Action tests in `app/__tests__/actions.test.ts` (if tests exist)

## Notes / Trade-offs

- **No API routes** — all inference via Server Action (`requestOutcome`), `useLocalRuntime` bridges directly
- **Mock adapter replaced** — initial adapter implementation may log messages for debugging before calling Server Action
- **Registry components** — `npx assistant-ui@latest add` scaffolds pre-styled components; may need Tailwind config adjustments
- **Multi-turn state** — attachment persistence tracked in chat context, not in assistant-ui internal state
- **Server offline** — `pingInference()` at render time, results passed as props to `ChatClient`
- **No LLM** — adapter does not use AI SDK; it calls Server Action directly and returns static message parts
