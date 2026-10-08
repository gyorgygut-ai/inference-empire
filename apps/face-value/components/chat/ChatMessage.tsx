"use client";

import React from "react";
import { ChatMessage as TanStackChatMessage, type ChatMessageProps } from "@tanstack/ai-react/ui";

export const ChatMessage = (props: ChatMessageProps) => (
  <TanStackChatMessage
    className="flex"
    userClassName="justify-end"
    assistantClassName="justify-start"
    {...props}
  />
);
