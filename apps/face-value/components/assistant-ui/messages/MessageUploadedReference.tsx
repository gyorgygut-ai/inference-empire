"use client";

import React from "react";
import { MessagePrimitive, AttachmentPrimitive } from "@assistant-ui/react";

export const MessageUploadedReference = () => (
  <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
    <div className="rounded-xl border-2 border-dashed border-border p-4 w-full">
      <AttachmentPrimitive.Root className="flex items-center gap-2 rounded-lg border p-2">
        <div className="flex size-10 items-center justify-center overflow-hidden rounded bg-muted text-xs">
          {/* Primitive handles image src resolution */}
        </div>
        {/*<AttachmentPrimitive.Name className="min-w-0 flex-1 truncate text-sm" />*/}
        <AttachmentPrimitive.Remove className="ml-auto rounded-full p-1 hover:bg-muted" />
      </AttachmentPrimitive.Root>
    </div>
  </MessagePrimitive.Root>
);
