# Face Value — Attachment Scope Fix

**Status**: Ready to implement
**Last tested**: 2025-09-28 — builds clean, runtime error on Chromium

## Error

```
Runtime Error: The current scope does not have a "attachment" property.
components/assistant-ui/chat-client.tsx (69:15) @ InnerChat
```

Screenshot shows Next.js error overlay at line 69: `<AttachmentPrimitive.unstable_Thumb />` inside `<AttachmentPrimitive.Root>` inside `<ComposerPrimitive.AddAttachment>`.

## Root Cause

`AttachmentPrimitive.Root` + `unstable_Thumb` require **attachment context** from `ComposerPrimitive.Attachments`.

Current code puts `AttachmentPrimitive.Root` inside `ComposerPrimitive.AddAttachment`, which only provides a file-picker trigger — no attachment state.

## Fix — chat-client.tsx lines 66–72

Replace the composer footer:

```tsx
<div className="p-4 border-t">
  <ComposerPrimitive.Root className="mt-4 flex flex-col gap-2">
    <ComposerPrimitive.Attachments className="flex flex-wrap gap-2">
      {() => (
        <AttachmentPrimitive.Root className="relative inline-flex h-16 w-16 items-center justify-center overflow-hidden rounded-lg border border-border">
          <AttachmentPrimitive.unstable_Thumb className="h-full w-full rounded-lg" />
          <AttachmentPrimitive.Remove className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-muted hover:bg-muted/80">
            ×
          </AttachmentPrimitive.Remove>
        </AttachmentPrimitive.Root>
      )}
    </ComposerPrimitive.Attachments>

    <div className="flex items-end gap-2">
      <ComposerPrimitive.AddAttachment className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm hover:bg-muted">
        +
      </ComposerPrimitive.AddAttachment>

      <ComposerPrimitive.Input
        className="flex-1 resize-none rounded-lg border border-border bg-background p-3 text-sm"
        placeholder="Type your message..."
      />

      <ComposerPrimitive.Send
        className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        disabled={isRunning}
      >
        {vocabulary.steps.generate.label}
      </ComposerPrimitive.Send>
    </div>
  </ComposerPrimitive.Root>
</div>
```

## Files to Edit

- `components/assistant-ui/chat-client.tsx` — lines 66–72

## Verification

1. `npx nx run face-value:build` passes
2. No runtime error in browser
3. Composer shows: file picker (+), text input, Generate button
4. Attaching file shows preview thumbnail + remove (×)
5. Outcome suggestion tap → user message → adapter processes it
