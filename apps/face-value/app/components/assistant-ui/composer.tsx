"use client"
import { useChat } from "./chat-context"
import {
  ComposerPrimitive,
  AttachmentPrimitive,
  AuiIf,
} from "@assistant-ui/react"

type ComposerProps = {
  serverOnline: boolean
}

export default function Composer({ serverOnline }: ComposerProps) {
  const { selectedOutcomeId, hasAttachment, setHasAttachment } = useChat()
  const isEnabled = serverOnline && selectedOutcomeId !== null && hasAttachment

  return (
    <ComposerPrimitive.Root className="p-3">
      <ComposerPrimitive.AttachmentDropzone disabled={!serverOnline}>
        <AuiIf condition={(s) => s.composer.attachments.length > 0}>
          <div className="flex flex-wrap gap-2 mb-2">
            <ComposerPrimitive.Attachments>
              {({ attachment }) => (
                <AttachmentPrimitive.Root key={attachment.id}>
                  <AttachmentPrimitive.unstable_Thumb />
                  <AttachmentPrimitive.Name />
                  <AttachmentPrimitive.Remove />
                </AttachmentPrimitive.Root>
              )}
            </ComposerPrimitive.Attachments>
          </div>
        </AuiIf>

        <div className="flex items-center gap-2">
          <ComposerPrimitive.AddAttachment
            disabled={!isEnabled}
            onChange={() => setHasAttachment(true)}
            aria-label="Add attachment"
          />
          <ComposerPrimitive.Input
            placeholder="Select an outcome above..."
            disabled={!isEnabled}
            className="flex-1 border rounded px-2 py-1"
          />
          <ComposerPrimitive.Send disabled={!isEnabled}>
            Send
          </ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.AttachmentDropzone>
    </ComposerPrimitive.Root>
  )
}