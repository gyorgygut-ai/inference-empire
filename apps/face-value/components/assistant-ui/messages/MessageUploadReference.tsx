"use client";

import { MessagePrimitive } from "@assistant-ui/react";
import { vocabulary } from "@/messages/vocabulary";

export const MessageUploadReference = () => (
  <MessagePrimitive.Root className="hidden mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500 bg-surface italic rounded-xl p-4">
    {vocabulary.messages.uploadReference}
  </MessagePrimitive.Root>
);
