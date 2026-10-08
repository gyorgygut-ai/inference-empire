"use client";

import React from "react";
import { ChatMessage as TanStackChatMessage } from "@tanstack/ai-react/ui";

export function ChatMessage({ message, ...props }: React.ComponentProps<typeof TanStackChatMessage>) {
  return (
    <TanStackChatMessage
      message={message}
      className="flex"
      userClassName="justify-end"
      assistantClassName="justify-start"
      {...props}
    />
  );
}
