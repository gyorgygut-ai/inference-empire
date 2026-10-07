"use client";

import React from "react";
import { MessagePrimitive } from "@assistant-ui/react";
import { vocabulary } from "@/messages/vocabulary";

export const MessageSelectOutcome = () => (
  <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4 text-sm">
    {vocabulary.messages.selectOutcome}
  </MessagePrimitive.Root>
);