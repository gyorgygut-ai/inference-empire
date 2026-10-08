"use client";

import React from "react";
import { useAppChat } from "./chat-hook";
import { vocabulary } from "@/messages";
import type { PublicOutcome } from "@/outcomes/outcomes";

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: [
      {
        id: "select-outcome",
        role: "assistant",
        metadata: { outcomes },
        parts: [{ type: "text", content: vocabulary.messages.selectOutcome }],
      },
    ],
  });
  return <chat.AppChat />;
};
