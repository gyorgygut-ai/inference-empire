# assistant-ui Migration Plan

## Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Primary interaction model | Chat interface, no LLM. Outcomes presented as selectable options within chat. Pure form-like flow wrapped in chat UI. |
| 2 | Image upload pattern | `AttachmentPrimitive` in composer after outcome selection. |
| 3 | Outcome selection UI | `SuggestionPrimitive` items inside the chat thread. |
| 4 | Generated image rendering | `ImageMessagePart` directly in assistant message. No tool-call chrome. |
| 5 | Multi-turn support | Yes. Re-select outcomes, re-upload, same or different outcome. |
| 6 | BE contract location | Canonical in `inference-tooling` (beam + modal workers). This repo's `schema.ts` mirrors it. Runpod flash out of service. Runtime bridge uses `useLocalRuntime` calling existing Server Action. |
| A | Server offline state | Disabled composer. |
| B | Error/loading states | Status messages in chat (system messages for errors, running status for loading). |
| C | Pre-send validation | Send button disabled until valid. |
| D | Previous image persistence | Keep last attachment visible in composer between turns. |
| E | Model fallback | Handled by external Cloudflare gateway proxy. This app calls gateway; no fallback logic here. |
| F | Download option | `Image.Actions` from registry (`npx assistant-ui@latest add image`) provides native download button. No custom `<a download>` needed. |
| G | Styling approach | Use assistant-ui registry components (`npx assistant-ui@latest add thread`, `npx assistant-ui@latest add image`). Pre-built, reasonably styled out of the box. Project already has Tailwind v4. Components support both Radix UI and Base UI flavors. |
| H | Layout | Full-width chat by default. At `lg` breakpoint → 2-column: left 2/3 (solid bg, hero img), right 1/3 (chat). Implemented as Tailwind grid on page wrapper, not inside assistant-ui primitives. |

---

## Files to Modify

**`app/page.tsx`**
- Replace `<ImageGenerationForm>` with `AssistantRuntimeProvider` + `Thread`
- Pass `serverOnline` into runtime initial state

**`app/actions.ts`**
- `ActionResult`: `{ imageBase64: string }` → `{ imageUrl: string }`
- Response: `response.output.artifact` → `response.output.artifact.presigned_url`

**`app/inference-api/schema.ts`**
- `Flux2Klein9BOutput.artifact`: `string` → `{ presigned_url: string }`

---

## Files to Delete

- `app/components/ImageGenerationForm.tsx`
- `app/components/ImageUpload.tsx`
- `app/components/OutcomePicker.tsx`
- `app/components/ResultDisplay.tsx`

---

## Files to Create

**`app/components/assistant-ui/thread.tsx`**
- Wraps registry `Thread` component + primitives
- Renders `SuggestionPrimitive` outcomes when none selected
- System message for server offline

**`app/components/assistant-ui/composer.tsx`**
- Registry `Composer` + `AttachmentPrimitive`
- Send button disabled when no outcome selected or no attachment
- Keeps last attachment visible between turns

---

## Packages to Add

- `@assistant-ui/react`
- `@assistant-ui/react-ai-sdk`

---

## Specs to Update

Add `## assistant-ui` section to `specs/SPECS.md` documenting the new chat-based UI, runtime choice (`useLocalRuntime`), and BE contract alignment.

---

## Test Cases

### TC-1: Outcome suggestions render
- Verify `SuggestionPrimitive` items appear in thread when no outcome selected
- Verify outcomes display correct titles from `getPublicOutcomes()`

### TC-2: Outcome selection updates composer
- Click a suggestion → outcome id stored in composer state
- Composer transitions to show `AttachmentPrimitive`
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
