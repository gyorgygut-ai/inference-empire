"use client";

import { useEffect } from "react";
import {
  useAui,
  useAuiState,
  ComposerPrimitive,
  AttachmentPrimitive,
} from "@assistant-ui/react";
import { ImageIcon, XIcon } from "lucide-react";
import { vocabulary } from "@/messages/vocabulary";
import { cn } from "../../styles/class-names";
import type { PublicOutcome } from "@/outcomes";

export const UploadComposer = ({
  _selectedOutcomeId,
}: {
  _selectedOutcomeId?: PublicOutcome["id"];
}) => {
  const aui = useAui();
  const messages = useAuiState((s) => s.thread.messages);
  const attachments = useAuiState((s) => s.thread.composer.attachments);
  const isAttachmentUploadEnabled = attachments.length < 1;

  useEffect(() => {
    const picked = attachments.some((a) => a.type === "image" && a.file);
    if (!picked) {
      return;
    }
    const exists = messages.some(
      (m) =>
        (m.metadata as { custom?: { type?: string } } | undefined)?.custom
          ?.type === "request-inference",
    );
    if (!exists) {
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.messages.requestInference }],
        metadata: { custom: { type: "request-inference" } },
      });
    }
  }, [attachments, messages, aui]);

  return (
    <ComposerPrimitive.AttachmentDropzone className="rounded-xl border-2 border-dashed border-border data-[dragging]:border-primary data-[dragging]:bg-primary/5">
      <ComposerPrimitive.Root
        className={cn("flex flex-col gap-2 ", {
          "bg-muted": !isAttachmentUploadEnabled,
          "bg-accent": isAttachmentUploadEnabled,
        })}
      >
        <ComposerPrimitive.Attachments>
          {({ attachment }) => {
            return attachment.type === "image" ? (
              <AttachmentPrimitive.Root className="flex items-center gap-2 rounded-lg border p-2 m-2 bg-background">
                <AttachmentPrimitive.unstable_Thumb className="flex size-10 items-center justify-center overflow-hidden rounded bg-muted text-xs">
                  <ImageIcon className="size-4" />
                </AttachmentPrimitive.unstable_Thumb>
                <span className="min-w-0 flex-1 truncate text-sm text-secondary-foreground">
                  <AttachmentPrimitive.Name />
                </span>
                <AttachmentPrimitive.Remove className="ml-auto rounded-full p-1 hover:bg-muted">
                  <XIcon className="size-3" />
                </AttachmentPrimitive.Remove>
              </AttachmentPrimitive.Root>
            ) : null;
          }}
        </ComposerPrimitive.Attachments>
        <ComposerPrimitive.AddAttachment
          disabled={!isAttachmentUploadEnabled}
          className="rounded p-3 w-full text-sm bg-accent font-medium text-accent-foreground disabled:bg-muted disabled:text-muted-foreground"
        >
          {vocabulary.messages.uploadReference}
        </ComposerPrimitive.AddAttachment>
      </ComposerPrimitive.Root>
    </ComposerPrimitive.AttachmentDropzone>
  );
}
