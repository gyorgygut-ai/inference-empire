"use client";

import React from "react";
import { ChatMessage as TanStackChatMessage } from "@tanstack/ai-react/ui";

export const ChatMessage = ({ message, ...props }: React.ComponentProps<typeof TanStackChatMessage>) => (
  <TanStackChatMessage
    message={message}
    className="flex"
    userClassName="justify-end"
    assistantClassName="justify-start"
    {...props}
  />
);
